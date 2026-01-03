# -*- coding: utf-8 -*-
"""
GitCAD Export Integration
Handles automatic GitCAD file export/decompression after save operations.
"""

from pathlib import Path
from typing import Optional

from freecad_gitpdm.core import log
from freecad_gitpdm.gitcad import GitCADWrapper


def gitcad_export_if_available(
    repo_root: str,
    file_path: str,
    gitcad_wrapper: Optional[GitCADWrapper] = None
) -> bool:
    """
    Export (decompress) a .FCStd file using GitCAD if available.
    
    This should be called after saving a FreeCAD file to decompress it
    into a directory structure for better version control.
    
    Args:
        repo_root: Path to repository root
        file_path: Path to the .FCStd file that was saved
        gitcad_wrapper: Optional GitCADWrapper instance (will create if needed)
        
    Returns:
        bool: True if export was successful or not needed, False if failed
    """
    try:
        # Check if file is a .FCStd file
        if not file_path.lower().endswith('.fcstd'):
            return True  # Not a FCStd file, nothing to do
        
        # Create wrapper if not provided
        if gitcad_wrapper is None:
            from freecad_gitpdm.gitcad import is_gitcad_initialized
            
            if not is_gitcad_initialized(repo_root):
                log.debug("GitCAD not initialized, skipping export")
                return True  # Not an error, just not available
            
            try:
                gitcad_wrapper = GitCADWrapper(repo_root)
            except Exception as e:
                log.debug(f"Could not create GitCAD wrapper: {e}")
                return True  # Not an error, just not available
        
        # Export the file
        log.info(f"Exporting {file_path} with GitCAD...")
        result = gitcad_wrapper.export_fcstd(file_path)
        
        if result.ok:
            log.info(f"GitCAD export successful: {result.value}")
            return True
        else:
            error_msg = result.error.message if result.error else "Unknown error"
            log.warning(f"GitCAD export failed: {error_msg}")
            return False
            
    except Exception as e:
        log.error(f"Error during GitCAD export: {e}")
        return False


def gitcad_import_if_available(
    repo_root: str,
    file_path: str,
    gitcad_wrapper: Optional[GitCADWrapper] = None
) -> bool:
    """
    Import (recompress) a .FCStd file using GitCAD if available.
    
    This should be called before opening a FreeCAD file to recompress it
    from its directory structure.
    
    Args:
        repo_root: Path to repository root
        file_path: Path to the .FCStd file to import
        gitcad_wrapper: Optional GitCADWrapper instance (will create if needed)
        
    Returns:
        bool: True if import was successful or not needed, False if failed
    """
    try:
        # Check if file is a .FCStd file
        if not file_path.lower().endswith('.fcstd'):
            return True  # Not a FCStd file, nothing to do
        
        # Create wrapper if not provided
        if gitcad_wrapper is None:
            from freecad_gitpdm.gitcad import is_gitcad_initialized
            
            if not is_gitcad_initialized(repo_root):
                log.debug("GitCAD not initialized, skipping import")
                return True  # Not an error, just not available
            
            try:
                gitcad_wrapper = GitCADWrapper(repo_root)
            except Exception as e:
                log.debug(f"Could not create GitCAD wrapper: {e}")
                return True  # Not an error, just not available
        
        # Import the file
        log.info(f"Importing {file_path} with GitCAD...")
        result = gitcad_wrapper.import_fcstd(file_path)
        
        if result.ok:
            log.info(f"GitCAD import successful: {result.value}")
            return True
        else:
            error_msg = result.error.message if result.error else "Unknown error"
            log.warning(f"GitCAD import failed: {error_msg}")
            return False
            
    except Exception as e:
        log.error(f"Error during GitCAD import: {e}")
        return False
