# GitPDM GitHub Authentication Cleaner

Write-Host "=====================================" -ForegroundColor Cyan
Write-Host "GitPDM GitHub Authentication Cleaner" -ForegroundColor Cyan
Write-Host "=====================================" -ForegroundColor Cyan
Write-Host ""

# Show current credentials
Write-Host "Current GitHub-related credentials:" -ForegroundColor Yellow
cmdkey /list | Select-String -Pattern "github"
Write-Host ""

# Remove GitPDM OAuth credential
Write-Host "Removing GitPDM OAuth credential..." -ForegroundColor Yellow
cmdkey /delete:"GitPDM:github.com:oauth" 2>&1 | Out-Null
if ($LASTEXITCODE -eq 0) {
    Write-Host " GitPDM OAuth credential removed" -ForegroundColor Green
} else {
    Write-Host " GitPDM OAuth credential not found or already removed" -ForegroundColor Gray
}
Write-Host ""

# Check git config
Write-Host "Current Git user configuration:" -ForegroundColor Yellow
$gitUser = git config user.name
$gitEmail = git config user.email
Write-Host "  user.name: $gitUser" -ForegroundColor Cyan
Write-Host "  user.email: $gitEmail" -ForegroundColor Cyan
Write-Host ""

Write-Host "=====================================" -ForegroundColor Cyan
Write-Host "Next Steps:" -ForegroundColor Cyan
Write-Host "=====================================" -ForegroundColor Cyan
Write-Host "1. Open FreeCAD and GitPDM"
Write-Host "2. Click 'Disconnect GitHub' if connected"
Write-Host "3. Click 'Connect GitHub' and authenticate with YOUR account"
Write-Host "4. The lock ownership should now show your username"
Write-Host ""
