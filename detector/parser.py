import os
import json
from typing import List, Dict, Any

API_LOG_FILE = "/shared/api_auth.log"

def parse_auth_events() -> List[Dict[str, Any]]:
    events = []
    if not os.path.exists(API_LOG_FILE):
        return events

    try:
        with open(API_LOG_FILE, "r") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        events.append(json.loads(line))
                    except Exception:
                        pass
    except Exception as e:
        print(f"[-] Error reading audit log: {e}")
    return events
