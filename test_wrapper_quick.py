#!/usr/bin/env python
"""
Quick GitCAD Wrapper Test (DEPRECATED)

⚠️ DEPRECATED - Sprint 5
This test file is for the deprecated bash wrapper layer.
The wrapper has been removed in Sprint 5, and GitCAD-main directory was removed in Sprint 3.

Use the native core modules instead:
    from freecad.gitpdm.core.fcstd_tool import export_fcstd, import_fcstd
    from freecad.gitpdm.core.lock_manager import LockManager
    from freecad.gitpdm.core.config_manager import load_config, save_config

For proper testing, see tests/core/ directory.
"""

import sys

print("\n" + "=" * 70)
print("⚠️  GitCAD Wrapper Test - DEPRECATED")
print("=" * 70)
print("\nThis test is deprecated. The gitcad wrapper layer has been removed.")
print("The GitCAD-main directory has also been removed (Sprint 3).")
print("\nUse native core modules:")
print("   >>> from freecad.gitpdm.core.fcstd_tool import export_fcstd")
print("   >>> from freecad.gitpdm.core.lock_manager import LockManager")
print("   >>> from freecad.gitpdm.core.config_manager import load_config")
print("\nSee tests/core/ for up-to-date unit tests.")
print("=" * 70)
sys.exit(0)
        print(f"  Has init-repo script: {status.has_init_script}")
        print(f"  Has git hooks: {status.has_git_hooks}")
        
        if status.missing_components:
            print(f"  Missing: {', '.join(status.missing_components)}")
        
        if status.warnings:
            print("  Warnings:")
            for warning in status.warnings:
                print(f"    - {warning}")
        print("✓ Status check complete\n")
    else:
        print(f"✗ FAILED: {result.error}\n")
except Exception as e:
    print(f"✗ FAILED: {e}\n")

# Test 4: Find .FCStd files
print("Test 4: Finding .FCStd files...")
try:
    files = find_fcstd_files(REPO_PATH)
    print(f"✓ Found {len(files)} .FCStd file(s):")
    for f in files:
        print(f"    - {f}")
    print()
except Exception as e:
    print(f"✗ FAILED: {e}\n")

# Test 5: Check bash availability
print("Test 5: Checking for bash executable...")
try:
    from freecad.gitpdm.gitcad.wrapper import _find_bash_executable
    bash = _find_bash_executable()
    if bash:
        print(f"✓ Bash found: {bash}\n")
    else:
        print("✗ WARNING: Bash not found (Git Bash required on Windows)\n")
except Exception as e:
    print(f"✗ FAILED: {e}\n")

# Test 6: Try loading config (may not exist yet)
print("Test 6: Loading configuration...")
try:
    result = load_gitcad_config(REPO_PATH)
    if result.ok:
        config = result.value
        print(f"✓ Config loaded:")
        print(f"    FreeCAD Python: {config.freecad_python_instance_path or '(not set)'}")
        print(f"    Require locks: {config.require_lock_to_modify_freecad_files}")
        print(f"    Uncompressed suffix: {config.uncompressed_directory_structure.uncompressed_directory_suffix}")
        print()
    else:
        print(f"⚠ Config not found (this is normal if not initialized yet)")
        print(f"   Error: {result.error}\n")
except Exception as e:
    print(f"✗ FAILED: {e}\n")

# Test 7: Try creating wrapper instance
print("Test 7: Creating GitCADWrapper instance...")
try:
    wrapper = GitCADWrapper(REPO_PATH)
    print(f"✓ Wrapper created successfully:")
    print(f"    Repo root: {wrapper.repo_root}")
    print(f"    Config file exists: {wrapper.paths.config_file.exists()}")
    print(f"    FCStd tool exists: {wrapper.paths.fcstd_tool.exists()}")
    print(f"    Bash exe: {wrapper._bash_exe}")
    print()
except Exception as e:
    print(f"⚠ Could not create wrapper: {e}")
    print(f"   (This may be normal if GitCAD not fully set up)\n")

print("=" * 70)
print("Test Complete!")
print("=" * 70)
print("\nNext steps:")
print("1. If config.json doesn't exist, you can create it:")
print("   >>> from freecad.gitpdm.gitcad import create_default_config")
print(f"   >>> result = create_default_config(r'{REPO_PATH}')")
print("   >>> print(result.value if result.ok else result.error)")
print("\n2. Edit config.json to add your FreeCAD Python path")
print("\n3. Run GitCAD's init-repo script to set up git hooks")
print("=" * 70 + "\n")
