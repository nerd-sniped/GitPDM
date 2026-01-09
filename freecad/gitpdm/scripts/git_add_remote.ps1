# Git Add Remote Script
# Adds a remote repository

param(
    [Parameter(Mandatory=$true)]
    [string]$RepoPath,
    
    [Parameter(Mandatory=$true)]
    [string]$RemoteName,
    
    [Parameter(Mandatory=$true)]
    [string]$RemoteUrl
)

$ErrorActionPreference = 'Stop'

try {
    Push-Location $RepoPath
    
    git remote add $RemoteName $RemoteUrl
    if ($LASTEXITCODE -ne 0) {
        throw "git remote add failed"
    }
    
    Pop-Location
    Write-Output "Remote '$RemoteName' added successfully"
    exit 0
} catch {
    Pop-Location
    Write-Error $_.Exception.Message
    exit 1
}
