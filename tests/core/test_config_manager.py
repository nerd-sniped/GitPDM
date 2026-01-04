# -*- coding: utf-8 -*-
"""
Tests for config_manager module
Sprint 1: Configuration management testing
"""

import pytest
from pathlib import Path
import tempfile
import json

from freecad_gitpdm.core.config_manager import (
    FCStdConfig,
    load_config,
    save_config,
    get_uncompressed_dir,
    create_default_config
)


@pytest.fixture
def temp_repo():
    """Create a temporary repository for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo = Path(tmpdir)
        (repo / ".git").mkdir()
        (repo / "FreeCAD_Automation").mkdir()
        yield repo


class TestFCStdConfig:
    """Tests for FCStdConfig dataclass."""
    
    def test_default_config(self):
        """Test default configuration values."""
        config = FCStdConfig()
        
        assert config.uncompressed_suffix == "_uncompressed"
        assert config.uncompressed_prefix == ""
        assert config.subdirectory_mode is False
        assert config.require_lock is True
        assert config.compress_binaries is True
    
    def test_binary_patterns_default(self):
        """Test that binary patterns have defaults."""
        config = FCStdConfig()
        
        assert config.binary_patterns is not None
        assert len(config.binary_patterns) > 0
        assert "*.brp" in config.binary_patterns
    
    def test_from_dict_our_format(self):
        """Test loading from our dictionary format."""
        data = {
            "uncompressed_suffix": "_data",
            "uncompressed_prefix": "uc_",
            "subdirectory_mode": True,
            "require_lock": False
        }
        
        config = FCStdConfig.from_dict(data)
        
        assert config.uncompressed_suffix == "_data"
        assert config.uncompressed_prefix == "uc_"
        assert config.subdirectory_mode is True
        assert config.require_lock is False
    
    def test_from_dict_gitcad_format(self):
        """Test loading from GitCAD's config.json format."""
        data = {
            "require-lock-to-modify-FreeCAD-files": True,
            "include-thumbnails": False,
            "uncompressed-directory-structure": {
                "uncompressed-directory-suffix": "_uc",
                "uncompressed-directory-prefix": "pre_",
                "subdirectory": {
                    "put-uncompressed-directory-in-subdirectory": True,
                    "subdirectory-name": ".data"
                }
            },
            "compress-non-human-readable-FreeCAD-files": {
                "enabled": False,
                "files-to-compress": ["*.brp"],
                "compression-level": 9
            }
        }
        
        config = FCStdConfig.from_dict(data)
        
        assert config.uncompressed_suffix == "_uc"
        assert config.uncompressed_prefix == "pre_"
        assert config.subdirectory_mode is True
        assert config.subdirectory_name == ".data"
        assert config.compress_binaries is False
        assert config.compression_level == 9
    
    def test_to_gitcad_format(self):
        """Test converting to GitCAD format."""
        config = FCStdConfig(
            uncompressed_suffix="_test",
            require_lock=False
        )
        
        data = config.to_gitcad_format()
        
        assert "uncompressed-directory-structure" in data
        assert data["uncompressed-directory-structure"]["uncompressed-directory-suffix"] == "_test"
        assert data["require-lock-to-modify-FreeCAD-files"] is False
    
    def test_roundtrip_conversion(self):
        """Test that we can convert to GitCAD format and back."""
        original = FCStdConfig(
            uncompressed_suffix="_test",
            subdirectory_mode=True,
            compression_level=7
        )
        
        gitcad_format = original.to_gitcad_format()
        restored = FCStdConfig.from_dict(gitcad_format)
        
        assert restored.uncompressed_suffix == original.uncompressed_suffix
        assert restored.subdirectory_mode == original.subdirectory_mode
        assert restored.compression_level == original.compression_level


