"""
Configuration Manager - Core Module
Sprint 1: Unified configuration management for FCStd handling

This module manages configuration for FCStd file operations,
providing a unified interface that's backward compatible with
GitCAD's config.json format.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional
from dataclasses import dataclass, asdict

from .result import Result
from . import log


@dataclass
class FCStdConfig:
    """
    Configuration for FCStd file handling.
    
    This dataclass provides a typed interface to GitCAD's config.json,
    with sensible defaults for when no configuration file exists.
    """
    
    # Uncompressed directory naming
    uncompressed_suffix: str = "_uncompressed"
    uncompressed_prefix: str = ""
    
    # Subdirectory mode
    subdirectory_mode: bool = False
    subdirectory_name: str = ".freecad_data"
    
    # File handling
    include_thumbnails: bool = False
    require_lock: bool = True
    
    # Binary compression
    compress_binaries: bool = True
    binary_patterns: list[str] = None
    max_compressed_size_gb: float = 2.0
    compression_level: int = 6
    zip_file_prefix: str = "binaries_"
    
    def __post_init__(self):
        """Set default binary patterns if not provided."""
        if self.binary_patterns is None:
            self.binary_patterns = [
                "*.brp",
                "*.Map.*",
                "no_extension/*"
            ]
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict) -> FCStdConfig:
        """
        Create FCStdConfig from dictionary.
        
        Handles both our format and GitCAD's original format.
        """
        # If it's already in our format, use directly
        if "uncompressed_suffix" in data:
            return cls(**data)
        
        # Otherwise, parse GitCAD format
        return cls._from_gitcad_format(data)
    
    @classmethod
    def _from_gitcad_format(cls, data: dict) -> FCStdConfig:
        """Parse GitCAD's config.json format."""
        struct = data.get("uncompressed-directory-structure", {})
        compress = data.get("compress-non-human-readable-FreeCAD-files", {})
        
        return cls(
            uncompressed_suffix=struct.get("uncompressed-directory-suffix", "_uncompressed"),
            uncompressed_prefix=struct.get("uncompressed-directory-prefix", ""),
            subdirectory_mode=struct.get("subdirectory", {}).get(
                "put-uncompressed-directory-in-subdirectory", False
            ),
            subdirectory_name=struct.get("subdirectory", {}).get(
                "subdirectory-name", ".freecad_data"
            ),
            include_thumbnails=data.get("include-thumbnails", False),
            require_lock=data.get("require-lock-to-modify-FreeCAD-files", True),
            compress_binaries=compress.get("enabled", True),
            binary_patterns=compress.get("files-to-compress", [
                "*.brp", "*.Map.*", "no_extension/*"
            ]),
            max_compressed_size_gb=compress.get("max-compressed-file-size-gigabyte", 2.0),
            compression_level=compress.get("compression-level", 6),
            zip_file_prefix=compress.get("zip-file-prefix", "binaries_"),
        )
    
    def to_gitcad_format(self) -> dict:
        """
        Convert to GitCAD's config.json format for backward compatibility.
        
        Returns:
            Dictionary in GitCAD format
        """
        return {
            "freecad-python-instance-path": "",
            "require-lock-to-modify-FreeCAD-files": self.require_lock,
            "require-GitCAD-activation": False,
            "include-thumbnails": self.include_thumbnails,
            "uncompressed-directory-structure": {
                "uncompressed-directory-suffix": self.uncompressed_suffix,
                "uncompressed-directory-prefix": self.uncompressed_prefix,
                "subdirectory": {
                    "put-uncompressed-directory-in-subdirectory": self.subdirectory_mode,
                    "subdirectory-name": self.subdirectory_name
                }
            },
            "compress-non-human-readable-FreeCAD-files": {
                "enabled": self.compress_binaries,
                "files-to-compress": self.binary_patterns,
                "max-compressed-file-size-gigabyte": self.max_compressed_size_gb,
                "compression-level": self.compression_level,
                "zip-file-prefix": self.zip_file_prefix
            }
        }


def has_config(repo_root: Path | str) -> bool:
    """
    Check if GitPDM/GitCAD is initialized (config.json exists).
    
    This is a lightweight check that only looks for the config file,
    without loading or validating it.
    
    Checks both new (.gitpdm/config.json) and legacy (FreeCAD_Automation/config.json) locations.
    
    Args:
        repo_root: Path to git repository root
        
    Returns:
        bool: True if config.json exists
        
    Example:
        >>> if has_config("/path/to/repo"):
        ...     config = load_config("/path/to/repo")
    """
    if isinstance(repo_root, str):
        repo_root = Path(repo_root)
    
    # Check new location first
    new_config = repo_root / ".gitpdm" / "config.json"
    if new_config.exists():
        return True
    
    # Check legacy location for backward compatibility
    legacy_config = repo_root / "FreeCAD_Automation" / "config.json"
    return legacy_config.exists()


