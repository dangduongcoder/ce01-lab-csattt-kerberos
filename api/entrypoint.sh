#!/bin/bash
set -e

echo "[*] Starting Kerberos API Service..."
echo "[*] Waiting for Domain Controller to export /shared/api.keytab..."

TIMEOUT=60
COUNTER=0

while [ ! -f /shared/api.keytab ]; do
    sleep 2
    COUNTER=$((COUNTER + 2))
    if [ $COUNTER -ge $TIMEOUT ]; then
        echo "[-] Timeout waiting for /shared/api.keytab! Starting anyway for debugging..."
        break
    fi
    echo "    ... waiting for keytab ($COUNTER/$TIMEOUT s)"
done

if [ -f /shared/api.keytab ]; then
    echo "[+] Found /shared/api.keytab! Setting permissions..."
    chmod 644 /shared/api.keytab
fi

echo "[*] Starting Uvicorn FastAPI Server on port 8000..."
exec uvicorn api.app.main:app --host 0.0.0.0 --port 8000
