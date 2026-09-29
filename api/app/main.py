import os
import logging
from datetime import datetime, timezone
from fastapi import FastAPI, Request, Response, status
from fastapi.responses import JSONResponse, HTMLResponse
from api.app.kerberos_auth import KerberosAuthenticator
from api.app.audit_log import log_auth_event, get_recent_events

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("api.main")

app = FastAPI(
    title="Kerberos Protected Service API",
    description="FastAPI service authenticating via Kerberos GSSAPI/SPNEGO for CSATTT Lab",
    version="1.0.0"
)

authenticator = KerberosAuthenticator(
    keytab_path=os.getenv("KEYTAB_PATH", "/shared/api.keytab"),
    spn=os.getenv("SERVICE_SPN", "HTTP/api.lab.local")
)

FLAG_VALUE = "CSATTT{G0LD3N_T1CK3T_KRBTGT_P0WN3D_2026}"

@app.get("/api/health")
async def health(request: Request):
    keytab_exists = os.path.exists(authenticator.keytab_path)
    return {
        "status": "healthy" if keytab_exists else "initializing",
        "service": authenticator.spn,
        "keytab_ready": keytab_exists,
        "server_time": datetime.now(timezone.utc).isoformat(),
        "client_ip": request.client.host
    }

@app.get("/api/whoami")
async def whoami(request: Request):
    auth_header = request.headers.get("Authorization")
    client_ip = request.client.host

    auth_result = authenticator.authenticate_header(auth_header, client_ip)

    log_auth_event(
        client_ip=client_ip,
        endpoint="/api/whoami",
        authenticated=auth_result.authenticated,
        principal=auth_result.principal,
        spn=auth_result.spn,
        user_rid=auth_result.user_rid,
        groups=auth_result.groups,
        is_admin=auth_result.is_admin,
        error=auth_result.error,
        auth_header_present=bool(auth_header)
    )

    if not auth_result.authenticated:
        return Response(
            content=JSONResponse(content={"error": auth_result.error}).body,
            status_code=status.HTTP_401_UNAUTHORIZED,
            headers={"WWW-Authenticate": "Negotiate"},
            media_type="application/json"
        )

    return {
        "authenticated": True,
        "principal": auth_result.principal,
        "service": auth_result.spn,
        "client_ip": auth_result.client_ip,
        "user_rid": auth_result.user_rid,
        "groups": auth_result.groups,
        "is_admin": auth_result.is_admin,
        "message": f"Welcome, {auth_result.principal}! Your identity has been cryptographically validated via Kerberos."
    }

@app.get("/api/profile")
async def profile(request: Request):
    return await whoami(request)

@app.get("/api/admin/flag")
async def admin_flag(request: Request):
    auth_header = request.headers.get("Authorization")
    client_ip = request.client.host

    auth_result = authenticator.authenticate_header(auth_header, client_ip)

    log_auth_event(
        client_ip=client_ip,
        endpoint="/api/admin/flag",
        authenticated=auth_result.authenticated,
        principal=auth_result.principal,
        spn=auth_result.spn,
        user_rid=auth_result.user_rid,
        groups=auth_result.groups,
        is_admin=auth_result.is_admin,
        error=auth_result.error,
        auth_header_present=bool(auth_header)
    )

    if not auth_result.authenticated:
        return Response(
            content=JSONResponse(content={"error": auth_result.error}).body,
            status_code=status.HTTP_401_UNAUTHORIZED,
            headers={"WWW-Authenticate": "Negotiate"},
            media_type="application/json"
        )

    if not auth_result.is_admin:
        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content={
                "access": "DENIED",
                "principal": auth_result.principal,
                "user_rid": auth_result.user_rid,
                "groups": auth_result.groups,
                "error": "Forbidden: Requires 'Domain Admins' (RID 512) or Administrator (RID 500) privileges."
            }
        )

    return {
        "access": "GRANTED",
        "principal": auth_result.principal,
        "user_rid": auth_result.user_rid,
        "groups": auth_result.groups,
        "flag": FLAG_VALUE,
        "message": "CONGRATULATIONS! You have successfully exploited Kerberos Golden Ticket architecture to achieve Domain Administrator access!"
    }

@app.get("/api/logs")
async def get_logs():
    return {"events": get_recent_events(limit=50)}

