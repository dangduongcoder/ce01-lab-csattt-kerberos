#!/usr/bin/env python3
"""
Export Domain SID and krbtgt cryptographic keys from Samba AD DC to /shared/domain_info.json
Used for the educational Golden Ticket demonstration.
"""
import os
import re
import struct
import subprocess
import json

def get_domain_sid():
    # Attempt to extract objectSid of administrator via samba-tool user show
    try:
        res = subprocess.run(
            ["samba-tool", "user", "show", "administrator"],
            capture_output=True,
            text=True,
            check=True
        )
        for line in res.stdout.splitlines():
            if "objectSid:" in line:
                sid_str = line.split(":", 1)[1].strip()
                # SID format: S-1-5-21-X-Y-Z-500 -> Domain SID is S-1-5-21-X-Y-Z
                if sid_str.endswith("-500"):
                    return sid_str[:-4]
                # In case regex needed
                match = re.search(r"(S-1-5-21-\d+-\d+-\d+)", sid_str)
                if match:
                    return match.group(1)
    except Exception as e:
        print(f"[-] Error getting SID via samba-tool user show: {e}")

    # Fallback: ldbsearch on sam.ldb
    sam_path = "/var/lib/samba/private/sam.ldb"
    if os.path.exists(sam_path):
        try:
            res = subprocess.run(
                ["ldbsearch", "-H", sam_path, "(sAMAccountName=administrator)", "objectSid"],
                capture_output=True,
                text=True
            )
            match = re.search(r"objectSid:\s*(S-1-5-21-\d+-\d+-\d+)-500", res.stdout)
            if match:
                return match.group(1)
        except Exception as e:
            print(f"[-] Error querying sam.ldb: {e}")
    return "S-1-5-21-1234567890-1234567890-1234567890"

def parse_keytab(keytab_path):
    """
    Parse a Kerberos v5 keytab file and return dict of {enctype: hex_key}
    Enctype 18 = aes256-cts-hmac-sha1-96
    Enctype 17 = aes128-cts-hmac-sha1-96
    Enctype 23 = rc4-hmac (NTLM hash)
    """
    keys = {}
    if not os.path.exists(keytab_path):
        return keys

    with open(keytab_path, "rb") as f:
        header = f.read(2)
        if header != b"\x05\x02":
            print(f"[-] Invalid keytab header: {header}")
            return keys

        while True:
            size_bytes = f.read(4)
            if len(size_bytes) < 4:
                break
            size = struct.unpack(">i", size_bytes)[0]
            if size <= 0:
                continue

            entry_data = f.read(size)
            if len(entry_data) < size:
                break

            idx = 0
            # num components
            num_components = struct.unpack(">h", entry_data[idx:idx+2])[0]
            idx += 2
            # realm
            realm_len = struct.unpack(">h", entry_data[idx:idx+2])[0]
            idx += 2
            realm = entry_data[idx:idx+realm_len].decode("utf-8", errors="ignore")
            idx += realm_len

            # components
            for _ in range(num_components):
                comp_len = struct.unpack(">h", entry_data[idx:idx+2])[0]
                idx += 2
                comp = entry_data[idx:idx+comp_len].decode("utf-8", errors="ignore")
                idx += comp_len

            # name_type (4 bytes), timestamp (4 bytes), vno8 (1 byte)
            idx += 9
            # enctype (2 bytes), key_len (2 bytes)
            enctype = struct.unpack(">h", entry_data[idx:idx+2])[0]
            idx += 2
            key_len = struct.unpack(">H", entry_data[idx:idx+2])[0]
            idx += 2
            key_bytes = entry_data[idx:idx+key_len]

            keys[enctype] = key_bytes.hex()
    return keys

def main():
    print("[*] Exporting Domain SID and krbtgt keys...")
    sid = get_domain_sid()
    print(f"[+] Found Domain SID: {sid}")

    keytab_path = "/shared/krbtgt.keytab"
    keys = parse_keytab(keytab_path)

    aes256_key = keys.get(18, "")
    rc4_key = keys.get(23, "")

    data = {
        "realm": "LAB.LOCAL",
        "domain": "lab.local",
        "netbios": "LAB",
        "dc_host": "dc.lab.local",
        "dc_ip": "172.30.0.10",
        "domain_sid": sid,
        "krbtgt_keys": {
            "aes256": aes256_key,
            "rc4": rc4_key
        }
    }

    out_file = "/shared/domain_info.json"
    with open(out_file, "w") as f:
        json.dump(data, f, indent=2)
    os.chmod(out_file, 0o644)
    print(f"[+] Exported domain info to {out_file}")
    if aes256_key:
        print(f"[+] krbtgt AES-256 Key: {aes256_key[:8]}...{aes256_key[-8:]}")
    if rc4_key:
        print(f"[+] krbtgt NTLM Hash (RC4): {rc4_key}")

if __name__ == "__main__":
    main()
