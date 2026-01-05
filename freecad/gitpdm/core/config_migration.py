"""
Configuration Migration Utility
Sprint 4: Migrate from FreeCAD_Automation/config.json to .gitpdm/config.json

This module handles automatic detection and migration of legacy GitCAD
configuration files to the new native GitPDM format.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Optional
from dataclasses import dataclass

from .config_manager import FCStdConfig
from .result import Result
from . import log


@dataclass
class MigrationResult:
    """Result of configuration migration."""
    success: bool
    old_path: Optional[Path]
    new_path: Optional[Path]
    migrated: bool  # False if already using new format
    backup_path: Optional[Path]
    message: str


def detect_config_location(repo_root: Path) -> Optional[Path]:
    """
    Detect which configuration file exists (if any).
    
    Checks in order:
    1. .gitpdm/config.json (new format)
    2. FreeCAD_Automation/config.json (legacy GitCAD format)
    
    Args:
        repo_root: Path to repository root
        
    Returns:
        Path to config file, or None if no config found
    """
    # Check new format first
    new_config = repo_root / ".gitpdm" / "config.json"
    if new_config.exists():
        return new_config
    
    # Check legacy format
    legacy_config = repo_root / "FreeCAD_Automation" / "config.json"
    if legacy_config.exists():
        return legacy_config
    
    return None


def needs_migration(repo_root: Path) -> bool:
    """
    Check if repository needs config migration.
    
    Returns True if legacy config exists but new config doesn't.
    
    Args:
        repo_root: Path to repository root
        
    Returns:
        bool: True if migration needed
    """
    legacy_config = repo_root / "FreeCAD_Automation" / "config.json"
    new_config = repo_root / ".gitpdm" / "config.json"
    
    return legacy_config.exists() and not new_config.exists()


def migrate_config(repo_root: Path, backup: bool = True) -> MigrationResult:
    """
    Migrate configuration from legacy to new format.
    
    This function:
    1. Detects legacy FreeCAD_Automation/config.json
    2. Loads and parses it
    3. Creates .gitpdm directory
    4. Saves in native Python format
    5. Optionally backs up original
    6. Leaves migration breadcrumb
    
    Args:
        repo_root: Path to repository root
        backup: Whether to create backup of original (default: True)
        
    Returns:
        MigrationResult with details of operation
    """
    legacy_path = repo_root / "FreeCAD_Automation" / "config.json"
    new_path = repo_root / ".gitpdm" / "config.json"
    
    # Check if already using new format
    if new_path.exists():
        return MigrationResult(
            success=True,
            old_path=None,
            new_path=new_path,
            migrated=False,
            backup_path=None,
            message="Already using new configuration format"
        )
    
    # Check if legacy config exists
    if not legacy_path.exists():
        return MigrationResult(
            success=False,
            old_path=None,
            new_path=None,
            migrated=False,
            backup_path=None,
            message="No configuration file found (will use defaults)"
        )
    
    try:
        # Load legacy config
        log.info(f"Migrating config from {legacy_path}")
        with open(legacy_path, 'r') as f:
            legacy_data = json.load(f)
        
        # Parse into FCStdConfig
        config = FCStdConfig.from_dict(legacy_data)
        
        # Create new directory
        new_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Save in native format (simpler, Python-friendly)
        new_data = config.to_dict()
        with open(new_path, 'w') as f:
            json.dump(new_data, f, indent=2)
        
        log.info(f"Created new config at {new_path}")
        
        # Create backup if requested
        backup_path = None
        if backup:
            backup_path = legacy_path.parent / "config.json.backup"
            shutil.copy2(legacy_path, backup_path)
            log.info(f"Backed up original to {backup_path}")
        
        # Create migration marker
        _create_migration_marker(repo_root, legacy_path, new_path)
        
        return MigrationResult(
            success=True,
            old_path=legacy_path,
            new_path=new_path,
            migrated=True,
            backup_path=backup_path,
            message=f"Successfully migrated config from {legacy_path.name} to {new_path}"
        )
        
    except json.JSONDecodeError as e:
        log.error(f"Invalid JSON in legacy config: {e}")
        return MigrationResult(
            success=False,
            old_path=legacy_path,
            new_path=None,
            migrated=False,
            backup_path=None,
            message=f"Failed to parse legacy config: {e}"
        )
    except Exception as e:
        log.error(f"Migration failed: {e}")
        return MigrationResult(
            success=False,
            old_path=legacy_path,
            new_path=None,
            migrated=False,
            backup_path=None,
            message=f"Migration error: {e}"
        )


def _create_migration_marker(repo_root: Path, old_path: Path, new_path: Path):
    """
    Create a marker file indicating migration has occurred.
    
    This helps with debugging and provides information for users.
    """
    marker_file = old_path.parent / ".migrated_to_gitpdm"
    
    marker_content = f"""GitPDM Configuration Migration
