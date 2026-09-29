#!/bin/bash
set -e

echo "[*] Initializing Samba AD Domain Controller..."
/scripts/provision.sh

echo "[+] Samba AD DC provisioning check complete."
echo "[*] Launching Samba daemon in foreground mode..."
exec samba -i -M single
