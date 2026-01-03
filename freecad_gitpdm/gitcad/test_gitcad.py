# -*- coding: utf-8 -*-
"""
GitCAD Integration Test Script
Simple test to verify GitCAD wrapper functionality.
"""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from freecad_gitpdm.gitcad import (
    is_gitcad_initialized,
    check_gitcad_status,
    load_gitcad_config,
    find_fcstd_files,
    GitCADWrapper,
)
from freecad_gitpdm.core import log


def test_gitcad_detection(repo_root: str):
    """Test GitCAD detection in repository."""
    print("\n" + "=" * 70)
    print("GitCAD Integration Test")
    print("=" * 70)

    print(f"\nTesting repository: {repo_root}")

    # Test 1: Check if GitCAD is initialized
    print("\n--- Test 1: GitCAD Initialization Check ---")
    is_init = is_gitcad_initialized(repo_root)
    print(f"Is GitCAD initialized: {is_init}")

    # Test 2: Get detailed status
    print("\n--- Test 2: Detailed Status Check ---")
    status_result = check_gitcad_status(repo_root)
    if status_result.ok:
        status = status_result.value
        print(f"Is initialized: {status.is_initialized}")
        print(f"Has config: {status.has_config}")
        print(f"Has FCStd tool: {status.has_fcstd_tool}")
        print(f"Has init script: {status.has_init_script}")
        print(f"Has git hooks: {status.has_git_hooks}")
        print(f"Config valid: {status.config_valid}")
        print(f"FreeCAD Python configured: {status.freecad_python_configured}")

        if status.missing_components:
            print(f"\nMissing components: {', '.join(status.missing_components)}")

        if status.warnings:
            print("\nWarnings:")
            for warning in status.warnings:
                print(f"  - {warning}")
    else:
        print(f"Error checking status: {status_result.error}")

    # Test 3: Load config
    if is_init:
        print("\n--- Test 3: Load Configuration ---")
        config_result = load_gitcad_config(repo_root)
        if config_result.ok:
            config = config_result.value
            print(f"FreeCAD Python path: {config.freecad_python_instance_path}")
            print(f"Require locks: {config.require_lock_to_modify_freecad_files}")
            print(f"Include thumbnails: {config.include_thumbnails}")
            print(
                f"Uncompressed suffix: {config.uncompressed_directory_structure.uncompressed_directory_suffix}"
            )
            print(
                f"Compress binaries: {config.compress_non_human_readable_freecad_files.enabled}"
            )
        else:
            print(f"Error loading config: {config_result.error}")

        # Test 4: Find .FCStd files
        print("\n--- Test 4: Find .FCStd Files ---")
        fcstd_files = find_fcstd_files(repo_root)
        print(f"Found {len(fcstd_files)} .FCStd files:")
        for fcstd_file in fcstd_files[:5]:  # Show first 5
            print(f"  - {fcstd_file}")
        if len(fcstd_files) > 5:
            print(f"  ... and {len(fcstd_files) - 5} more")

        # Test 5: Create wrapper and get locks
        print("\n--- Test 5: Get Lock Status ---")
        try:
            wrapper = GitCADWrapper(repo_root)
            locks_result = wrapper.get_locks()
            if locks_result.ok:
                locks = locks_result.value
                print(f"Found {len(locks)} locked files:")
                for lock in locks:
                    print(f"  - {lock.path} (owner: {lock.owner}, ID: {lock.lock_id})")
                if not locks:
                    print("  (No files currently locked)")
            else:
                print(f"Error getting locks: {locks_result.error}")
        except Exception as e:
            print(f"Could not create wrapper: {e}")

    print("\n" + "=" * 70)
    print("Test Complete")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    # Test with current repository (should have GitCAD-main)
    repo_root = Path(__file__).parent.parent.parent
    test_gitcad_detection(str(repo_root))

    # Also test GitCAD-main folder specifically
    gitcad_repo = repo_root / "GitCAD-main"
    if gitcad_repo.exists():
        print("\n\nTesting GitCAD-main folder specifically:")
        test_gitcad_detection(str(gitcad_repo))
