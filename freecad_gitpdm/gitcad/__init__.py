# -*- coding: utf-8 -*-
"""
GitCAD Integration Module (PARTIALLY DEPRECATED)

⚠️ DEPRECATION NOTICE ⚠️
The bash wrapper components of this module are deprecated as of Sprint 3 (January 2026).

DEPRECATED:
- GitCADWrapper class - Use freecad_gitpdm.core modules instead
- Bash-based operations (export_fcstd, import_fcstd, lock/unlock from wrapper)
- is_gitcad_initialized() - Will be simplified to only check config

ACTIVE (Not Deprecated):
- GitCADConfig and related config classes - Still valid
- Detector functions (check_gitcad_status, find_fcstd_files, etc.) - Still valid

Migration Guide:
---------------

OLD CODE (deprecated):
    from freecad_gitpdm.gitcad import GitCADWrapper, export_fcstd
    wrapper = GitCADWrapper(repo_root)
    export_fcstd(repo_root, file_path)

NEW CODE (recommended):
    from freecad_gitpdm.core.fcstd_tool import export_fcstd
    from freecad_gitpdm.core.config_manager import load_config
    from freecad_gitpdm.core.lock_manager import lock_file, unlock_file
    
    config = load_config(repo_root)
    export_fcstd(repo_root, file_path, config)

For most use cases, import directly from freecad_gitpdm.export.gitcad_integration:
    from freecad_gitpdm.export.gitcad_integration import (
        gitcad_export_if_available,
        gitcad_import_if_available
    )
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
