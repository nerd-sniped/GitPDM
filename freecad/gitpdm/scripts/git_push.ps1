# Git Push Script
# Pushes commits to remote

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
        git push $RemoteName $Branch
    } else {
        # Push current branch
        git push $RemoteName HEAD
    }
    
    if ($LASTEXITCODE -ne 0) {
        throw "git push failed"
    }
    
    Pop-Location
    Write-Output "Pushed successfully"
    exit 0
} catch {
    Pop-Location
    Write-Error $_.Exception.Message
    exit 1
}
