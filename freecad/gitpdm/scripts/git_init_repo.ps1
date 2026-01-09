# Git Initialize Repository Script
# Creates a new git repository

param(
    [Parameter(Mandatory=$true)]
    [string]$Path
)

$ErrorActionPreference = 'Stop'

try {
    if (-not (Test-Path $Path)) {
        Write-Error "Path does not exist: $Path"
        exit 1
    }
    
    Push-Location $Path
    git init
    Pop-Location
    
    Write-Output "Repository initialized at $Path"
    exit 0
} catch {
    Write-Error $_.Exception.Message
    exit 1
}
