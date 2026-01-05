# Setup Git Credentials for GitPDM User
# This script configures git to use the correct GitHub token

param(
    [Parameter(Mandatory=$true)]
    [string]$Username,
    
    [Parameter(Mandatory=$true)]
    [string]$Token
)

Write-Host "Configuring git credentials for user: $Username" -ForegroundColor Cyan

# Use git credential approve to store credentials
$credentialInput = @"
protocol=https
host=github.com
username=$Username
password=$Token

"@

try {
    $credentialInput | git credential approve
    Write-Host "✓ Git credentials configured successfully" -ForegroundColor Green
    Write-Host ""
    Write-Host "Git LFS will now authenticate as: $Username" -ForegroundColor Cyan
} catch {
    Write-Host "✗ Failed to configure git credentials: $_" -ForegroundColor Red
}

Write-Host ""
Write-Host "To test, run:" -ForegroundColor Yellow
Write-Host "  git lfs locks" -ForegroundColor White
