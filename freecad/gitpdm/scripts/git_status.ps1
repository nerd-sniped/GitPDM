# Git Status Script
# Returns status in porcelain format

param(
    [Parameter(Mandatory=$true)]
    [string]$RepoPath
)

$ErrorActionPreference = 'Stop'

try {
    Push-Location $RepoPath
    git status --porcelain
    Pop-Location
    exit 0
} catch {
    Write-Error $_.Exception.Message
    exit 1
}
