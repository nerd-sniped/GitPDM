"""
FCStd Export Integration
Handles automatic FCStd file export/import operations.

Sprint 6: Renamed from gitcad_integration.py, standardized function names.
"""

from pathlib import Path

from freecad.gitpdm.core import log


def export_fcstd_file(repo_root: str, file_path: str) -> bool:
    """
    Export (decompress) a .FCStd file to directory structure.
    
    Args:
        repo_root: Path to repository root
        file_path: Path to the .FCStd file to export
        
    Returns:
        bool: True if export was successful, False if failed
    """
    try:
        from freecad.gitpdm.core.fcstd_tool import export_fcstd
        from freecad.gitpdm.core.config_manager import load_config
        
        # Load config from repo
        config = load_config(Path(repo_root))
        
        # Export the file
        log.info(f"Exporting {file_path}...")
        result = export_fcstd(Path(file_path), config=config)
        
        if result.ok:
            log.info(f"Export successful: {result.value.output_dir}")
            return True
        else:
            error_msg = result.error
            log.warning(f"Export failed: {error_msg}")
            return False
            
    except Exception as e:
        log.error(f"Error during export: {e}")
        return False


def import_fcstd_file(repo_root: str, file_path: str) -> bool:
    """
    Import (recompress) a .FCStd file from directory structure.
    
    Args:
        repo_root: Path to repository root
        file_path: Path to the .FCStd file to import
        
    Returns:
        bool: True if import was successful or not needed, False if failed
    """
    try:
        from freecad.gitpdm.core.fcstd_tool import import_fcstd
        from freecad.gitpdm.core.config_manager import load_config, get_uncompressed_dir
        
        # Load config from repo
        config = load_config(Path(repo_root))
        
        # Calculate the uncompressed directory path
        fcstd_path = Path(file_path)
        uncompressed_dir = get_uncompressed_dir(
            fcstd_path.parent,
            fcstd_path.name,
            config
        )
        
        # Check if uncompressed directory exists
        if not uncompressed_dir.exists():
            log.debug(f"Uncompressed directory does not exist: {uncompressed_dir}")
            return True  # Not an error, just not yet exported
        
        # Import the file
        log.info(f"Importing {file_path}...")
        result = import_fcstd(uncompressed_dir, fcstd_path, config=config)
        
        if result.ok:
            log.info(f"Import successful: {result.value.fcstd_path}")
            return True
        else:
            error_msg = result.error
            log.warning(f"Import failed: {error_msg}")
            return False
            
    except Exception as e:
        log.error(f"Error during import: {e}")
        return False


def export_if_available(repo_root: str, file_path: str) -> bool:
    """
    Export (decompress) a .FCStd file if it's a FCStd file.
    
    This should be called after saving a FreeCAD file to decompress it
    into a directory structure for better version control.
    
    Args:
        repo_root: Path to repository root
        file_path: Path to the .FCStd file that was saved
        
    Returns:
        bool: True if export was successful or not needed, False if failed
    """
    try:
        # Check if file is a .FCStd file
        if not file_path.lower().endswith('.fcstd'):
            return True  # Not a FCStd file, nothing to do
        
        return export_fcstd_file(repo_root, file_path)
            
    except Exception as e:
        log.error(f"Error during export: {e}")
        return False


def import_if_available(repo_root: str, file_path: str) -> bool:
    """
    Import (recompress) a .FCStd file if it's a FCStd file.
    
    This should be called before opening a FreeCAD file to recompress it
    from its directory structure.
    
    Args:
        repo_root: Path to repository root
        file_path: Path to the .FCStd file to import
        
    Returns:
        bool: True if import was successful or not needed, False if failed
    """
    try:
        # Check if file is a .FCStd file
        if not file_path.lower().endswith('.fcstd'):
            return True  # Not a FCStd file, nothing to do
        
        return import_fcstd_file(repo_root, file_path)
            
    except Exception as e:
        log.error(f"Error during import: {e}")
        return False
