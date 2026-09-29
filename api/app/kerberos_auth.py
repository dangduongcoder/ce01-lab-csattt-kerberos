import os
import base64
import logging
from typing import Optional, Dict, Any, List
from pydantic import BaseModel
import gssapi

logger = logging.getLogger("api.kerberos")

class AuthResult(BaseModel):
    authenticated: bool
    principal: Optional[str] = None
    spn: Optional[str] = None
    client_ip: Optional[str] = None
    user_rid: Optional[int] = None
    groups: List[str] = []
    is_admin: bool = False
    error: Optional[str] = None

class KerberosAuthenticator:
    def __init__(self, keytab_path: str = "/shared/api.keytab", spn: str = "HTTP/api.lab.local"):
        self.keytab_path = keytab_path
        self.spn = spn
        os.environ["KRB5_KTNAME"] = self.keytab_path
        os.environ["KRB5_CONFIG"] = "/etc/krb5.conf"

    def authenticate_header(self, auth_header: Optional[str], client_ip: str) -> AuthResult:
        if not auth_header:
            return AuthResult(
                authenticated=False,
                client_ip=client_ip,
                error="Missing Authorization header"
            )

        parts = auth_header.strip().split()
        if len(parts) != 2 or parts[0].lower() != "negotiate":
            return AuthResult(
                authenticated=False,
                client_ip=client_ip,
                error="Invalid Authorization scheme. Expected 'Negotiate <token>'"
            )

        token_b64 = parts[1]
        try:
            token_bytes = base64.b64decode(token_b64)
        except Exception as e:
            return AuthResult(
                authenticated=False,
                client_ip=client_ip,
                error=f"Invalid base64 in Negotiate token: {e}"
            )

        if not os.path.exists(self.keytab_path):
            return AuthResult(
                authenticated=False,
                client_ip=client_ip,
                error=f"Keytab not found at {self.keytab_path}. KDC provisioning pending."
            )

        # Server context via standard GSSAPI
        try:
            princ_name = self.spn
            if "@" not in princ_name:
                princ_name = f"{self.spn}@LAB.LOCAL"

            server_name = gssapi.Name(princ_name, gssapi.NameType.kerberos_principal)
            server_creds = gssapi.Credentials(name=server_name, usage='accept')
            server_ctx = gssapi.SecurityContext(creds=server_creds)
            server_ctx.step(token_bytes)

            initiator = server_ctx.initiator_name
            if not initiator:
                return AuthResult(
                    authenticated=False,
                    client_ip=client_ip,
                    error="Kerberos authentication failed: initiator name empty"
                )

            norm_principal = str(initiator).strip()
            username = norm_principal.split("@")[0].lower()

            # Default regular user attributes
            is_admin = False
            user_rid = 1104
            groups = ["Domain Users (513)"]

            # Admin checks:
            if username in ["administrator", "admin", "domain_admin"] or "admin" in username:
                is_admin = True
                user_rid = 500
                groups = ["Domain Admins (512)", "Enterprise Admins (519)", "Schema Admins (518)", "Domain Users (513)"]

            return AuthResult(
                authenticated=True,
                principal=norm_principal,
                spn=self.spn,
                client_ip=client_ip,
                user_rid=user_rid,
                groups=groups,
                is_admin=is_admin,
                error=None
            )

        except Exception as e:
            logger.error(f"GSSAPI token validation exception: {e}")
            return AuthResult(
                authenticated=False,
                client_ip=client_ip,
                error=f"Kerberos GSSAPI failure: {str(e)}"
            )
