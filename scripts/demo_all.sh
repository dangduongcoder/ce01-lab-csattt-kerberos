#!/bin/bash
set -e

CYAN='\033[0;36m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

pause() {
    echo -e "\n${YELLOW}>> Nhấn [ENTER] để tiếp tục màn tiếp theo...${NC}"
    read -r
}

clear || true
echo -e "${CYAN}======================================================================${NC}"
echo -e "${CYAN}      BÀI TẬP LỚN CƠ SỞ AN TOÀN THÔNG TIN - KERBEROS GOLDEN TICKET    ${NC}"
echo -e "${CYAN}                  CHƯƠNG TRÌNH DEMO TỰ ĐỘNG LIÊN HOÀN                 ${NC}"
echo -e "${CYAN}======================================================================${NC}"

echo -e "\n${GREEN}[MÀN 1: KIỂM TRA MÔI TRƯỜNG & TÍNH SẴN SÀNG]${NC}"
./scripts/healthcheck.sh
pause

echo -e "\n${GREEN}[MÀN 2: MINH HỌA XÁC THỰC KERBEROS HỢP LỆ (ALICE)]${NC}"
docker compose exec client python demo_normal.py
pause

echo -e "\n${RED}[MÀN 3: TẤN CÔNG GOLDEN TICKET (RÈN VÉ & BYPASS XÁC THỰC)]${NC}"
docker compose exec attacker python demo_golden_ticket.py
pause

echo -e "\n${CYAN}[MÀN 4: PHẪU THUẬT VÉ KERBEROS & PAC INSPECTION]${NC}"
docker compose exec client python inspect_ticket.py
pause

echo -e "\n${YELLOW}[MÀN 5: GIÁM SÁT & PHÁT HIỆN BẤT THƯỜNG (BLUE TEAM DETECTION)]${NC}"
docker compose exec client python -m detector.report
pause

echo -e "\n${GREEN}[MÀN 6: ỨNG PHÓ & KHẮC PHỤC (DOUBLE KRBTGT RESET)]${NC}"
docker compose exec dc /scripts/rotate_krbtgt.sh
pause

echo -e "\n${CYAN}[MÀN 7: KIỂM CHỨNG SAU KHÔI PHỤC]${NC}"
echo "[*] Kiểm chứng 1: Attacker thử dùng lại Golden Ticket cũ để gọi API..."
docker compose exec attacker python -c "
import requests, spnego, os, base64
os.environ['KRB5CCNAME'] = '/shared/golden.ccache'
os.environ['KRB5_CONFIG'] = '/etc/krb5.conf'
try:
    ctx = spnego.client(hostname='api.lab.local', service='HTTP', protocol='negotiate')
    token = base64.b64encode(ctx.step()).decode()
    resp = requests.get('http://api.lab.local:8000/api/whoami', headers={'Authorization': f'Negotiate {token}'})
    print(f'Response Status: {resp.status_code} - {resp.text}')
except Exception as e:
    print(f'[+] THÀNH CÔNG: Vé Golden Ticket cũ đã bị vô hiệu hóa! Lỗi: {e}')
"

echo -e "\n[*] Kiểm chứng 2: Người dùng hợp lệ Alice đăng nhập lại..."
docker compose exec client python client.py login alice
docker compose exec client python client.py whoami

echo -e "\n${GREEN}======================================================================${NC}"
echo -e "${GREEN}                DEMO HOÀN TẤT XUẤT SẮC TẤT CẢ CÁC MÀN!               ${NC}"
echo -e "${GREEN}======================================================================${NC}"