class TestLoadConfig:
    """Tests for load_config function."""
    
    def test_load_existing_config(self, temp_repo):
        """Test loading an existing config file."""
        config_file = temp_repo / "FreeCAD_Automation" / "config.json"
        
        # Create a config file
        test_config = FCStdConfig(uncompressed_suffix="_test")
        with open(config_file, 'w') as f:
            json.dump(test_config.to_gitcad_format(), f)
        
        # Load it
        loaded = load_config(temp_repo)
        
        assert loaded.uncompressed_suffix == "_test"
    
    def test_load_missing_config(self, temp_repo):
        """Test loading when no config file exists (use defaults)."""
        # Don't create config file
        
        config = load_config(temp_repo)
        
        # Should return defaults
        assert config.uncompressed_suffix == "_uncompressed"
    
    def test_load_invalid_json(self, temp_repo):
        """Test handling invalid JSON gracefully."""
        config_file = temp_repo / "FreeCAD_Automation" / "config.json"
        config_file.write_text("{ invalid json }")
        
        # Should return defaults without crashing
        config = load_config(temp_repo)
        
        assert config.uncompressed_suffix == "_uncompressed"


class TestSaveConfig:
    """Tests for save_config function."""
    
    def test_save_config(self, temp_repo):
        """Test saving configuration to file."""
        config = FCStdConfig(uncompressed_suffix="_saved")
        
        result = save_config(temp_repo, config)
        
        assert result.ok
        
        # Verify file was created
        config_file = temp_repo / "FreeCAD_Automation" / "config.json"
        assert config_file.exists()
        
        # Verify contents
        with open(config_file) as f:
            data = json.load(f)
        
        assert data["uncompressed-directory-structure"]["uncompressed-directory-suffix"] == "_saved"
    
    def test_save_creates_directory(self):
        """Test that save creates directory if needed."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = Path(tmpdir)
            (repo / ".git").mkdir()
            # Don't create FreeCAD_Automation
            
            config = FCStdConfig()
            result = save_config(repo, config)
            
            assert result.ok
            assert (repo / "FreeCAD_Automation" / "config.json").exists()


class TestGetUncompressedDir:
    """Tests for get_uncompressed_dir function."""
    
    def test_basic_uncompressed_dir(self, temp_repo):
        """Test basic uncompressed directory calculation."""
        config = FCStdConfig()
        
        uncompressed = get_uncompressed_dir(
            temp_repo,
            "test.FCStd",
            config
        )
        
        assert uncompressed == temp_repo / "test_uncompressed"
    
    def test_with_subdirectory(self, temp_repo):
        """Test with subdirectory in path."""
        config = FCStdConfig()
        
        uncompressed = get_uncompressed_dir(
            temp_repo,
            "parts/bracket.FCStd",
            config
        )
        
        assert uncompressed == temp_repo / "parts" / "bracket_uncompressed"
    
    def test_with_prefix_suffix(self, temp_repo):
        """Test with custom prefix and suffix."""
        config = FCStdConfig(
            uncompressed_prefix="uc_",
            uncompressed_suffix="_data"
        )
        
        uncompressed = get_uncompressed_dir(
            temp_repo,
            "test.FCStd",
            config
        )
        
        assert uncompressed == temp_repo / "uc_test_data"
    
    def test_with_subdirectory_mode(self, temp_repo):
        """Test with subdirectory mode enabled."""
        config = FCStdConfig(
            subdirectory_mode=True,
            subdirectory_name=".freecad_data"
        )
        
        uncompressed = get_uncompressed_dir(
            temp_repo,
            "test.FCStd",
            config
        )
        
        assert uncompressed == temp_repo / ".freecad_data" / "test_uncompressed"
    
    def test_loads_config_if_none(self, temp_repo):
        """Test that it loads config if not provided."""
        # Create a config file with custom suffix
        config_file = temp_repo / "FreeCAD_Automation" / "config.json"
        test_config = FCStdConfig(uncompressed_suffix="_custom")
        with open(config_file, 'w') as f:
            json.dump(test_config.to_gitcad_format(), f)
        
        # Don't pass config parameter
        uncompressed = get_uncompressed_dir(
            temp_repo,
            "test.FCStd"
        )
        
        # Should use loaded config
        assert "_custom" in str(uncompressed)


class TestCreateDefaultConfig:
    """Tests for create_default_config function."""
    
    def test_creates_default(self):
        """Test creating default configuration."""
        config = create_default_config()
        
        assert isinstance(config, FCStdConfig)
        assert config.uncompressed_suffix == "_uncompressed"
        assert config.require_lock is True