==============================

This repository's configuration has been migrated to the new GitPDM format.

Old location: {old_path.relative_to(repo_root)}
New location: {new_path.relative_to(repo_root)}

The new configuration format is simpler and native to Python/GitPDM.
Your settings have been preserved.

You can safely delete the FreeCAD_Automation directory if you're not
using the legacy bash scripts anymore.

Migration performed: Sprint 4 (January 2026)
"""
    
    try:
        with open(marker_file, 'w') as f:
            f.write(marker_content)
        log.debug(f"Created migration marker at {marker_file}")
    except Exception as e:
        log.warning(f"Could not create migration marker: {e}")


def auto_migrate_if_needed(repo_root: Path) -> bool:
    """
    Automatically migrate config if legacy format detected.
    
    This is a convenience function that checks for legacy config
    and migrates automatically. Safe to call repeatedly.
    
    Args:
        repo_root: Path to repository root
        
    Returns:
        bool: True if migration performed or already using new format
    """
    if not needs_migration(repo_root):
        return True  # Already good
    
    result = migrate_config(repo_root)
    
    if result.success:
        log.info(f"Auto-migration complete: {result.message}")
        return True
    else:
        log.warning(f"Auto-migration failed: {result.message}")
        return False


def get_config_path(repo_root: Path) -> Path:
    """
    Get the configuration file path (new format preferred).
    
    This function determines which config path to use:
    - If new format exists, use it
    - If only legacy exists, use legacy (will auto-migrate later)
    - If neither exists, return new format path (for creation)
    
    Args:
        repo_root: Path to repository root
        
    Returns:
        Path where config should be read/written
    """
    new_path = repo_root / ".gitpdm" / "config.json"
    legacy_path = repo_root / "FreeCAD_Automation" / "config.json"
    
    # Prefer new format
    if new_path.exists():
        return new_path
    
    # Fall back to legacy if it exists
    if legacy_path.exists():
        log.warning(
            f"Using legacy config at {legacy_path}. "
            "Consider running migrate_config() to update."
        )
        return legacy_path
    
    # Neither exists - return new path for future creation
    return new_path


def load_config_with_migration(repo_root: Path) -> FCStdConfig:
    """
    Load configuration with automatic migration.
    
    This is the recommended way to load config in GitPDM code.
    It handles migration transparently.
    
    Args:
        repo_root: Path to repository root
        
    Returns:
        FCStdConfig object (with defaults if no config found)
    """
    from .config_manager import load_config
    
    # Try auto-migration first
    auto_migrate_if_needed(repo_root)
    
    # Now load from the appropriate location
    config_path = get_config_path(repo_root)
    
    if not config_path.exists():
        log.debug("No config file found, using defaults")
        return FCStdConfig()
    
    try:
        with open(config_path, 'r') as f:
            data = json.load(f)
        
        config = FCStdConfig.from_dict(data)
        log.debug(f"Loaded config from {config_path}")
        return config
        
    except Exception as e:
        log.error(f"Failed to load config from {config_path}: {e}")
        return FCStdConfig()


def save_config_new_format(repo_root: Path, config: FCStdConfig) -> Result:
    """
    Save configuration in new format (.gitpdm/config.json).
    
    This always saves to the new location, regardless of where
    it was loaded from.
    
    Args:
        repo_root: Path to repository root
        config: Configuration to save
        
    Returns:
        Result indicating success or failure
    """
    try:
        config_path = repo_root / ".gitpdm" / "config.json"
        
        # Create directory
        config_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Save in native format
        data = config.to_dict()
        with open(config_path, 'w') as f:
            json.dump(data, f, indent=2)
        
        log.info(f"Saved config to {config_path}")
        return Result.success(str(config_path))
        
    except PermissionError as e:
        return Result.failure("PERMISSION_DENIED", str(e))
    except Exception as e:
        log.error(f"Failed to save config: {e}")
        return Result.failure("SAVE_ERROR", str(e))
