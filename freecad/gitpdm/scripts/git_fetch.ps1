# Git Fetch Script
# Fetches from remote

param(
    [Parameter(Mandatory=$true)]
    [string]$RepoPath,
    
    [Parameter(Mandatory=$true)]
    [string]$RemoteName
)

$ErrorActionPreference = 'Stop'

try {
    Push-Location $RepoPath
    
    git fetch $RemoteName
    if ($LASTEXITCODE -ne 0) {
        throw "git fetch failed"
    }
    
    Pop-Location
    Write-Output "Fetched successfully"
    exit 0
} catch {
    Pop-Location
    Write-Error $_.Exception.Message
    exit 1
}
