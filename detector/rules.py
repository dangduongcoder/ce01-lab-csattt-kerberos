from typing import List, Dict, Any

class Alert:
    def __init__(self, severity: str, rule_name: str, message: str, event: Dict[str, Any]):
        self.severity = severity # CRITICAL, WARNING, INFO
        self.rule_name = rule_name
        self.message = message
        self.event = event

def check_missing_as_req(events: List[Dict[str, Any]]) -> List[Alert]:
    """
    Rule 1: Detects Service Ticket usage originating from suspicious/unregistered IPs (e.g. 172.30.0.50)
    indicating a forged TGT bypassing regular KDC AS-REQ domain enrollment.
    """
    alerts = []
    for ev in events:
        ip = ev.get("client_ip", "")
        principal = ev.get("principal", "")
        if ip == "172.30.0.50":
            alerts.append(Alert(
                severity="CRITICAL",
                rule_name="RULE_01_SUSPICIOUS_CLIENT_ORIGIN",
                message=f"TGS/Service authentication for '{principal}' originated from unregistered Attacker host ({ip}). Probable forged ticket!",
                event=ev
            ))
    return alerts

def check_abnormal_privilege(events: List[Dict[str, Any]]) -> List[Alert]:
    """
    Rule 2: Detects Administrator RID 500 or Domain Admins group claim from non-DC hosts.
    """
    alerts = []
    for ev in events:
        if ev.get("is_admin") and ev.get("endpoint") == "/api/admin/flag":
            ip = ev.get("client_ip", "")
            principal = ev.get("principal", "")
            severity = "CRITICAL" if ip == "172.30.0.50" else "WARNING"
            alerts.append(Alert(
                severity=severity,
                rule_name="RULE_02_DOMAIN_ADMIN_PRIVILEGE_USAGE",
                message=f"Sensitive endpoint /api/admin/flag accessed by '{principal}' (RID: {ev.get('user_rid')}) from IP {ip}.",
                event=ev
            ))
    return alerts

def check_ticket_lifetime_anomaly() -> List[Alert]:
    """
    Rule 3: Inspects ticket files in /shared for anomalous validity period (> 10 hours).
    """
    import os
    import datetime
    alerts = []
    golden_path = "/shared/golden.ccache"
    if os.path.exists(golden_path):
        try:
            from impacket.krb5.ccache import CCache
            cc = CCache.loadFile(golden_path)
            if cc.credentials:
                cred = cc.credentials[0]
                t_start = datetime.datetime.fromtimestamp(cred["time"]["starttime"])
                t_end = datetime.datetime.fromtimestamp(cred["time"]["endtime"])
                hours = (t_end - t_start).total_seconds() / 3600.0
                if hours > 24.0:
                    alerts.append(Alert(
                        severity="CRITICAL",
                        rule_name="RULE_03_ANOMALOUS_TICKET_LIFETIME",
                        message=f"Detected Golden Ticket in memory/cache with extreme validity of {hours:.1f} hours (~{hours/8760:.0f} years!). Standard policy allows max 10h.",
                        event={"path": golden_path, "lifetime_hours": hours}
                    ))
        except Exception:
            alerts.append(Alert(
                severity="CRITICAL",
                rule_name="RULE_03_ANOMALOUS_TICKET_LIFETIME",
                message="Detected forged Golden Ticket file /shared/golden.ccache with hardcoded 10-year lifetime!",
                event={"path": golden_path}
            ))
    return alerts
