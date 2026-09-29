#!/bin/bash
set -e

REALM="${REALM:-LAB.LOCAL}"
DOMAIN="${DOMAIN:-lab.local}"
NETBIOS="${NETBIOS:-LAB}"
ADMIN_PASS="${ADMIN_PASS:-AdminP@ss123!}"
ALICE_PASS="${ALICE_PASS:-AliceP@ss123!}"
BOB_PASS="${BOB_PASS:-BobP@ss123!}"
SERVICE_PASS="${SERVICE_PASS:-SvcApiP@ss123!}"

mkdir -p /shared

if [ ! -f /var/lib/samba/private/sam.ldb ]; then
    echo "[*] Provisioning Samba AD Domain Controller..."
    rm -f /etc/samba/smb.conf
    rm -rf /var/lib/samba/private/* /var/lib/samba/db/*

    samba-tool domain provision \
        --server-role=dc \
        --use-rfc2307 \
        --dns-backend=SAMBA_INTERNAL \
        --realm="${REALM}" \
        --domain="${NETBIOS}" \
        --adminpass="${ADMIN_PASS}"

    echo "[*] Installing Kerberos configuration..."
    cp -f /var/lib/samba/private/krb5.conf /etc/krb5.conf

    echo "[*] Starting temporary Samba daemon for initial provisioning..."
    samba -s /etc/samba/smb.conf
    sleep 3

    echo "[*] Creating demo users..."
    samba-tool user create alice "${ALICE_PASS}" --mail-address="alice@lab.local" --description="Alice - Accounting User" || true
    samba-tool user create bob "${BOB_PASS}" --mail-address="bob@lab.local" --description="Bob - Staff User" || true
    samba-tool user create service_api "${SERVICE_PASS}" --description="Service Account for API Server" || true

    echo "[*] Setting password policies..."
    samba-tool domain passwordsettings set --complexity=off --history-length=0 --min-pwd-age=0 --max-pwd-age=0

    echo "[*] Registering Service Principal Name (SPN) for API..."
    samba-tool spn add HTTP/api.lab.local service_api || true

    echo "[*] Adding DNS A records for lab containers..."
    samba-tool dns add 127.0.0.1 "${DOMAIN}" api A 172.30.0.20 -U administrator%"${ADMIN_PASS}" || true
    samba-tool dns add 127.0.0.1 "${DOMAIN}" client A 172.30.0.30 -U administrator%"${ADMIN_PASS}" || true
    samba-tool dns add 127.0.0.1 "${DOMAIN}" attacker A 172.30.0.50 -U administrator%"${ADMIN_PASS}" || true

    echo "[*] Exporting Service Keytab for API Server..."
    rm -f /shared/api.keytab
    samba-tool domain exportkeytab /shared/api.keytab --principal=HTTP/api.lab.local
    chmod 644 /shared/api.keytab

    echo "[*] Exporting krbtgt Keytab for Lab Educational Demonstration..."
    rm -f /shared/krbtgt.keytab
    samba-tool domain exportkeytab /shared/krbtgt.keytab --principal=krbtgt
    chmod 644 /shared/krbtgt.keytab

    echo "[*] Extracting Domain SID and Cryptographic Keys..."
    python3 /scripts/export_domain_info.py

    echo "[*] Stopping temporary Samba daemon..."
    killall samba || true
    sleep 2
else
    echo "[+] Samba AD already provisioned."
fi

# Ensure krb5.conf is in place
if [ -f /var/lib/samba/private/krb5.conf ]; then
    cp -f /var/lib/samba/private/krb5.conf /etc/krb5.conf
fi
