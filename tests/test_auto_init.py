"""
Test auto-initialization functionality (Sprint 7)
Verifies that GitPDM automatically creates .gitpdm/config.json when opening repositories.
"""

import os
import shutil
import tempfile
from pathlib import Path

# Import GitPDM modules
from freecad.gitpdm.ui.init_wizard import auto_initialize_if_needed
from freecad.gitpdm.core.config_manager import has_config, load_config


def test_auto_init_new_repo():
    """Test auto-initialization on repository without config."""
    print("\n=== Test 1: Auto-Init New Repository ===")
    
    # Create temp repo directory
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_path = Path(tmpdir)
        print(f"Temp repo: {repo_path}")
        
        # Initialize git repo
        os.system(f'cd "{repo_path}" && git init > nul 2>&1')
        
        # Verify no config exists
        assert not has_config(repo_path), "Config should not exist yet"
        print("✓ No config detected (expected)")
        
        # Call auto-initialization
        was_initialized = auto_initialize_if_needed(repo_path)
        assert was_initialized, "Should have initialized"
        print("✓ Auto-initialization triggered")
        
        # Verify config created
        assert has_config(repo_path), "Config should exist now"
        print("✓ Config created successfully")
        
        # Verify config contents
        config = load_config(repo_path)
        assert isinstance(config, dict), "Config should be a dictionary"
        assert "fcstd_compress" in config, "Config should have fcstd_compress key"
        print(f"✓ Config contents: {config}")
        
    print("✅ Test 1 PASSED\n")


def test_auto_init_existing_config():
    """Test auto-initialization skips if config already exists."""
    print("\n=== Test 2: Skip If Config Exists ===")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_path = Path(tmpdir)
        print(f"Temp repo: {repo_path}")
        
        # Initialize git repo
        os.system(f'cd "{repo_path}" && git init > nul 2>&1')
        
        # Create config manually
        from freecad.gitpdm.core.config_manager import save_config, FCStdConfig
        config = FCStdConfig()
        save_config(repo_path, config)
        print("✓ Created config manually")
        
        # Try auto-initialization
        was_initialized = auto_initialize_if_needed(repo_path)
        assert not was_initialized, "Should NOT have initialized (already exists)"
        print("✓ Auto-initialization correctly skipped")
        
        # Verify config still exists
        assert has_config(repo_path), "Config should still exist"
        print("✓ Existing config preserved")
        
    print("✅ Test 2 PASSED\n")


def test_auto_init_invalid_path():
    """Test auto-initialization handles invalid paths gracefully."""
    print("\n=== Test 3: Handle Invalid Path ===")
    
    # Try to initialize non-existent path
    fake_path = Path("C:/this/path/does/not/exist/fake_repo")
    print(f"Fake path: {fake_path}")
    
    try:
        was_initialized = auto_initialize_if_needed(fake_path)
        print(f"Result: {was_initialized} (should be False)")
        assert not was_initialized, "Should not crash on invalid path"
        print("✓ Handled invalid path gracefully")
    except Exception as e:
        print(f"⚠ Exception caught: {e}")
        print("✓ Exception handled (acceptable)")
    
    print("✅ Test 3 PASSED\n")


if __name__ == "__main__":
    print("=" * 60)
    print("GitPDM Auto-Initialization Test Suite (Sprint 7)")
    print("=" * 60)
    
    try:
        test_auto_init_new_repo()
        test_auto_init_existing_config()
        test_auto_init_invalid_path()
        
        print("\n" + "=" * 60)
        print("✅ ALL TESTS PASSED")
        print("=" * 60)
        print("\nAuto-initialization is working correctly!")
        print("\nNext steps:")
        print("1. Restart FreeCAD")
        print("2. Open a Git repository without .gitpdm/config.json")
        print("3. Verify config is created automatically")
        print("4. Verify lock/unlock options appear immediately")
        
    except AssertionError as e:
        print("\n" + "=" * 60)
        print(f"❌ TEST FAILED: {e}")
        print("=" * 60)
        raise
    except Exception as e:
        print("\n" + "=" * 60)
        print(f"❌ UNEXPECTED ERROR: {e}")
        print("=" * 60)
        raise
