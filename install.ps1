# GitPDM Installation Helper for FreeCAD 1.2+
# Run this after closing FreeCAD to install/update the addon

Write-Output "==============================================================="
Write-Output "        GitPDM Installation Helper for FreeCAD 1.2+           "
Write-Output "==============================================================="
Write-Output ""

$sourcePath = $PSScriptRoot
$targetPath = "$env:APPDATA\FreeCAD\v1-2\Mod\GitPDM"

# Check if FreeCAD is running
$freecadRunning = Get-Process -Name "FreeCAD" -ErrorAction SilentlyContinue
if ($freecadRunning) {
    Write-Output "WARNING: FreeCAD is currently running!"
    Write-Output "Please close FreeCAD before installing."
    Write-Output ""
    $continue = Read-Host "Continue anyway? (y/N)"
    if ($continue -ne "y") {
        Write-Output "Installation cancelled."
        exit 1
    }
}

Write-Output "Source: $sourcePath"
Write-Output "Target: $targetPath"
Write-Output ""

# Create target directory if it doesn't exist
if (!(Test-Path $targetPath)) {
    Write-Output "Creating FreeCAD Mod directory..."
    New-Item -ItemType Directory -Path $targetPath -Force | Out-Null
    Write-Output "[OK] Directory created"
} else {
    Write-Output "[OK] FreeCAD Mod directory exists"
}

Write-Output ""
Write-Output "Installing GitPDM addon..."

# Copy the entire freecad directory
Write-Output "  Copying freecad/ directory..."
if (Test-Path "$sourcePath\freecad") {
    Copy-Item "$sourcePath\freecad" "$targetPath\freecad" -Recurse -Force
    Write-Output "  [OK] freecad/ copied"
} else {
    Write-Output "  [ERROR] freecad/ directory not found!"
    exit 1
}

# Copy compatibility shim files
Write-Output "  Copying compatibility shims..."
Copy-Item "$sourcePath\__init__.py" "$targetPath\__init__.py" -Force -ErrorAction Stop
Copy-Item "$sourcePath\InitGui.py" "$targetPath\InitGui.py" -Force -ErrorAction Stop
Write-Output "  [OK] __init__.py copied"
Write-Output "  [OK] InitGui.py copied"

# Copy metadata
Write-Output "  Copying metadata files..."
if (Test-Path "$sourcePath\package.xml") {
    Copy-Item "$sourcePath\package.xml" "$targetPath\package.xml" -Force
    Write-Output "  [OK] package.xml copied"
}

Write-Output ""
Write-Output "==============================================================="
Write-Output "             Installation Complete!                           "
Write-Output "==============================================================="
Write-Output ""
Write-Output "Next steps:"
Write-Output "   1. Start FreeCAD 1.2+"
Write-Output "   2. Look for 'Git PDM' in the workbench dropdown"
Write-Output "   3. Switch to Git PDM workbench"
Write-Output "   4. The GitPDM panel should auto-open"
Write-Output ""
Write-Output "Troubleshooting:"
Write-Output "   - If workbench doesn't appear, check FreeCAD console for errors"
Write-Output "   - Verify FreeCAD version is 1.2.0 or newer"
Write-Output "   - Check that Python 3.10+ is being used"
Write-Output ""
Write-Output "Documentation: https://github.com/nerd-sniped/GitPDM"
Write-Output ""
