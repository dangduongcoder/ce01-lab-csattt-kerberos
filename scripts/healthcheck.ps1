# Windows PowerShell Healthcheck Script for CSATTT Kerberos Lab

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "        KERBEROS LAB HEALTHCHECK & READINESS (WINDOWS)   " -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

function Check-Container($name) {
    $running = docker ps --format '{{.Names}}' | Select-String -Pattern "^$name$"
    if ($running) {
        Write-Host "[OK] Container $name is RUNNING." -ForegroundColor Green
        return $true
    } else {
        Write-Host "[FAIL] Container $name is NOT running!" -ForegroundColor Red
        return $false
    }
}

Write-Host "`n[*] Step 1: Checking Docker Containers..." -ForegroundColor Yellow
Check-Container "kerberos-dc"
Check-Container "kerberos-api"
Check-Container "kerberos-client"
Check-Container "kerberos-attacker"

Write-Host "`n[*] Step 2: Checking Samba AD DC & Kerberos KDC..." -ForegroundColor Yellow
$dcInfo = docker exec kerberos-dc samba-tool domain info 127.0.0.1 2>$null
if ($LASTEXITCODE -eq 0) {
    Write-Host "[OK] Samba AD DC is initialized and operational." -ForegroundColor Green
} else {
    Write-Host "[WAIT] Samba AD DC is still initializing... please wait." -ForegroundColor Yellow
}

Write-Host "`n[*] Step 3: Checking DNS Resolution..." -ForegroundColor Yellow
docker exec kerberos-client python -c "import socket; socket.gethostbyname('dc.lab.local')" 2>$null
if ($LASTEXITCODE -eq 0) {
    Write-Host "[OK] Host resolution successfully resolves dc.lab.local." -ForegroundColor Green
} else {
    Write-Host "[FAIL] Host resolution failed!" -ForegroundColor Red
}

Write-Host "`n[*] Step 4: Checking Service Keytab Distribution..." -ForegroundColor Yellow
docker exec kerberos-api test -f /shared/api.keytab 2>$null
if ($LASTEXITCODE -eq 0) {
    Write-Host "[OK] Shared volume has /shared/api.keytab." -ForegroundColor Green
} else {
    Write-Host "[WAIT] Keytab not yet present in /shared." -ForegroundColor Yellow
}

Write-Host "`n[*] Step 5: Checking API Server Health Endpoint..." -ForegroundColor Yellow
try {
    $resp = Invoke-RestMethod -Uri "http://localhost:8080/api/health" -Method Get -TimeoutSec 3 -ErrorAction SilentlyContinue
    if ($resp.status -eq "healthy") {
        Write-Host "[OK] FastAPI Service is healthy (status: $($resp.status)) at http://localhost:8080" -ForegroundColor Green
    } else {
        Write-Host "[WAIT] API health status: $($resp.status)" -ForegroundColor Yellow
    }
} catch {
    # Fallback to curl inside container if host port 8080 is blocked or still warming up
    $httpCode = docker exec kerberos-client curl -s -o /dev/null -w "%{http_code}" http://api.lab.local:8000/api/health
    if ($httpCode -eq "200") {
        Write-Host "[OK] FastAPI Service is healthy (HTTP 200) inside Docker network." -ForegroundColor Green
    } else {
        Write-Host "[WAIT] API healthcheck returned HTTP $httpCode" -ForegroundColor Yellow
    }
}

Write-Host "`n==========================================================" -ForegroundColor Cyan
Write-Host "Healthcheck complete." -ForegroundColor Cyan
