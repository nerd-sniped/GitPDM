# Git Current Branch Script
# Returns the current branch name

param(
    [Parameter(Mandatory=$true)]
    [string]$RepoPath
)

$ErrorActionPreference = 'Stop'

try {
    Push-Location $RepoPath
    
    $branch = git rev-parse --abbrev-ref HEAD 2>$null
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to get current branch"
    }
    
    Pop-Location
    Write-Output $branch
    exit 0
} catch {
    Pop-Location
    Write-Error $_.Exception.Message
    exit 1
}
