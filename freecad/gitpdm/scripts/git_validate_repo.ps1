# Git Validate Repository Script
# Returns the repository root if valid, empty if not

param(
    [Parameter(Mandatory=$true)]
    [string]$Path
)

$ErrorActionPreference = 'SilentlyContinue'

# Check if path exists
if (-not (Test-Path $Path)) {
    exit 1
}

# Get repository root
Push-Location $Path
$repoRoot = git rev-parse --show-toplevel 2>$null
Pop-Location

if ($repoRoot) {
    # Convert to Windows path
    $repoRoot = $repoRoot -replace '/', '\'
    Write-Output $repoRoot
    exit 0
} else {
    exit 1
}
