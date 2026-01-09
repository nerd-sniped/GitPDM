# Git Pull Script
# Pulls from remote (fetch + fast-forward merge)

param(
    [Parameter(Mandatory=$true)]
    [string]$RepoPath,
    
    [Parameter(Mandatory=$true)]
    [string]$RemoteName,
    
    [Parameter(Mandatory=$false)]
    [string]$Branch = ""
)

$ErrorActionPreference = 'Stop'

try {
    Push-Location $RepoPath
    
    if ($Branch) {
        git pull --ff-only $RemoteName $Branch
    } else {
        git pull --ff-only $RemoteName
    }
    
    if ($LASTEXITCODE -ne 0) {
        throw "git pull failed"
    }
    
    Pop-Location
    Write-Output "Pulled successfully"
    exit 0
} catch {
    Pop-Location
    Write-Error $_.Exception.Message
    exit 1
}
