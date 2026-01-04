# -*- coding: utf-8 -*-
"""
FCStd File Tool - Core Module
Sprint 1: Native Python implementation of FCStd compression/decompression

This module provides functionality for working with FreeCAD .FCStd files,
including compression, decompression, and conversion between .FCStd archives
and uncompressed directory structures for version control.

Ported from GitCAD's FCStdFileTool.py to eliminate bash wrapper dependency.
"""

from __future__ import annotations

import zipfile
import shutil
import json
from pathlib import Path
from typing import Optional, TYPE_CHECKING
from dataclasses import dataclass

from .result import Result
from . import log

if TYPE_CHECKING:
    from .config_manager import FCStdConfig


@dataclass
class ExportResult:
    """Result of FCStd export operation."""
    output_dir: Path
    files_exported: int
    binaries_compressed: int


@dataclass
class ImportResult:
    """Result of FCStd import operation."""
    fcstd_path: Path
    files_imported: int
    binaries_decompressed: int


def export_fcstd(
    fcstd_path: Path,
    output_dir: Optional[Path] = None,
    config: Optional[dict] = None
) -> Result:
    """
    Export (decompress) a .FCStd file to an uncompressed directory structure.
    
    This decompresses the .FCStd ZIP archive into a directory, making the
    contents (Document.xml, GuiDocument.xml, etc.) visible to version control.
    Binary files (.brp, etc.) can optionally be compressed separately.
    
    Args:
        fcstd_path: Path to the .FCStd file to export
        output_dir: Target directory (auto-calculated if None)
        config: Configuration dict (loads default if None)
        
    Returns:
        Result with ExportResult on success, error on failure
        
    Example:
        >>> result = export_fcstd(Path("part.FCStd"))
        >>> if result.ok:
        ...     print(f"Exported to {result.value.output_dir}")
    """
    try:
        fcstd_path = Path(fcstd_path)
        
        if not fcstd_path.exists():
            return Result.failure(
                "FILE_NOT_FOUND",
                f"FCStd file not found: {fcstd_path}"
            )
        
        if not fcstd_path.suffix.lower() == '.fcstd':
            return Result.failure(
                "INVALID_FILE",
                f"Not a .FCStd file: {fcstd_path}"
            )
        
        # Load configuration
        if config is None:
            from .config_manager import load_config
            # Try to load from repo, fall back to defaults
            try:
                repo_root = _find_repo_root(fcstd_path.parent)
                config = load_config(repo_root)
            except Exception:
                from .config_manager import FCStdConfig
                config = FCStdConfig()
        
        # Calculate output directory
        if output_dir is None:
            from .config_manager import get_uncompressed_dir
            output_dir = get_uncompressed_dir(
                fcstd_path.parent,
                fcstd_path.name,
                config
            )
        
        log.info(f"Exporting {fcstd_path} to {output_dir}")
        
        # Create output directory
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Extract the FCStd file (it's a ZIP archive)
        files_exported = 0
        with zipfile.ZipFile(fcstd_path, 'r') as zip_ref:
            for member in zip_ref.namelist():
                zip_ref.extract(member, output_dir)
                files_exported += 1
        
        log.info(f"Exported {files_exported} files to {output_dir}")
        
        # Handle binary compression if enabled
        binaries_compressed = 0
        if config.compress_binaries:
            compress_result = compress_binaries(output_dir, config)
            if compress_result.ok:
                binaries_compressed = compress_result.value
            else:
                log.warning(f"Binary compression failed: {compress_result.error}")
        
        # Move files without extension to subdirectory
        move_files_without_extension(output_dir, "no_extension")
        
        result = ExportResult(
            output_dir=output_dir,
            files_exported=files_exported,
            binaries_compressed=binaries_compressed
        )
        
        return Result.success(result)
        
    except zipfile.BadZipFile:
        return Result.failure(
            "CORRUPT_FILE",
            f"File is not a valid ZIP/FCStd archive: {fcstd_path}"
        )
    except PermissionError as e:
        return Result.failure(
            "PERMISSION_DENIED",
            f"Permission denied accessing {fcstd_path}: {e}"
        )
    except Exception as e:
        log.error(f"Export failed: {e}")
        return Result.failure(
            "EXPORT_ERROR",
            f"Failed to export {fcstd_path}: {e}"
        )


def import_fcstd(
    input_dir: Path,
    fcstd_path: Path,
    config: Optional[dict] = None
) -> Result:
    """
    Import (compress) an uncompressed directory back to a .FCStd file.
    
    This creates a .FCStd ZIP archive from a directory structure,
    reversing the export operation. Used by git hooks after checkout/merge.
    
    Args:
        input_dir: Source directory with uncompressed FCStd contents
        fcstd_path: Target .FCStd file path
        config: Configuration dict (loads default if None)
        
    Returns:
        Result with ImportResult on success, error on failure
        
    Example:
        >>> result = import_fcstd(Path("part_uncompressed"), Path("part.FCStd"))
        >>> if result.ok:
        ...     print(f"Created {result.value.fcstd_path}")
    """
    try:
        input_dir = Path(input_dir)
        fcstd_path = Path(fcstd_path)
        
        if not input_dir.exists():
            return Result.failure(
                "DIR_NOT_FOUND",
                f"Input directory not found: {input_dir}"
            )
        
        if not input_dir.is_dir():
            return Result.failure(
                "NOT_A_DIRECTORY",
                f"Not a directory: {input_dir}"
            )
        
        log.info(f"Importing {input_dir} to {fcstd_path}")
        
        # Load configuration
        if config is None:
            from .config_manager import load_config
            try:
                repo_root = _find_repo_root(fcstd_path.parent)
                config = load_config(repo_root)
            except Exception:
                from .config_manager import FCStdConfig
                config = FCStdConfig()
        
        # Decompress binary files first if they exist
        binaries_decompressed = 0
        if config.compress_binaries:
            decompress_result = decompress_binaries(input_dir, config)
            if decompress_result.ok:
                binaries_decompressed = decompress_result.value
            else:
                log.warning(f"Binary decompression failed: {decompress_result.error}")
        
        # Create FCStd file (ZIP archive)
        files_imported = 0
        with zipfile.ZipFile(fcstd_path, 'w', zipfile.ZIP_DEFLATED) as zip_ref:
            for file_path in input_dir.rglob('*'):
                if file_path.is_file():
                    # Skip compressed binary zips
                    if config.compress_binaries and file_path.name.startswith(config.zip_file_prefix):
                        continue
                    arcname = file_path.relative_to(input_dir)
                    zip_ref.write(file_path, arcname)
                    files_imported += 1
        
        log.info(f"Imported {files_imported} files to {fcstd_path}")
        
        result = ImportResult(
            fcstd_path=fcstd_path,
            files_imported=files_imported,
            binaries_decompressed=binaries_decompressed
        )
        
        return Result.success(result)
        
    except PermissionError as e:
        return Result.failure(
            "PERMISSION_DENIED",
            f"Permission denied: {e}"
        )
    except Exception as e:
        log.error(f"Import failed: {e}")
        return Result.failure(
            "IMPORT_ERROR",
            f"Failed to import {input_dir}: {e}"
        )


def _find_repo_root(start_path: Path) -> Path:
    """
    Find the git repository root by searching for .git directory.
    
    Args:
        start_path: Directory to start searching from
        
    Returns:
        Path to repository root
        
    Raises:
        RuntimeError: If not in a git repository
    """
    current = start_path.resolve()
    
    while current != current.parent:
        if (current / ".git").exists():
            return current
        current = current.parent
    
    raise RuntimeError(f"Not in a git repository: {start_path}")


def compress_binaries(uncompressed_dir: Path, config: 'FCStdConfig') -> Result:
    """
    Compress binary files in uncompressed directory according to config patterns.
    
    Creates zip files with prefix from config, splitting into multiple zips if size
    limit is exceeded. Removes original files after compression.
    
    Args:
        uncompressed_dir: Path to uncompressed FCStd directory
        config: Configuration with binary patterns and compression settings
        
    Returns:
        Result indicating success or number of compressed files
    """
    from pathlib import PurePosixPath
    import io
    
    if not config.compress_binaries:
        return Result.success(0)
    
    try:
        patterns = config.binary_file_patterns
        max_size_bytes = config.max_compressed_file_size_gb * (1024 ** 3)
        compression_level = config.compression_level
        zip_prefix = config.zip_file_prefix
        
        # Collect files to compress
        to_compress = []
        for item_path in uncompressed_dir.rglob("*"):
            if not item_path.is_file():
                continue
                
            # Convert to POSIX path for pattern matching (GitCAD compatibility)
            rel_path = item_path.relative_to(uncompressed_dir)
            posix_path = PurePosixPath('/' + str(rel_path).replace('\\', '/'))
            
            # Check if matches any pattern
            for pattern in patterns:
                if posix_path.match(pattern):
                    to_compress.append(item_path)
                    break
        
        if not to_compress:
            log.debug("No binary files found to compress")
            return Result.success(0)
            
        log.info(f"Compressing {len(to_compress)} binary files")
        
        # Compress items into zip files
        zip_index = 1
        current_zip = io.BytesIO()
        i = 0
        is_recompressing_file = False
        was_recompressing_file = False
        
        while i < len(to_compress):
            item = to_compress[i]
            
            # Prevent infinite loop if file is too large
            if is_recompressing_file and was_recompressing_file:
                file_size_gb = item.stat().st_size / (1024 ** 3)
                return Result.failure(
                    "FILE_TOO_LARGE",
                    f"Max zip size {config.max_compressed_file_size_gb} GB and compression "
                    f"level {compression_level} is too small for '{item.name}' "
                    f"with size {file_size_gb:.2f} GB"
                )
            
            # Backup before adding
            backup = io.BytesIO(current_zip.getvalue())
            path_in_zip = str(item.relative_to(uncompressed_dir))
            
            # Add file to zip
            with zipfile.ZipFile(current_zip, 'a', zipfile.ZIP_DEFLATED, 
                               compresslevel=compression_level) as zf:
                zf.write(str(item), path_in_zip)
            
            # Check if exceeded size limit
            if current_zip.tell() > max_size_bytes:
                # Restore backup
                current_zip = backup
                
                # Write current zip to disk
                zip_index = _write_zip_to_disk(
                    uncompressed_dir, zip_prefix, zip_index, current_zip
                )
                
                # Start new zip
                current_zip = io.BytesIO()
                
                # Retry this file with new archive
                was_recompressing_file = is_recompressing_file
                is_recompressing_file = True
                continue
            
            # Remove original file after successful compression
            item.unlink()
            
            is_recompressing_file = False
            was_recompressing_file = False
            i += 1
        
        # Write last zip if it has content
        if current_zip.tell() > 0:
            _write_zip_to_disk(uncompressed_dir, zip_prefix, zip_index, current_zip)
        
        log.info(f"Binary compression completed with {zip_index} zip file(s)")
        return Result.success(len(to_compress))
        
    except Exception as e:
        log.error(f"Failed to compress binaries: {e}")
        return Result.failure("COMPRESSION_ERROR", f"Binary compression failed: {e}")


def _write_zip_to_disk(directory: Path, prefix: str, index: int, zip_buffer: 'io.BytesIO') -> int:
    """
    Write a zip buffer to disk with indexed filename.
    
    Args:
        directory: Directory to write zip file to
        prefix: Prefix for zip filename
        index: Current index for filename
        zip_buffer: BytesIO buffer containing zip data
        
    Returns:
        Next index (index + 1)
    """
    import os
    
    zip_name = f"{prefix}{index}.zip"
    zip_path = directory / zip_name
    
    with open(zip_path, 'wb') as f:
        f.write(zip_buffer.getvalue())
        f.flush()
        os.fsync(f.fileno())
    
    return index + 1


def decompress_binaries(uncompressed_dir: Path, config: 'FCStdConfig') -> Result:
    """
    Decompress binary zip files in an uncompressed FCStd directory.
    
    Extracts all zip files matching the configured prefix, used during
    import operations to restore binary files before creating .FCStd.
    
    Args:
        uncompressed_dir: Path to uncompressed FCStd directory
        config: Configuration with zip file prefix
        
    Returns:
        Result indicating success or number of decompressed files
    """
    if not config.compress_binaries:
        return Result.success(0)
    
    try:
        zip_prefix = config.zip_file_prefix
        
        # Find all compressed binary zip files
        zip_files = sorted(uncompressed_dir.glob(f"{zip_prefix}*.zip"))
        
        if not zip_files:
            log.debug("No compressed binary files found")
            return Result.success(0)
        
        log.info(f"Decompressing {len(zip_files)} binary zip file(s)")
        
        total_extracted = 0
        for zip_file in zip_files:
            with zipfile.ZipFile(zip_file, 'r') as zf:
                zf.extractall(uncompressed_dir)
                total_extracted += len(zf.namelist())
        
        log.info(f"Decompressed {total_extracted} binary files")
        return Result.success(total_extracted)
        
    except Exception as e:
        log.error(f"Failed to decompress binaries: {e}")
        return Result.failure("DECOMPRESSION_ERROR", f"Binary decompression failed: {e}")


def extract_thumbnail(fcstd_path: Path, output_path: Optional[Path] = None) -> Result:
    """
    Extract thumbnail image from a .FCStd file.
    
    Args:
        fcstd_path: Path to .FCStd file
        output_path: Where to save thumbnail (defaults to fcstd_name_thumbnail.png)
        
    Returns:
        Result with Path to extracted thumbnail on success
    """
    try:
        fcstd_path = Path(fcstd_path)
        
        if not fcstd_path.exists():
            return Result.failure("FILE_NOT_FOUND", f"FCStd file not found: {fcstd_path}")
        
        # Default output path
        if output_path is None:
            output_path = fcstd_path.parent / f"{fcstd_path.stem}_thumbnail.png"
        
        # Extract thumbnail from FCStd ZIP
        with zipfile.ZipFile(fcstd_path, 'r') as zf:
            thumbnail_name = 'thumbnails/Thumbnail.png'
            if thumbnail_name not in zf.namelist():
                return Result.failure("NO_THUMBNAIL", f"No thumbnail found in {fcstd_path}")
            
            # Extract to output path
            thumbnail_data = zf.read(thumbnail_name)
            output_path.write_bytes(thumbnail_data)
        
        log.info(f"Extracted thumbnail to {output_path}")
        return Result.success(output_path)
        
    except zipfile.BadZipFile:
        return Result.failure("CORRUPT_FILE", f"Not a valid FCStd file: {fcstd_path}")
    except Exception as e:
        log.error(f"Failed to extract thumbnail: {e}")
        return Result.failure("EXTRACTION_ERROR", f"Thumbnail extraction failed: {e}")


def move_files_without_extension(uncompressed_dir: Path, subdir_name: str = "no_extension") -> Result:
    """
    Move files without extensions to a subdirectory for better organization.
    
    Args:
        uncompressed_dir: Path to uncompressed FCStd directory
        subdir_name: Name of subdirectory to create
        
    Returns:
        Result with count of moved files
    """
    try:
        no_ext_dir = uncompressed_dir / subdir_name
        no_ext_dir.mkdir(exist_ok=True)
        
        moved_count = 0
        for item in uncompressed_dir.iterdir():
            if item.is_file() and '.' not in item.name:
                target = no_ext_dir / item.name
                item.rename(target)
                moved_count += 1
        
        if moved_count > 0:
            log.info(f"Moved {moved_count} files without extension to {no_ext_dir}")
        
        return Result.success(moved_count)
        
    except Exception as e:
        log.error(f"Failed to move files without extension: {e}")
        return Result.failure("MOVE_ERROR", f"Failed to organize files: {e}")
