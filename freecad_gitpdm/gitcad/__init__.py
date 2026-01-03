# -*- coding: utf-8 -*-
"""
GitCAD Integration Module
Provides Python interface to GitCAD's bash-based git automation system.
"""

from .wrapper import (
    GitCADWrapper,
    LockInfo,
    init_repository,
    lock_file,
    unlock_file,
    export_fcstd,
    import_fcstd,
    get_locks,
    is_gitcad_initialized,
)
from .config import (
    GitCADConfig,
    UncompressedDirStructure,
    CompressBinariesConfig,
    load_gitcad_config,
    save_gitcad_config,
    create_default_config,
    get_uncompressed_dir_path,
)
from .detector import (
    GitCADStatus,
    check_gitcad_status,
    find_fcstd_files,
    get_fcstd_uncompressed_dir,
    is_fcstd_exported,
)

__all__ = [
    # Wrapper
    "GitCADWrapper",
    "LockInfo",
    "init_repository",
    "lock_file",
    "unlock_file",
    "export_fcstd",
    "import_fcstd",
    "get_locks",
    "is_gitcad_initialized",
    # Config
    "GitCADConfig",
    "UncompressedDirStructure",
    "CompressBinariesConfig",
    "load_gitcad_config",
    "save_gitcad_config",
    "create_default_config",
    "get_uncompressed_dir_path",
    # Detector
    "GitCADStatus",
    "check_gitcad_status",
    "find_fcstd_files",
    "get_fcstd_uncompressed_dir",
    "is_fcstd_exported",
]
