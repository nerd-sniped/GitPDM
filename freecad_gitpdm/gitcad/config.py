# -*- coding: utf-8 -*-
"""
GitCAD Configuration Bridge
Handles reading/writing GitCAD's config.json file.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, asdict

from freecad_gitpdm.core import log
from freecad_gitpdm.core.result import Result


@dataclass
class UncompressedDirStructure:
    """Configuration for uncompressed directory structure."""

    uncompressed_directory_suffix: str = "_uncompressed"
    uncompressed_directory_prefix: str = ""
    put_uncompressed_directory_in_subdirectory: bool = False
    subdirectory_name: str = ".freecad_data"


@dataclass
class CompressBinariesConfig:
    """Configuration for compressing binary files."""

    enabled: bool = True
    files_to_compress: List[str] = None
    max_compressed_file_size_gigabyte: float = 2.0
    compression_level: int = 6
    zip_file_prefix: str = "binaries_"

    def __post_init__(self):
        if self.files_to_compress is None:
            self.files_to_compress = [
                "*.brp",
                "*.Map.*",
                "no_extension/*",
            ]


@dataclass
class GitCADConfig:
    """
    GitCAD configuration structure.
    Mirrors the structure of GitCAD's config.json file.
    """

    freecad_python_instance_path: str = ""
    require_lock_to_modify_freecad_files: bool = True
    require_gitcad_activation: bool = False
    include_thumbnails: bool = False
    uncompressed_directory_structure: UncompressedDirStructure = None
    compress_non_human_readable_freecad_files: CompressBinariesConfig = None

    def __post_init__(self):
        if self.uncompressed_directory_structure is None:
            self.uncompressed_directory_structure = UncompressedDirStructure()
        if self.compress_non_human_readable_freecad_files is None:
            self.compress_non_human_readable_freecad_files = CompressBinariesConfig()

    def to_dict(self) -> dict:
        """Convert to dictionary matching GitCAD's config.json format."""
        return {
            "freecad-python-instance-path": self.freecad_python_instance_path,
            "require-lock-to-modify-FreeCAD-files": self.require_lock_to_modify_freecad_files,
            "require-GitCAD-activation": self.require_gitcad_activation,
            "include-thumbnails": self.include_thumbnails,
            "uncompressed-directory-structure": {
                "uncompressed-directory-suffix": self.uncompressed_directory_structure.uncompressed_directory_suffix,
                "uncompressed-directory-prefix": self.uncompressed_directory_structure.uncompressed_directory_prefix,
                "subdirectory": {
                    "put-uncompressed-directory-in-subdirectory": self.uncompressed_directory_structure.put_uncompressed_directory_in_subdirectory,
                    "subdirectory-name": self.uncompressed_directory_structure.subdirectory_name,
                },
            },
            "compress-non-human-readable-FreeCAD-files": {
                "enabled": self.compress_non_human_readable_freecad_files.enabled,
                "files-to-compress": self.compress_non_human_readable_freecad_files.files_to_compress,
                "max-compressed-file-size-gigabyte": self.compress_non_human_readable_freecad_files.max_compressed_file_size_gigabyte,
                "compression-level": self.compress_non_human_readable_freecad_files.compression_level,
                "zip-file-prefix": self.compress_non_human_readable_freecad_files.zip_file_prefix,
            },
        }

    @classmethod
    def from_dict(cls, data: dict) -> GitCADConfig:
        """Create GitCADConfig from dictionary (GitCAD's config.json format)."""
        # Parse uncompressed directory structure
        uncompressed = data.get("uncompressed-directory-structure", {})
        subdirectory = uncompressed.get("subdirectory", {})

        uncompressed_struct = UncompressedDirStructure(
            uncompressed_directory_suffix=uncompressed.get(
                "uncompressed-directory-suffix", "_uncompressed"
            ),
            uncompressed_directory_prefix=uncompressed.get(
                "uncompressed-directory-prefix", ""
            ),
            put_uncompressed_directory_in_subdirectory=subdirectory.get(
                "put-uncompressed-directory-in-subdirectory", False
            ),
            subdirectory_name=subdirectory.get("subdirectory-name", ".freecad_data"),
        )

        # Parse binary compression config
        compress = data.get("compress-non-human-readable-FreeCAD-files", {})
        compress_config = CompressBinariesConfig(
            enabled=compress.get("enabled", True),
            files_to_compress=compress.get(
                "files-to-compress", ["*.brp", "*.Map.*", "no_extension/*"]
            ),
            max_compressed_file_size_gigabyte=compress.get(
                "max-compressed-file-size-gigabyte", 2.0
            ),
            compression_level=compress.get("compression-level", 6),
            zip_file_prefix=compress.get("zip-file-prefix", "binaries_"),
        )

        return cls(
            freecad_python_instance_path=data.get("freecad-python-instance-path", ""),
            require_lock_to_modify_freecad_files=data.get(
                "require-lock-to-modify-FreeCAD-files", True
            ),
            require_gitcad_activation=data.get("require-GitCAD-activation", False),
            include_thumbnails=data.get("include-thumbnails", False),
            uncompressed_directory_structure=uncompressed_struct,
            compress_non_human_readable_freecad_files=compress_config,
        )


