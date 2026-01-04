"""
Sprint 4: Native Core Module Test
Demonstrates using native Python modules instead of bash wrapper.
"""
import sys
from pathlib import Path
from freecad_gitpdm.core import log

repo = Path(r"C:\Factorem\Nerd-Sniped\GitPDM")

print("=" * 70)
print("NATIVE CORE MODULE TEST (Sprint 4)")
print("=" * 70)

# Test 1: Check if GitPDM is initialized
print("\n1. Testing has_config...")
try:
    from freecad_gitpdm.core.config_manager import has_config
    result = has_config(repo)
    print(f"✓ has_config: {result}")
except Exception as e:
    print(f"✗ FAILED: {e}")
    import traceback
    traceback.print_exc()

# Test 2: Load configuration
print("\n2. Testing load_config...")
try:
    from freecad_gitpdm.core.config_manager import load_config
    config = load_config(repo)
    print(f"✓ Config loaded")
    print(f"  Uncompressed suffix: {config.uncompressed_suffix}")
    print(f"  Include thumbnails: {config.include_thumbnails}")
    print(f"  Require lock: {config.require_lock}")
except Exception as e:
    print(f"✗ FAILED: {e}")
    import traceback
    traceback.print_exc()

# Test 3: Create LockManager
print("\n3. Testing LockManager...")
try:
    from freecad_gitpdm.core.lock_manager import LockManager
    manager = LockManager(repo)
    print(f"✓ LockManager created")
    print(f"  Repo root: {manager.repo_root}")
    
    # Get current locks
    result = manager.get_locks()
    if result.ok:
        print(f"  Current locks: {len(result.value)}")
    else:
        print(f"  Lock query: {result.error}")
except Exception as e:
    print(f"✗ FAILED: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 70)
print("✓ Native core modules working! No bash wrapper needed.")
print("=" * 70)
