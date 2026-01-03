"""
Initialize GitCAD in the GitPDM repository

This script copies the FreeCAD_Automation directory from GitCAD-main
to the root of GitPDM so it can work with the actual repo files.
"""
import os
import shutil
import json

# Paths
gitpdm_root = r"C:\Factorem\Nerd-Sniped\GitPDM"
gitcad_source = os.path.join(gitpdm_root, "GitCAD-main", "FreeCAD_Automation")
gitcad_dest = os.path.join(gitpdm_root, "FreeCAD_Automation")

print("GitCAD Installation for GitPDM Repository")
print("=" * 60)
print(f"Source: {gitcad_source}")
print(f"Destination: {gitcad_dest}")
print()

# Check if source exists
if not os.path.isdir(gitcad_source):
    print(f"ERROR: Source directory not found: {gitcad_source}")
    exit(1)

# Check if destination already exists
if os.path.exists(gitcad_dest):
    response = input(f"FreeCAD_Automation already exists at {gitcad_dest}. Overwrite? (y/n): ")
    if response.lower() != 'y':
        print("Cancelled.")
        exit(0)
    print("Removing existing directory...")
    shutil.rmtree(gitcad_dest)

# Copy the directory
print("Copying FreeCAD_Automation directory...")
shutil.copytree(gitcad_source, gitcad_dest)
print("✓ Directory copied")

# Create default config.json
config_path = os.path.join(gitcad_dest, "config.json")
if not os.path.exists(config_path):
    print("\nCreating default config.json...")
    default_config = {
        "git_relative_project_path": "",
        "python_path": ""
    }
    with open(config_path, 'w') as f:
        json.dump(default_config, f, indent=4)
    print(f"✓ Created config.json with defaults")
else:
    print(f"✓ config.json already exists")

# Check if .gitattributes exists (needed for git LFS filters)
gitattributes_path = os.path.join(gitpdm_root, ".gitattributes")
if not os.path.exists(gitattributes_path):
    print("\n⚠ WARNING: .gitattributes not found")
    print("GitCAD requires .gitattributes for git clean/smudge filters")
    print("You should copy it from GitCAD-main or run the GitCAD setup.")
else:
    print("✓ .gitattributes exists")

# Check if Git LFS is installed
print("\n" + "=" * 60)
print("GitCAD Installation Complete!")
print()
print("Next steps:")
print("1. Install git-lfs if not already installed: git lfs install")
print("2. Setup GitCAD filters by running hooks in FreeCAD_Automation/")
print("3. Reload FreeCAD or refresh the GitPDM panel")
print("4. GitCAD should now show as available")
