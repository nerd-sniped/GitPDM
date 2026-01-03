# GitCAD Wrapper Manual Test Script
# This script provides interactive tests you can run to verify the wrapper functionality

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "GitCAD Wrapper Manual Test Guide" -ForegroundColor Cyan
Write-Host "========================================`n" -ForegroundColor Cyan

$repoPath = "C:\Factorem\Nerd-Sniped\GitPDM\GitCAD-main"

Write-Host "Testing repository: $repoPath`n" -ForegroundColor Yellow

# Test 1: Check GitCAD Detection
Write-Host "TEST 1: GitCAD Detection" -ForegroundColor Green
Write-Host "---------------------------------------"
Write-Host "This tests if GitCAD is properly detected in the repository."
Write-Host "`nCommands to run:"
Write-Host "  python -c `"from freecad_gitpdm.gitcad import is_gitcad_initialized; print('GitCAD Initialized:', is_gitcad_initialized('$repoPath'))`"" -ForegroundColor White
Write-Host "`nExpected result: GitCAD Initialized: True"
Write-Host "(GitCAD files are present but not yet initialized/configured)`n"

# Test 2: Check Status
Write-Host "TEST 2: Detailed Status Check" -ForegroundColor Green
Write-Host "---------------------------------------"
Write-Host "This checks what components are present and what's missing."
Write-Host "`nCommand to run:"
@"
python -c "from freecad_gitpdm.gitcad import check_gitcad_status; import json
result = check_gitcad_status('$repoPath')
if result.ok:
    status = result.value
    print('Initialized:', status.is_initialized)
    print('Has Config:', status.has_config)
    print('Has FCStd Tool:', status.has_fcstd_tool)
    print('Has Init Script:', status.has_init_script)
    print('Has Git Hooks:', status.has_git_hooks)
    print('Config Valid:', status.config_valid)
    print('FreeCAD Python Configured:', status.freecad_python_configured)
    if status.missing_components:
        print('Missing:', ', '.join(status.missing_components))
    if status.warnings:
        print('Warnings:')
        for w in status.warnings:
            print('  -', w)
else:
    print('Error:', result.error)"
"@ | Write-Host -ForegroundColor White
Write-Host "`nExpected result: Should show config.json is missing (not initialized yet)`n"

# Test 3: Find .FCStd Files
Write-Host "TEST 3: Find .FCStd Files" -ForegroundColor Green
Write-Host "---------------------------------------"
Write-Host "This finds all .FCStd files in the repository."
Write-Host "`nCommand to run:"
@"
python -c "from freecad_gitpdm.gitcad import find_fcstd_files
files = find_fcstd_files('$repoPath')
print(f'Found {len(files)} .FCStd files:')
for f in files:
    print(f'  - {f}')"
"@ | Write-Host -ForegroundColor White
Write-Host "`nExpected result: Should find AssemblyExample.FCStd and BIMExample.FCStd`n"

# Test 4: Check for Bash
Write-Host "TEST 4: Bash Detection (Windows)" -ForegroundColor Green
Write-Host "---------------------------------------"
Write-Host "This checks if Git Bash is available (required for wrapper)."
Write-Host "`nCommand to run:"
@"
python -c "from freecad_gitpdm.gitcad.wrapper import _find_bash_executable
bash = _find_bash_executable()
if bash:
    print(f'Bash found: {bash}')
else:
    print('ERROR: Bash not found! Git Bash is required.')"
"@ | Write-Host -ForegroundColor White
Write-Host "`nExpected result: Should find Git Bash executable (e.g., C:\Program Files\Git\bin\bash.exe)`n"

# Test 5: Create Default Config
Write-Host "TEST 5: Create Default Configuration" -ForegroundColor Green
Write-Host "---------------------------------------"
Write-Host "This creates a default config.json file."
Write-Host "`nCommand to run:"
@"
python -c "from freecad_gitpdm.gitcad import create_default_config
result = create_default_config('$repoPath', '')
if result.ok:
    print('SUCCESS: Config created')
    config = result.value
    print('  FreeCAD Python:', config.freecad_python_instance_path or '(not set)')
    print('  Require locks:', config.require_lock_to_modify_freecad_files)
    print('  Uncompressed suffix:', config.uncompressed_directory_structure.uncompressed_directory_suffix)
else:
    print('ERROR:', result.error)"
