#!/usr/bin/env python3
"""
Simulate the exact folder creation code from the wizard in isolation.
This helps identify if the problem is in Qt/wizard context or the code itself.
"""

import os
import sys

# Add the project to path
sys.path.insert(0, r"C:\nerd-sniped\GitPDM")

from freecad_gitpdm.core import log

def simulate_wizard_folder_creation():
    """Simulate exactly what happens in the wizard."""
    
    print("=" * 70)
    print("SIMULATING WIZARD FOLDER CREATION")
    print("=" * 70)
    
    # Simulate wizard inputs
    inputs = {
        "folder": r"C:\Users\Ryank\Desktop\Sandbox\testproject_sim",
        "name": "testproject_sim",
        "private": False,
        "description": "Simulation test",
    }
    
    folder = inputs["folder"]
    name = inputs["name"]
    
    # This is the exact code from run_workflow()
    folder_abs = os.path.normpath(os.path.abspath(folder))
    log.info(f"=== run_workflow START (SIMULATION) ===")
    log.info(f"folder input: {folder}")
    log.info(f"folder_abs after normpath: {folder_abs}")
    log.info(f"name: {name}")
    
    try:
        # Check parent directory exists BEFORE trying to create anything
        parent_dir = os.path.dirname(folder_abs)
        log.info(f"Parent directory: {parent_dir}")
        log.info(f"Parent exists: {os.path.exists(parent_dir)}")
        
        if not os.path.exists(parent_dir):
            msg = f"Parent directory does not exist: {parent_dir}"
            log.error(msg)
            print(f"\n✗ FAILED: {msg}")
            return False
        
        # === STEP 0: Create the target folder ===
        print(f"\nStep 0: Creating folder: {name}/")
        log.info(f"Step 0: About to create folder at {folder_abs}")
        log.info(f"  Folder exists before: {os.path.exists(folder_abs)}")
        
        # Ensure the folder doesn't already exist to avoid conflicts
        if os.path.exists(folder_abs) and not os.path.isdir(folder_abs):
            msg = f"Path exists but is not a folder: {folder_abs}"
            log.error(msg)
            print(f"\n✗ FAILED: {msg}")
            return False
        
        # Create folder - try multiple approaches
        if not os.path.exists(folder_abs):
            log.info(f"Folder doesn't exist, creating it...")
            try:
                # Approach 1: Direct makedirs
                log.info(f"Attempt 1: os.makedirs('{folder_abs}')")
                os.makedirs(folder_abs, exist_ok=True)
                log.info(f"  Return from makedirs")
                
                # Verify immediately
                exists_check1 = os.path.exists(folder_abs)
                isdir_check1 = os.path.isdir(folder_abs)
                log.info(f"  After makedirs - exists: {exists_check1}, isdir: {isdir_check1}")
                
                if not exists_check1:
                    log.warning(f"  os.path.exists() says False immediately after makedirs!")
                    # Try alternative check
                    import pathlib
                    pathlib_exists = pathlib.Path(folder_abs).exists()
                    log.info(f"  pathlib.Path.exists(): {pathlib_exists}")
                    
                    if pathlib_exists:
                        log.info(f"  pathlib says it exists, issue with os.path.exists()?")
                    else:
                        log.error(f"  pathlib also says it doesn't exist!")
                
                if not isdir_check1:
                    msg = f"Failed to create directory (isdir=False): {folder_abs}"
                    log.error(msg)
                    print(f"\n✗ FAILED: {msg}")
                    return False
                
                log.info(f"Step 0: Folder created successfully")
                print(f"\n✓ SUCCESS: Folder created at {folder_abs}")
                return True
                
            except PermissionError as e:
                msg = f"Permission denied creating folder: {folder_abs}\nError: {e}"
                log.error(msg)
                print(f"\n✗ FAILED (Permission): {msg}")
                return False
            except FileExistsError as e:
                msg = f"File exists error: {folder_abs}\nError: {e}"
                log.error(msg)
                print(f"\n✗ FAILED (File Exists): {msg}")
                return False
            except OSError as e:
                msg = f"OS Error creating folder: {e}"
                log.error(msg)
                print(f"\n✗ FAILED (OS Error): {msg}")
                return False
            except Exception as e:
                msg = f"Unexpected error creating folder: {type(e).__name__}: {e}"
                log.error(msg)
                print(f"\n✗ FAILED (Unexpected): {msg}")
                return False
        else:
            log.info(f"Folder already exists, using it")
            if not os.path.isdir(folder_abs):
                msg = f"Path exists but is not a folder: {folder_abs}"
                log.error(msg)
                print(f"\n✗ FAILED: {msg}")
                return False
            print(f"\n✓ SUCCESS: Using existing folder at {folder_abs}")
            return True
            
    except Exception as e:
        msg = f"Unexpected error in folder creation: {type(e).__name__}: {e}"
        log.error(msg)
        print(f"\n✗ FAILED (Top-level): {msg}")
        return False

if __name__ == "__main__":
    result = simulate_wizard_folder_creation()
    print("\n" + "=" * 70)
    print(f"SIMULATION {'PASSED' if result else 'FAILED'}")
    print("=" * 70)
    
    # Show what was created
    if result:
        import pathlib
        parent = r"C:\Users\Ryank\Desktop\Sandbox"
        print(f"\nContents of {parent}:")
        for item in pathlib.Path(parent).iterdir():
            print(f"  - {item.name}")
