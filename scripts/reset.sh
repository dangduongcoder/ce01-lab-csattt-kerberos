#!/bin/bash
set -e

CYAN='\033[0;36m'
GREEN='\033[0;32m'
NC='\033[0m'

echo -e "${CYAN}==========================================================${NC}"
echo -e "${CYAN}           RESETTING KERBEROS LAB TO CLEAN STATE         ${NC}"
echo -e "${CYAN}==========================================================${NC}"

echo "[*] Stopping and removing all lab containers and volumes..."
docker compose down -v --remove-orphans

echo "[*] Cleaning up any local caches..."
rm -f *.ccache

echo -e "\n${GREEN}[✓] Lab has been completely reset to pristine state.${NC}"
echo -e "You can re-launch anytime with: ${CYAN}make up${NC} or ${CYAN}docker compose up -d --build${NC}"
