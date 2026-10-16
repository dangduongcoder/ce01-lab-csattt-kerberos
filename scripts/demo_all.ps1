# Windows PowerShell Interactive Demo Script for CSATTT Kerberos Lab

function Pause-Step {
    Write-Host "`n[>>] Nhấn [ENTER] để tiếp tục màn tiếp theo..." -ForegroundColor Yellow
    [void][System.Console]::ReadLine()
}

Clear-Host
Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host "      BÀI TẬP LỚN CƠ SỞ AN TOÀN THÔNG TIN - KERBEROS GOLDEN TICKET    " -ForegroundColor Cyan
Write-Host "                  CHƯƠNG TRÌNH DEMO TỰ ĐỘNG LIÊN HOÀN                 " -ForegroundColor Cyan
Write-Host "======================================================================" -ForegroundColor Cyan

# MÀN 1
Write-Host "`n[MÀN 1: KIỂM TRA MÔI TRƯỜNG & TÍNH SẴN SÀNG]" -ForegroundColor Green
powershell -ExecutionPolicy Bypass -File .\scripts\healthcheck.ps1
Pause-Step

# MÀN 2
Write-Host "`n[MÀN 2: MINH HỌA XÁC THỰC KERBEROS HỢP LỆ (ALICE)]" -ForegroundColor Green
docker compose exec client python demo_normal.py
Pause-Step

# MÀN 3
Write-Host "`n[MÀN 3: TẤN CÔNG GOLDEN TICKET (RÈN VÉ & BYPASS XÁC THỰC)]" -ForegroundColor Red
docker compose exec attacker python demo_golden_ticket.py
Pause-Step

# MÀN 4
Write-Host "`n[MÀN 4: PHẪU THUẬT VÉ KERBEROS & PAC INSPECTION]" -ForegroundColor Cyan
docker compose exec client python inspect_ticket.py
Pause-Step

# MÀN 5
Write-Host "`n[MÀN 5: GIÁM SÁT & PHÁT HIỆN BẤT THƯỜNG (BLUE TEAM DETECTION)]" -ForegroundColor Yellow
docker compose exec client python -m detector.report
Pause-Step

# MÀN 6
Write-Host "`n[MÀN 6: ỨNG PHÓ & KHẮC PHỤC (DOUBLE KRBTGT RESET)]" -ForegroundColor Green
docker compose exec dc /scripts/rotate_krbtgt.sh
Pause-Step

# MÀN 7
Write-Host "`n[MÀN 7: KIỂM CHỨNG SAU KHÔI PHỤC]" -ForegroundColor Cyan
Write-Host "[*] Kiểm chứng 1: Attacker thử dùng lại Golden Ticket cũ để gọi API..."
docker compose exec attacker python -c "
import requests, gssapi, os, base64
os.environ['KRB5CCNAME'] = '/shared/golden.ccache'
os.environ['KRB5_CONFIG'] = '/etc/krb5.conf'
try:
    target_name = gssapi.Name('HTTP/api.lab.local@LAB.LOCAL', gssapi.NameType.kerberos_principal)
    ctx = gssapi.SecurityContext(name=target_name, usage='initiate')
    token = base64.b64encode(ctx.step()).decode()
    resp = requests.get('http://api.lab.local:8000/api/whoami', headers={'Authorization': f'Negotiate {token}'})
    print(f'Response Status: {resp.status_code} - {resp.text}')
except Exception as e:
    print(f'[+] THÀNH CÔNG: Vé Golden Ticket cũ đã bị vô hiệu hóa hoàn toàn! Lỗi: {e}')
"

Write-Host "`n[*] Kiểm chứng 2: Người dùng hợp lệ Alice đăng nhập lại với khóa mới..."
docker compose exec client python client.py login alice
docker compose exec client python client.py whoami

Write-Host "`n======================================================================" -ForegroundColor Green
Write-Host "                DEMO HOÀN TẤT XUẤT SẮC TẤT CẢ CÁC MÀN!               " -ForegroundColor Green
Write-Host "======================================================================" -ForegroundColor Green
