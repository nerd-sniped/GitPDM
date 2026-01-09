# Git Commit Script
# Stages and commits changes

param(
    [Parameter(Mandatory=$true)]
    [string]$RepoPath,
    
    [Parameter(Mandatory=$true)]
    [string]$Message,
    
    [Parameter(Mandatory=$false)]
    [switch]$StageAll = $false
)

$ErrorActionPreference = 'Stop'

try {
    Push-Location $RepoPath
    
    if ($StageAll) {
        git add -A
        if ($LASTEXITCODE -ne 0) {
            throw "git add failed"
        }
    }
    
    git commit -m $Message
    if ($LASTEXITCODE -ne 0) {
        throw "git commit failed"
    }
    
    Pop-Location
    Write-Output "Committed successfully"
    exit 0
} catch {
    Pop-Location
    Write-Error $_.Exception.Message
    exit 1
}
