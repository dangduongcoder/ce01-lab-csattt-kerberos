import os
import json
import logging
from datetime import datetime, timezone
from typing import Dict, Any

AUDIT_LOG_FILE = "/shared/api_auth.log"
logger = logging.getLogger("api.audit")

def log_auth_event(
    client_ip: str,
    endpoint: str,
    authenticated: bool,
    principal: str = None,
    spn: str = None,
    user_rid: int = None,
    groups: list = None,
    is_admin: bool = False,
    error: str = None,
    auth_header_present: bool = True
):
    event = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "client_ip": client_ip,
        "endpoint": endpoint,
        "authenticated": authenticated,
        "principal": principal,
        "spn": spn,
        "user_rid": user_rid,
        "groups": groups or [],
        "is_admin": is_admin,
        "auth_header_present": auth_header_present,
        "error": error
    }

    try:
        os.makedirs(os.path.dirname(AUDIT_LOG_FILE), exist_ok=True)
        with open(AUDIT_LOG_FILE, "a") as f:
            f.write(json.dumps(event) + "\n")
    except Exception as e:
        logger.error(f"Failed to write to audit log: {e}")

    logger.info(f"AUDIT: IP={client_ip} Principal={principal} Auth={authenticated} Admin={is_admin}")

def get_recent_events(limit: int = 50):
    events = []
    if not os.path.exists(AUDIT_LOG_FILE):
        return events
    try:
        with open(AUDIT_LOG_FILE, "r") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        events.append(json.loads(line))
                    except Exception:
                        pass
        return events[-limit:]
    except Exception as e:
        logger.error(f"Failed to read audit log: {e}")
        return []

def clear_audit_logs() -> bool:
    try:
        if os.path.exists(AUDIT_LOG_FILE):
            with open(AUDIT_LOG_FILE, "w") as f:
                f.truncate(0)
        logger.info("AUDIT: All audit log events have been cleared.")
        return True
    except Exception as e:
        logger.error(f"Failed to clear audit log: {e}")
        return False
