# Windows PowerShell Reset Script for CSATTT Kerberos Lab

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "           RESETTING KERBEROS LAB TO CLEAN STATE         " -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

Write-Host "[*] Stopping and removing all lab containers and volumes..." -ForegroundColor Yellow
docker compose down -v --remove-orphans

Write-Host "[*] Cleaning up any local caches..." -ForegroundColor Yellow
if (Test-Path "*.ccache") {
    Remove-Item -Path "*.ccache" -Force
}

Write-Host "`n[+] Lab has been completely reset to pristine state." -ForegroundColor Green
Write-Host "You can re-launch anytime with: docker compose up -d --build" -ForegroundColor Cyan
