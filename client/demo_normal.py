#!/usr/bin/env python3
"""
Normal Kerberos Authentication Demonstration Script
Shows complete legitimate Kerberos flow: AS-REQ/REP -> TGS-REQ/REP -> AP-REQ/REP
"""
import time
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from client import kinit_login, call_endpoint, show_klist

console = Console()

def run_demo():
    console.print(Panel.fit(
        "[bold cyan]===========================================================\n"
        "   SCENARIO 1: LEGITIMATE KERBEROS AUTHENTICATION (ALICE)   \n"
        "===========================================================[/]\n"
        "Mô tả: Alice (Nhân viên kế toán) thực hiện đăng nhập hợp lệ vào Active Directory,\n"
        "nhận TGT từ KDC và truy cập API dịch vụ qua chuẩn Kerberos GSSAPI/SPNEGO.",
        style="bold blue"
    ))

    time.sleep(1)

    console.print("\n[bold yellow][PHASE 1: XÁC THỰC DANH TÍNH VỚI KDC][/]")
    console.print("  [1] [bold green]AS-REQ:[/] Client gửi yêu cầu kèm Pre-Authentication (Timestamp mã hóa bằng mật khẩu của Alice).")
    console.print("  [2] [bold green]AS-REP:[/] KDC xác minh mật khẩu, tạo Session Key và cấp [bold cyan]TGT[/] (mã hóa bằng key của [bold red]krbtgt[/]).")
    
    success = kinit_login("alice", "AliceP@ss123!")
    if not success:
        console.print("[bold red][-] Đăng nhập thất bại. Vui lòng kiểm tra trạng thái Samba AD DC.[/]")
        return

    time.sleep(1)

    console.print("\n[bold yellow][PHASE 2: TRUY CẬP DỊCH VỤ (API SERVER)][/]")
    console.print("  [3] [bold green]TGS-REQ:[/] Client gửi TGT + Authenticator lên KDC xin vé truy cập [cyan]HTTP/api.lab.local[/].")
    console.print("  [4] [bold green]TGS-REP:[/] KDC giải mã TGT bằng key của [red]krbtgt[/], kiểm tra hợp lệ và cấp [bold cyan]Service Ticket[/] (mã hóa bằng key của Service).")
    console.print("  [5] [bold green]AP-REQ:[/] Client gửi Service Ticket qua HTTP Header [yellow]Authorization: Negotiate &lt;Ticket&gt;[/].")
    console.print("  [6] [bold green]AP-REP:[/] API Server giải mã Service Ticket bằng keytab nội bộ, xác thực Alice thành công!")

    resp = call_endpoint("/api/whoami")

    time.sleep(1)

    console.print("\n[bold yellow][PHASE 3: KIỂM SOÁT QUYỀN TRUY CẬP (AUTHORIZATION / RBAC)][/]")
    console.print("[*] Alice thử truy cập tài nguyên quản trị nhạy cảm: [bold red]/api/admin/flag[/]...")
    admin_resp = call_endpoint("/api/admin/flag")

    if admin_resp and admin_resp.status_code == 403:
        console.print(Panel(
            "[bold green][+] PHÂN QUYỀN BẢO VỆ CHUẨN XÁC:[/] Alice chỉ thuộc nhóm [cyan]Domain Users[/] (RID 513).\n"
            "Hệ thống từ chối quyền truy cập quản trị (HTTP 403 Forbidden).\n"
            "[yellow]=> Đây là lý do kẻ tấn công cần rèn Golden Ticket để tự nâng quyền lên 'Domain Admins'![/]",
            title="[bold green]Kết quả kịch bản 1[/]",
            style="green"
        ))

if __name__ == "__main__":
    run_demo()