def _get_config_path(repo_root: str) -> Path:
    """Get path to GitCAD config.json file."""
    return Path(repo_root) / "FreeCAD_Automation" / "config.json"


def load_gitcad_config(repo_root: str) -> Result:
    """
    Load GitCAD configuration from config.json.
    
    Args:
        repo_root: Path to repository root
        
    Returns:
        Result containing GitCADConfig, or error
    """
    config_path = _get_config_path(repo_root)

    if not config_path.exists():
        return Result.failure("CONFIG_ERROR", f"GitCAD config not found: {config_path}")

    try:
        with open(config_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        config = GitCADConfig.from_dict(data)
        log.debug(f"Loaded GitCAD config from: {config_path}")
        return Result.success(config)

    except json.JSONDecodeError as e:
        return Result.failure("CONFIG_ERROR", f"Invalid JSON in config file: {e}")
    except Exception as e:
        return Result.failure("CONFIG_ERROR", f"Failed to load config: {e}")


def save_gitcad_config(repo_root: str, config: GitCADConfig) -> Result:
    """
    Save GitCAD configuration to config.json.
    
    Args:
        repo_root: Path to repository root
        config: GitCADConfig object to save
        
    Returns:
        Result indicating success/failure
    """
    config_path = _get_config_path(repo_root)

    # Ensure directory exists
    config_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        data = config.to_dict()

        # Write with proper formatting (2 space indent, like GitCAD default)
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
            f.write("\n")  # Add trailing newline

        log.debug(f"Saved GitCAD config to: {config_path}")
        return Result.success(f"Config saved to: {config_path}")

    except Exception as e:
        return Result.failure("CONFIG_ERROR", f"Failed to save config: {e}")


def create_default_config(repo_root: str, freecad_python_path: str = "") -> Result:
    """
    Create a default GitCAD configuration file.
    
    Args:
        repo_root: Path to repository root
        freecad_python_path: Path to FreeCAD's Python executable (optional)
        
    Returns:
        Result containing created GitCADConfig, or error
    """
    # Auto-detect Python path if not provided
    if not freecad_python_path:
        try:
            import sys
            freecad_python_path = sys.executable
            log.info(f"Auto-detected Python path: {freecad_python_path}")
        except Exception as e:
            log.warning(f"Could not auto-detect Python path: {e}")
            freecad_python_path = ""
    
    config = GitCADConfig(freecad_python_instance_path=freecad_python_path)

    result = save_gitcad_config(repo_root, config)
    if not result.ok:
        error_msg = result.error.message if result.error else "Unknown error"
        return Result.failure(
            code="CONFIG_CREATE_FAILED",
            message="Failed to create default config",
            details=error_msg
        )

    return Result.success(config)


def get_uncompressed_dir_path(
    fcstd_file_path: str, config: GitCADConfig, repo_root: str
) -> str:
    """
    Get the uncompressed directory path for a .FCStd file based on config.
    
    Args:
        fcstd_file_path: Path to .FCStd file (relative to repo root)
        config: GitCADConfig object
        repo_root: Path to repository root
        
    Returns:
        str: Path to uncompressed directory (relative to repo root)
    """
    fcstd_path = Path(fcstd_file_path)
    fcstd_dir = fcstd_path.parent
    fcstd_name = fcstd_path.stem  # Filename without extension

    # Build uncompressed directory name
    struct = config.uncompressed_directory_structure
    uncompressed_dir_name = (
        f"{struct.uncompressed_directory_prefix}"
        f"{fcstd_name}"
        f"{struct.uncompressed_directory_suffix}"
    )

    # Build full path
    if struct.put_uncompressed_directory_in_subdirectory:
        uncompressed_path = (
            fcstd_dir / struct.subdirectory_name / uncompressed_dir_name
        )
    else:
        uncompressed_path = fcstd_dir / uncompressed_dir_name

    return str(uncompressed_path)
