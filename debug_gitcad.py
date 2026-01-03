"""
Debug script to run in FreeCAD Python console to diagnose GitCAD initialization
Run this line by line in the console to see where it fails
"""
import sys
print("Python version:", sys.version)

# Step 1: Check import
print("\n=== Testing imports ===")
try:
    from freecad_gitpdm.gitcad import is_gitcad_initialized, GitCADWrapper
    print("✓ Import successful")
except Exception as e:
    print(f"✗ Import failed: {e}")
    import traceback
    traceback.print_exc()

# Step 2: Check if GitCAD directory exists
print("\n=== Checking GitCAD directory ===")
import os
repo_root = r"C:\Factorem\Nerd-Sniped\GitPDM\GitCAD-main"
automation_dir = os.path.join(repo_root, "FreeCAD_Automation")
print(f"Repo root: {repo_root}")
print(f"Automation dir exists: {os.path.isdir(automation_dir)}")

# Step 3: Test is_gitcad_initialized
print("\n=== Testing is_gitcad_initialized ===")
try:
    result = is_gitcad_initialized(repo_root)
    print(f"is_gitcad_initialized result: {result}")
except Exception as e:
    print(f"✗ is_gitcad_initialized failed: {e}")
    import traceback
    traceback.print_exc()

# Step 4: Try to create GitCADWrapper
print("\n=== Testing GitCADWrapper creation ===")
try:
    wrapper = GitCADWrapper(repo_root)
    print(f"✓ GitCADWrapper created successfully")
    print(f"  Bash path: {wrapper.bash_path}")
    print(f"  Automation dir: {wrapper.automation_dir}")
except Exception as e:
    print(f"✗ GitCADWrapper creation failed: {e}")
    import traceback
    traceback.print_exc()

# Step 5: Check if config.json exists
print("\n=== Checking config.json ===")
config_path = os.path.join(automation_dir, "config.json")
print(f"Config path: {config_path}")
print(f"Config exists: {os.path.exists(config_path)}")

print("\n=== Debug complete ===")