@app.get("/", response_class=HTMLResponse)
async def dashboard():
    events = get_recent_events(limit=15)
    rows_html = ""
    for ev in reversed(events):
        badge_class = "success" if ev.get("authenticated") else "danger"
        admin_badge = '<span class="badge admin">ADMIN</span>' if ev.get("is_admin") else '<span class="badge user">USER</span>'
        rows_html += f"""
        <tr>
            <td>{ev.get('timestamp', '')[:19]}</td>
            <td><code>{ev.get('client_ip', '')}</code></td>
            <td><code>{ev.get('endpoint', '')}</code></td>
            <td><b>{ev.get('principal') or 'Anonymous'}</b></td>
            <td>{admin_badge}</td>
            <td><span class="badge {badge_class}">{'OK' if ev.get('authenticated') else 'FAILED'}</span></td>
            <td><small>{ev.get('error') or 'None'}</small></td>
        </tr>
        """

    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Kerberos Lab - Live Dashboard</title>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <meta http-equiv="refresh" content="5">
        <style>
            body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #0f172a; color: #f8fafc; margin: 0; padding: 24px; }}
            .container {{ max-width: 1100px; margin: 0 auto; }}
            h1 {{ color: #38bdf8; margin-bottom: 6px; }}
            p.sub {{ color: #94a3b8; margin-top: 0; margin-bottom: 24px; }}
            .cards {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 16px; margin-bottom: 24px; }}
            .card {{ background: #1e293b; border-radius: 8px; padding: 16px; border: 1px solid #334155; }}
            .card h3 {{ margin: 0 0 8px 0; font-size: 14px; color: #94a3b8; }}
            .card p {{ margin: 0; font-size: 18px; font-weight: bold; color: #f1f5f9; }}
            table {{ width: 100%; border-collapse: collapse; background: #1e293b; border-radius: 8px; overflow: hidden; }}
            th, td {{ padding: 12px 16px; text-align: left; border-bottom: 1px solid #334155; font-size: 14px; }}
            th {{ background: #0f172a; color: #94a3b8; font-weight: 600; }}
            .badge {{ padding: 4px 8px; border-radius: 4px; font-size: 11px; font-weight: bold; }}
            .badge.success {{ background: #065f46; color: #34d399; }}
            .badge.danger {{ background: #991b1b; color: #f87171; }}
            .badge.admin {{ background: #7c2d12; color: #fb923c; }}
            .badge.user {{ background: #1e3a8a; color: #60a5fa; }}
            code {{ background: #0f172a; padding: 2px 6px; border-radius: 4px; color: #38bdf8; }}
            .flow {{ background: #1e293b; padding: 16px; border-radius: 8px; border: 1px solid #334155; margin-bottom: 24px; font-family: monospace; white-space: pre; color: #a5f3fc; overflow-x: auto; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🛡️ CSATTT Kerberos Lab Dashboard</h1>
            <p class="sub">Môi trường thử nghiệm xác thực Kerberos & Tấn công Golden Ticket (Auto-refresh 5s)</p>

            <div class="cards">
                <div class="card">
                    <h3>REALM</h3>
                    <p>LAB.LOCAL</p>
                </div>
                <div class="card">
                    <h3>DOMAIN CONTROLLER</h3>
                    <p>dc.lab.local (172.20.0.10)</p>
                </div>
                <div class="card">
                    <h3>SERVICE PRINCIPAL (SPN)</h3>
                    <p>HTTP/api.lab.local</p>
                </div>
                <div class="card">
                    <h3>AUTH PROTOCOL</h3>
                    <p>GSSAPI / SPNEGO</p>
                </div>
            </div>

            <div class="flow">
[1. AS-REQ] Client -> KDC (dc.lab.local)        : Request TGT for Alice
[2. AS-REP] KDC -> Client                       : TGT (Encrypted with krbtgt key)
[3. TGS-REQ] Client -> KDC                      : Request Service Ticket for HTTP/api.lab.local
[4. TGS-REP] KDC -> Client                      : Service Ticket (Encrypted with api service key)
[5. AP-REQ] Client -> API Server (api.lab.local): HTTP Authorization: Negotiate &lt;Ticket&gt;
[6. AP-REP] API Server -> Client                : 200 OK Authenticated Principal
            </div>

            <h2>📋 Real-time Authentication Audit Log</h2>
            <table>
                <thead>
                    <tr>
                        <th>Time</th>
                        <th>Client IP</th>
                        <th>Endpoint</th>
                        <th>Principal</th>
                        <th>Role</th>
                        <th>Status</th>
                        <th>Detail</th>
                    </tr>
                </thead>
                <tbody>
                    {rows_html if rows_html else '<tr><td colspan="7" style="text-align:center; color:#64748b;">Chưa có sự kiện xác thực nào. Hãy chạy demo từ Client hoặc Attacker.</td></tr>'}
                </tbody>
            </table>
        </div>
    </body>
    </html>
    """
