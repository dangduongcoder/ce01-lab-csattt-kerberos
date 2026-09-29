#!/bin/bash
set -e

echo "=========================================================="
echo "    [RECOVERY] Active Directory krbtgt Double Reset       "
echo "=========================================================="
echo "[!] Incident Response: krbtgt cryptographic material suspected compromised."
echo "[!] Theoretical Context:"
echo "    Active Directory maintains two keys for krbtgt: Current and Previous."
echo "    A single reset leaves the old key in history, allowing existing tickets to work."
echo "    A SECOND reset is MANDATORY to completely evict the old key from history."
echo "----------------------------------------------------------"

NEW_PASS_1="NewKrbTgtP@ssWord_Phase1_$(date +%s)!"
NEW_PASS_2="NewKrbTgtP@ssWord_Phase2_$(date +%s)!"

echo "[*] Step 1: Performing FIRST krbtgt password reset..."
samba-tool user password krbtgt --newpassword="${NEW_PASS_1}"
echo "[+] First reset completed. Current key updated, old key moved to 'Previous'."
sleep 2

echo "[*] Step 2: Performing SECOND krbtgt password reset..."
samba-tool user password krbtgt --newpassword="${NEW_PASS_2}"
echo "[+] Second reset completed. Compromised key is now permanently purged!"

echo "[*] Step 3: Re-exporting fresh krbtgt keytab..."
rm -f /shared/krbtgt.keytab
samba-tool domain exportkeytab /shared/krbtgt.keytab --principal=krbtgt
chmod 644 /shared/krbtgt.keytab

echo "[*] Step 4: Updating domain info with new keys..."
python3 /scripts/export_domain_info.py

echo "----------------------------------------------------------"
echo "[+] RECOVERY COMPLETE:"
echo "    - All previously forged Golden Tickets are now INVALID (decryption will fail)."
echo "    - Legitimate users will obtain fresh, valid TGTs upon re-authentication."
echo "=========================================================="
