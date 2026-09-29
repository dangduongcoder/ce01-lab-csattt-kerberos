#!/usr/bin/env python3
"""
Blue Team Detection & Incident Analysis Report
Evaluates Kerberos audit logs against detection rules for Golden Ticket attacks.
"""
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from detector.parser import parse_auth_events
from detector.rules import check_missing_as_req, check_abnormal_privilege, check_ticket_lifetime_anomaly

console = Console()

def generate_report():
    console.print(Panel.fit(
        "[bold blue]🛡️ BLUE TEAM DETECTION ENGINE & SECURITY INCIDENT REPORT[/]\n"
        "Hệ thống giám sát và phân tích bất thường xác thực Kerberos Active Directory",
        style="bold cyan"
    ))

    events = parse_auth_events()
    console.print(f"[dim]Đã tải {len(events)} sự kiện xác thực từ /shared/api_auth.log...[/dim]\n")

    alerts = []
    alerts.extend(check_missing_as_req(events))
    alerts.extend(check_abnormal_privilege(events))
    alerts.extend(check_ticket_lifetime_anomaly())

    if not alerts:
        console.print(Panel(
            "[bold green][✓] Không phát hiện hành vi bất thường nào.[/]\n"
            "Tất cả các phiên xác thực đều tuân thủ chính sách bảo mật Kerberos tiêu chuẩn.",
            title="[bold green]Trạng thái an toàn[/]",
            style="green"
        ))
        return

    table = Table(title="Danh sách Cảnh báo Bảo mật (Security Alerts Detected)")
    table.add_column("Mức độ (Severity)", justify="center", no_wrap=True)
    table.add_column("Tên Quy tắc (Rule ID)", style="cyan", no_wrap=True)
    table.add_column("Mô tả Chi tiết (Description)", style="white")

    for al in alerts:
        sev_style = "[bold red on black] CRITICAL [/]" if al.severity == "CRITICAL" else "[bold yellow] WARNING [/]"
        table.add_row(sev_style, al.rule_name, al.message)

    console.print(table)

    console.print("\n[bold red]🚨 KẾT LUẬN ĐIỀU TRA (INCIDENT RESPONSE):[/]")
    console.print("  [!] Hệ thống có dấu hiệu rõ ràng của cuộc tấn công [bold red]Golden Ticket (MITRE ATT&CK T1558.001)[/].")
    console.print("  [!] Kẻ tấn công đã nắm giữ bí mật của tài khoản [bold red]krbtgt[/] và tự rèn vé có hạn 10 năm với quyền Administrator.")
    console.print("  [!] Đề xuất hành động khắc phục ngay lập tức: [bold yellow]Thực hiện Double Reset mật khẩu krbtgt[/] để vô hiệu hóa toàn bộ vé giả mạo!")

if __name__ == "__main__":
    generate_report()
