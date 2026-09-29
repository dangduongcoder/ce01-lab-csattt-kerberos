#!/usr/bin/env python3
"""
Python Kerberos Client CLI for CSATTT Lab
Demonstrates Kerberos authentication flow and API consumption via SPNEGO.
"""
import os
import sys
import base64
import subprocess
import requests
import spnego
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()

API_URL = os.getenv("API_URL", "http://api.lab.local:8000")
SERVICE_SPN = os.getenv("SERVICE_SPN", "HTTP/api.lab.local")
DEFAULT_REALM = os.getenv("REALM", "LAB.LOCAL")

PASSWORDS = {
    "alice": "AliceP@ss123!",
    "bob": "BobP@ss123!",
    "administrator": "AdminP@ss123!"
}

def kinit_login(username: str, password: str = None) -> bool:
    if "@" not in username:
        principal = f"{username}@{DEFAULT_REALM}"
    else:
        principal = username

    user_base = username.split("@")[0].lower()
    pwd = password or PASSWORDS.get(user_base, "AliceP@ss123!")

    console.print(f"[bold cyan][*] Authenticating with Kerberos KDC for principal:[/] [yellow]{principal}[/]")
    console.print("    [dim]Sending AS-REQ to dc.lab.local (Port 88)...[/dim]")

    try:
        proc = subprocess.Popen(
            ["kinit", principal],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        stdout, stderr = proc.communicate(input=pwd + "\n", timeout=10)

        if proc.returncode != 0:
            console.print(f"[bold red][-] kinit failed (Exit {proc.returncode}):[/] {stderr.strip()}")
            return False

        console.print("[bold green][+] AS-REP received: TGT successfully stored in credential cache![/]")
        show_klist()
        return True
    except Exception as e:
        console.print(f"[bold red][-] Exception during kinit:[/] {e}")
        return False

def show_klist():
    try:
        res = subprocess.run(["klist"], capture_output=True, text=True)
        if res.returncode == 0:
            console.print(Panel(res.stdout.strip(), title="[bold green]Kerberos Credential Cache (klist)[/]", expand=False))
        else:
            console.print(f"[yellow][!] klist returned {res.returncode}: {res.stderr.strip()}[/]")
    except Exception as e:
        console.print(f"[red][-] Error running klist:[/] {e}")

def get_spnego_token(spn: str = SERVICE_SPN) -> str:
    """
    Generate Kerberos AP-REQ token for the given SPN using active credentials in Kerberos ccache.
    """
    import gssapi
    target_spn = spn if "@" in spn else f"{spn}@{DEFAULT_REALM}"
    target = gssapi.Name(target_spn, gssapi.NameType.kerberos_principal)
    ctx = gssapi.SecurityContext(name=target, usage='initiate')
    token_bytes = ctx.step()
    return base64.b64encode(token_bytes).decode("ascii")

def call_endpoint(endpoint: str = "/api/whoami"):
    url = f"{API_URL}{endpoint}"
    console.print(f"[bold cyan][*] Calling Service API:[/] [yellow]{url}[/]")
    console.print(f"    [dim]Target SPN: {SERVICE_SPN}[/dim]")

    try:
        console.print("    [dim]Generating Kerberos SPNEGO AP-REQ token...[/dim]")
        token_b64 = get_spnego_token(SERVICE_SPN)
        headers = {"Authorization": f"Negotiate {token_b64}"}

        console.print(f"    [dim]Sending HTTP GET with Authorization header...[/dim]")
        resp = requests.get(url, headers=headers, timeout=5)

        table = Table(title=f"API Response (HTTP {resp.status_code})")
        table.add_column("Property", style="cyan")
        table.add_column("Value", style="magenta")

        table.add_row("Status Code", str(resp.status_code))
        try:
            data = resp.json()
            for k, v in data.items():
                table.add_row(k, str(v))
        except Exception:
            table.add_row("Body", resp.text)

        console.print(table)
        return resp
    except Exception as e:
        console.print(f"[bold red][-] Failed to call API with Kerberos:[/] {e}")
        return None

def main():
    if len(sys.argv) < 2:
        console.print("[bold yellow]Usage:[/]")
        console.print("  python client.py login <username> [password]")
        console.print("  python client.py whoami")
        console.print("  python client.py admin")
        console.print("  python client.py klist")
        sys.exit(1)

    cmd = sys.argv[1].lower()
    if cmd == "login":
        user = sys.argv[2] if len(sys.argv) > 2 else "alice"
        pwd = sys.argv[3] if len(sys.argv) > 3 else None
        kinit_login(user, pwd)
    elif cmd in ["whoami", "call"]:
        call_endpoint("/api/whoami")
    elif cmd in ["admin", "flag"]:
        call_endpoint("/api/admin/flag")
    elif cmd == "klist":
        show_klist()
    else:
        console.print(f"[red]Unknown command: {cmd}[/]")

if __name__ == "__main__":
    main()
