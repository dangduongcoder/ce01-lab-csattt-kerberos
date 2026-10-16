#!/usr/bin/env python3
"""
Normal Kerberos Authentication Demonstration Script
CSATTT Lab - Kerberos / Active Directory
Optimized for clean classroom presentation and terminal display.
"""
import sys
from rich.console import Console
from rich.panel import Panel
from client import kinit_login, call_endpoint

console = Console()

def wait_user(step_desc: str):
    console.print(f"\n[bold yellow][>>] NHẤN [ENTER] ĐỂ BẮT ĐẦU:[/] [bold cyan]{step_desc}[/]")
    try:
        input()
    except (EOFError, KeyboardInterrupt):
        pass

def run_demo():
    console.print(Panel.fit(
        "[bold cyan]======================================================================\n"
        "   KỊCH BẢN 1: QUY TRÌNH XÁC THỰC KERBEROS HỢP LỆ (ALICE)\n"
        "   Môn học: Cơ sở An toàn Thông tin | Chuẩn giao thức: RFC 4120\n"
        "======================================================================[/]\n\n"
        "Mô tả: Alice (Nhân viên kế toán) thực hiện đăng nhập hợp lệ vào Active Directory,\n"
        "nhận TGT từ KDC và truy cập API dịch vụ qua chuẩn Kerberos GSSAPI/SPNEGO.",
        style="bold blue"
    ))

    # GIAI ĐOẠN 1
    wait_user("GIAI ĐOẠN 1: Gửi AS-REQ đến KDC (Port 88) để xác thực mật khẩu & xin TGT")

    console.print("\n[bold yellow][PHASE 1: AS EXCHANGE - XÁC THỰC VÀ CẤP PHÁT TGT][/]")
    console.print("  [1] [bold green]AS-REQ:[/] Client gửi yêu cầu kèm Pre-Authentication (Timestamp mã hóa bằng khóa K_alice).")
    console.print("  [2] [bold green]AS-REP:[/] KDC xác minh mật khẩu, tạo Session Key và cấp TGT (mã hóa bằng khóa K_krbtgt).")
    
    success = kinit_login("alice", "AliceP@ss123!")
    if not success:
        console.print("[bold red][-] Đăng nhập thất bại. Vui lòng kiểm tra trạng thái Samba AD DC.[/]")
        return

    # GIAI ĐOẠN 2
    wait_user("GIAI ĐOẠN 2: Dùng TGT xin Service Ticket qua TGS-REQ và gọi /api/whoami")

    console.print("\n[bold yellow][PHASE 2: TGS & AP EXCHANGE - TRUY CẬP DỊCH VỤ ỨNG DỤNG][/]")
    console.print("  [3] [bold green]TGS-REQ:[/] Client gửi TGT + Authenticator lên KDC xin vé truy cập [cyan]HTTP/api.lab.local[/].")
    console.print("  [4] [bold green]TGS-REP:[/] KDC giải mã TGT bằng khóa K_krbtgt, kiểm tra PAC và cấp vé Service Ticket (mã hóa bằng K_api).")
    console.print("  [5] [bold green]AP-REQ:[/] Client gửi Service Ticket qua HTTP Header [yellow]Authorization: Negotiate <Ticket>[/].")
    console.print("  [6] [bold green]AP-REP:[/] API Server giải mã vé cục bộ bằng file keytab và xác thực Alice thành công!")

    resp = call_endpoint("/api/whoami")

    # GIAI ĐOẠN 3
    wait_user("GIAI ĐOẠN 3: Kiểm tra phân quyền RBAC (Alice thử truy cập /api/admin/flag)")

    console.print("\n[bold yellow][PHASE 3: KIỂM SOÁT PHÂN QUYỀN TRUY CẬP (RBAC / PAC VALIDATION)][/]")
    console.print("[*] Alice thử truy cập tài nguyên quản trị nhạy cảm: [bold red]/api/admin/flag[/]...")
    admin_resp = call_endpoint("/api/admin/flag")

    if admin_resp and admin_resp.status_code == 403:
        console.print(Panel(
            "[bold green][+] CƠ CHẾ PHÂN QUYỀN BẢO VỆ CHUẨN XÁC:[/]\n"
            "  • Người dùng: [cyan]alice@LAB.LOCAL[/] | Nhóm: [cyan]Domain Users[/] (RID 513)\n"
            "  • Kết quả: [bold red]HTTP 403 Forbidden[/] - Từ chối truy cập vì không có quyền [bold red]Domain Admins[/] (RID 512).\n"
            "  [yellow]=> Chứng minh: Kerberos kiểm soát phân quyền chặt chẽ. Kẻ tấn công muốn leo quyền buộc phải rèn Golden Ticket![/]",
            title="[bold green]Kết quả Kịch bản 1[/]",
            style="green"
        ))

    console.print("\n[bold green][+] Kịch bản xác thực thông thường hoàn tất![/]\n")

if __name__ == "__main__":
    run_demo()