def load_config(repo_root: Path) -> FCStdConfig:
    """
    Load configuration from .gitpdm/config.json or legacy location, or use defaults.
    
    Automatically detects and migrates from legacy FreeCAD_Automation/config.json.
    
    Args:
        repo_root: Path to git repository root
        
    Returns:
        FCStdConfig object with loaded or default configuration
        
    Example:
        >>> config = load_config(Path("/path/to/repo"))
        >>> print(config.uncompressed_suffix)
        '_uncompressed'
    """
    # Try new location first
    new_config = repo_root / ".gitpdm" / "config.json"
    legacy_config = repo_root / "FreeCAD_Automation" / "config.json"
    
    config_file = new_config if new_config.exists() else legacy_config
    
    if not config_file.exists():
        log.debug(f"No config file found at {config_file}, using defaults")
        return FCStdConfig()
    
    try:
        with open(config_file, 'r') as f:
            data = json.load(f)
        
        config = FCStdConfig.from_dict(data)
        log.debug(f"Loaded config from {config_file}")
        return config
        
    except json.JSONDecodeError as e:
        log.error(f"Invalid JSON in config file: {e}")
        log.info("Using default configuration")
        return FCStdConfig()
    except Exception as e:
        log.error(f"Failed to load config: {e}")
        return FCStdConfig()


def save_config(repo_root: Path, config: FCStdConfig) -> Result:
    """
    Save configuration to .gitpdm/config.json (new native format).
    
    Args:
        repo_root: Path to git repository root
        config: Configuration to save
        
    Returns:
        Result indicating success or failure
    """
    try:
        # Always save to new location
        config_file = repo_root / ".gitpdm" / "config.json"
        
        # Create directory if needed
        config_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Save in native Python format (simpler than GitCAD format)
        data = config.to_dict()
        
        with open(config_file, 'w') as f:
            json.dump(data, f, indent=2)
        
        log.info(f"Saved config to {config_file}")
        return Result.success(str(config_file))
        
    except PermissionError as e:
        return Result.failure("PERMISSION_DENIED", str(e))
    except Exception as e:
        log.error(f"Failed to save config: {e}")
        return Result.failure("SAVE_ERROR", str(e))


def get_uncompressed_dir(
    repo_root: Path,
    fcstd_path: str,
    config: Optional[FCStdConfig] = None
) -> Path:
    """
    Calculate the uncompressed directory path for a .FCStd file.
    
    This applies the configuration rules (prefix, suffix, subdirectory)
    to determine where the uncompressed version should be stored.
    
    Args:
        repo_root: Path to repository root
        fcstd_path: Relative path to .FCStd file (or just filename)
        config: Configuration to use (loads if None)
        
    Returns:
        Path to uncompressed directory
        
    Example:
        >>> dir_path = get_uncompressed_dir(
        ...     Path("/repo"),
        ...     "parts/bracket.FCStd",
        ...     config
        ... )
        >>> print(dir_path)
        /repo/parts/bracket_uncompressed
    """
    if config is None:
        config = load_config(repo_root)
    
    # Parse the FCStd path
    fcstd_path = Path(fcstd_path)
    
    # If it's absolute, make it relative to repo_root
    if fcstd_path.is_absolute():
        try:
            fcstd_path = fcstd_path.relative_to(repo_root)
        except ValueError:
            # Not under repo_root, just use the name
            fcstd_path = Path(fcstd_path.name)
    
    # Get the base name without extension
    base_name = fcstd_path.stem  # "bracket.FCStd" -> "bracket"
    
    # Apply prefix and suffix
    dir_name = f"{config.uncompressed_prefix}{base_name}{config.uncompressed_suffix}"
    
    # Determine parent directory
    parent = repo_root / fcstd_path.parent
    
    # Apply subdirectory mode if configured
    if config.subdirectory_mode:
        uncompressed_dir = parent / config.subdirectory_name / dir_name
    else:
        uncompressed_dir = parent / dir_name
    
    return uncompressed_dir


def create_default_config() -> FCStdConfig:
    """
    Create a new configuration with default values.
    
    Returns:
        FCStdConfig with default settings
    """
    return FCStdConfig()