"@ | Write-Host -ForegroundColor White
Write-Host "`nExpected result: Creates FreeCAD_Automation/config.json with defaults"
Write-Host "After running, check: Test-Path `"$repoPath\FreeCAD_Automation\config.json`"`n"

# Test 6: Load Configuration
Write-Host "TEST 6: Load Configuration" -ForegroundColor Green
Write-Host "---------------------------------------"
Write-Host "This loads and displays the configuration (run after Test 5)."
Write-Host "`nCommand to run:"
@"
python -c "from freecad_gitpdm.gitcad import load_gitcad_config
result = load_gitcad_config('$repoPath')
if result.ok:
    config = result.value
    print('FreeCAD Python Path:', config.freecad_python_instance_path or '(empty)')
    print('Require Locks:', config.require_lock_to_modify_freecad_files)
    print('Include Thumbnails:', config.include_thumbnails)
    print('Uncompressed Suffix:', config.uncompressed_directory_structure.uncompressed_directory_suffix)
    print('Uncompressed Prefix:', config.uncompressed_directory_structure.uncompressed_directory_prefix or '(empty)')
    print('Use Subdirectory:', config.uncompressed_directory_structure.put_uncompressed_directory_in_subdirectory)
    print('Compress Binaries:', config.compress_non_human_readable_freecad_files.enabled)
else:
    print('ERROR:', result.error)"
"@ | Write-Host -ForegroundColor White
Write-Host "`nExpected result: Shows all configuration values`n"

# Test 7: Get Locks (will be empty until files are locked)
Write-Host "TEST 7: Get Lock Status" -ForegroundColor Green
Write-Host "---------------------------------------"
Write-Host "This gets the current lock status (requires git LFS)."
Write-Host "`nCommand to run:"
@"
python -c "from freecad_gitpdm.gitcad import get_locks
result = get_locks('$repoPath')
if result.ok:
    locks = result.value
    print(f'Found {len(locks)} locked files:')
    if locks:
        for lock in locks:
            print(f'  - {lock.path} (owner: {lock.owner}, ID: {lock.lock_id})')
    else:
        print('  (No files currently locked)')
else:
    print('ERROR:', result.error)"
"@ | Write-Host -ForegroundColor White
Write-Host "`nExpected result: Should show 0 locked files (or error if not a git repo yet)`n"

# Test 8: Create Wrapper Instance
Write-Host "TEST 8: Create Wrapper Instance" -ForegroundColor Green
Write-Host "---------------------------------------"
Write-Host "This creates a GitCADWrapper instance and verifies paths."
Write-Host "`nCommand to run:"
@"
python -c "from freecad_gitpdm.gitcad import GitCADWrapper
try:
    wrapper = GitCADWrapper('$repoPath')
    print('SUCCESS: Wrapper created')
    print('  Repo root:', wrapper.repo_root)
    print('  Config file:', wrapper.paths.config_file)
    print('  FCStd tool:', wrapper.paths.fcstd_tool)
    print('  Lock script:', wrapper.paths.lock_script)
    print('  Bash exe:', wrapper._bash_exe)
except Exception as e:
    print('ERROR:', e)"
"@ | Write-Host -ForegroundColor White
Write-Host "`nExpected result: Shows all paths to GitCAD components`n"

# Summary
Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "Test Instructions" -ForegroundColor Cyan
Write-Host "========================================`n" -ForegroundColor Cyan
Write-Host "1. Make sure you have Python installed and in PATH" -ForegroundColor Yellow
Write-Host "2. Install FreeCAD if you want to test export/import" -ForegroundColor Yellow
Write-Host "3. Run tests 1-4 first (don't require config)" -ForegroundColor Yellow
Write-Host "4. Run test 5 to create config.json" -ForegroundColor Yellow
Write-Host "5. Optionally edit config.json to add FreeCAD Python path" -ForegroundColor Yellow
Write-Host "6. Run tests 6-8 (require config)" -ForegroundColor Yellow
Write-Host "`nNote: Some tests (lock operations, export/import) require:" -ForegroundColor Yellow
Write-Host "  - Repository to be initialized (run init-repo script)" -ForegroundColor Yellow
Write-Host "  - Git repository with LFS installed" -ForegroundColor Yellow
Write-Host "  - FreeCAD Python path configured" -ForegroundColor Yellow

Write-Host "`n========================================`n" -ForegroundColor Cyan
