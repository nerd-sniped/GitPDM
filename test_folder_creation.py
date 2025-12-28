#!/usr/bin/env python3
"""Test script to debug folder creation issues."""

import os
import pathlib

# Test the exact path the user is trying
test_path = r"C:\Users\Ryank\Desktop\Sandbox\testproject"

print(f"Testing folder creation at: {test_path}")
print()

# Check parent
parent = os.path.dirname(test_path)
print(f"Parent directory: {parent}")
print(f"Parent exists: {os.path.exists(parent)}")
print(f"Parent is dir: {os.path.isdir(parent)}")
print()

# Normalize path (like we do in the wizard)
test_path_abs = os.path.normpath(os.path.abspath(test_path))
print(f"Normalized path: {test_path_abs}")
print(f"Normalized == original: {test_path_abs == test_path}")
print()

# Try creating with os.makedirs
print("Creating directory...")
try:
    os.makedirs(test_path_abs, exist_ok=True)
    print("  makedirs() returned successfully")
except Exception as e:
    print(f"  makedirs() raised: {type(e).__name__}: {e}")

# Check with os.path.exists
print()
print("Checking with os.path.exists():")
exists_os = os.path.exists(test_path_abs)
print(f"  Result: {exists_os}")

# Check with os.path.isdir
print()
print("Checking with os.path.isdir():")
isdir_os = os.path.isdir(test_path_abs)
print(f"  Result: {isdir_os}")

# Check with pathlib
print()
print("Checking with pathlib.Path:")
path_obj = pathlib.Path(test_path_abs)
exists_pathlib = path_obj.exists()
is_dir_pathlib = path_obj.is_dir()
print(f"  .exists(): {exists_pathlib}")
print(f"  .is_dir(): {is_dir_pathlib}")

# Check if we can list parent directory
print()
print("Listing parent directory:")
try:
    items = os.listdir(parent)
    print(f"  Items in parent: {items}")
    if "testproject" in items:
        print(f"  ✓ testproject IS in the listing")
    else:
        print(f"  ✗ testproject NOT in the listing")
except Exception as e:
    print(f"  Error listing: {e}")

# Final check - list with pathlib
print()
print("Listing parent with pathlib:")
try:
    parent_path = pathlib.Path(parent)
    items = list(parent_path.iterdir())
    item_names = [p.name for p in items]
    print(f"  Items: {item_names}")
    if "testproject" in item_names:
        print(f"  ✓ testproject IS in the pathlib listing")
    else:
        print(f"  ✗ testproject NOT in the pathlib listing")
except Exception as e:
    print(f"  Error listing with pathlib: {e}")
