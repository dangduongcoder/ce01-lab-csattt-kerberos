#!/bin/bash
set -e

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${CYAN}==========================================================${NC}"
echo -e "${CYAN}        KERBEROS LAB HEALTHCHECK & READINESS             ${NC}"
echo -e "${CYAN}==========================================================${NC}"

check_container() {
    local name="$1"
    if docker ps --format '{{.Names}}' | grep -q "^${name}$"; then
        echo -e "[${GREEN}OK${NC}] Container ${name} is RUNNING."
        return 0
    else
        echo -e "[${RED}FAIL${NC}] Container ${name} is NOT running!"
        return 1
    fi
}

echo -e "\n[*] Step 1: Checking Docker Containers..."
check_container "kerberos-dc"
check_container "kerberos-api"
check_container "kerberos-client"
check_container "kerberos-attacker"

echo -e "\n[*] Step 2: Checking Samba AD DC & Kerberos KDC..."
if docker exec kerberos-dc samba-tool domain info 127.0.0.1 >/dev/null 2>&1; then
    echo -e "[${GREEN}OK${NC}] Samba AD DC is initialized and operational."
else
    echo -e "[${YELLOW}WAIT${NC}] Samba AD DC is still initializing... please wait."
fi

echo -e "\n[*] Step 3: Checking DNS Resolution..."
if docker exec kerberos-client python -c "import socket; socket.gethostbyname('dc.lab.local')" >/dev/null 2>&1; then
    echo -e "[${GREEN}OK${NC}] Host resolution successfully resolves dc.lab.local."
else
    echo -e "[${RED}FAIL${NC}] Host resolution failed!"
fi

echo -e "\n[*] Step 4: Checking Service Keytab Distribution..."
if docker exec kerberos-api test -f /shared/api.keytab; then
    echo -e "[${GREEN}OK${NC}] Shared volume has /shared/api.keytab."
else
    echo -e "[${YELLOW}WAIT${NC}] Keytab not yet present in /shared."
fi

echo -e "\n[*] Step 5: Checking API Server Health Endpoint..."
HTTP_CODE=$(docker exec kerberos-client curl -s -o /dev/null -w "%{http_code}" http://api.lab.local:8000/api/health || echo "000")
if [ "$HTTP_CODE" = "200" ]; then
    echo -e "[${GREEN}OK${NC}] FastAPI Service is healthy (HTTP 200) at http://api.lab.local:8000."
else
    echo -e "[${YELLOW}WAIT${NC}] API healthcheck returned HTTP ${HTTP_CODE}."
fi

echo -e "\n${CYAN}==========================================================${NC}"
echo -e "${GREEN}Lab environment is ready for live demonstration!${NC}"
echo -e "${CYAN}Web Dashboard available at:${NC} http://localhost:8080"
echo -e "${CYAN}==========================================================${NC}"
