# middlewares/maintenance_middleware.py
from pathlib import Path
from fastapi import Request
from typing import Optional
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import HTMLResponse, JSONResponse, Response
from config.settings import settings
import json
import urllib.parse
import logging
logger = logging.getLogger("MaintenanceMiddleware")

# optional: try to import jose for unverified claims parsing
try:
    from jose import jwt as jose_jwt  # type: ignore
except Exception:
    jose_jwt = None
    logger.debug("python-jose not available; token claim parsing disabled")

# Adjust path to your project layout (this resolves relative to this file)
MAINT_PAGE_PATH = Path(__file__).resolve().parent.parent / "static" / "maintenance.html"

def _cors_headers(request: Request) -> dict:
    origin = request.headers.get("origin", "*")
    acrh = request.headers.get("access-control-request-headers", "authorization,content-type")
    return {
        "Access-Control-Allow-Origin": origin,
        "Access-Control-Allow-Credentials": "true",
        "Access-Control-Allow-Methods": "GET,POST,PUT,PATCH,DELETE,OPTIONS",
        "Access-Control-Allow-Headers": acrh,
    }

def _get_token_from_header(request: Request) -> Optional[str]:
    auth = request.headers.get("authorization") or request.headers.get("Authorization")
    if not auth:
        return None
    parts = auth.split()
    if len(parts) >= 2 and parts[0].lower() == "bearer":
        return parts[1].strip()
    return parts[0].strip() if parts else None

def _email_from_auth_cookie(request: Request) -> Optional[str]:
    raw = request.cookies.get("auth")
    if not raw:
        return None
    try:
        decoded = urllib.parse.unquote(raw)
        payload = json.loads(decoded)
        if isinstance(payload, dict):
            e = payload.get("email")
            if isinstance(e, str) and "@" in e:
                return e.strip()
            user = payload.get("user")
            if isinstance(user, dict):
                ue = user.get("email")
                if isinstance(ue, str) and "@" in ue:
                    return ue.strip()
    except Exception as exc:
        logger.debug("BetaAccessMiddleware: failed to parse auth cookie: %s", exc)
    return None

def _email_from_token_claims(token: str) -> Optional[str]:
    if not token or not jose_jwt:
        return None
    try:
        claims = jose_jwt.get_unverified_claims(token)
    except Exception as exc:
        logger.debug("BetaAccessMiddleware: failed to parse token claims: %s", exc)
        return None
    if not isinstance(claims, dict):
        return None
    for k in ("email", "preferred_username", "username", "user_email"):
        v = claims.get(k)
        if isinstance(v, str) and "@" in v:
            return v.strip()
    user = claims.get("user")
    if isinstance(user, dict):
        ue = user.get("email")
        if isinstance(ue, str) and "@" in ue:
            return ue.strip()
    return None

class MaintenanceMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        path = request.url.path or "/"

        # Allow health, static, uploads, and auth endpoints
        if (
            path.startswith("/health")
            or path.startswith("/static")
            or path.startswith("/uploads")
            or path in {
                "/api/auth/login",
                "/api/auth/register",
                "/api/auth/register/verify",
                "/api/auth/refresh",
                "/api/auth/logout",
                "/health",
                "/forbidden.html",
            }
        ):
            return await call_next(request)

        # Preflight CORS
        if request.method == "OPTIONS":
            return Response(status_code=204, headers=_cors_headers(request))

        # --- Resolve email (BetaAccess-style) ---
        user_email: Optional[str] = None
        token = _get_token_from_header(request)

        # 1) Try request.state.user
        if hasattr(request.state, "user") and request.state.user:
            try:
                u = request.state.user
                if isinstance(u, str) and "@" in u:
                    user_email = u.strip()
                else:
                    for attr in (
                        "email",
                        "user_email",
                        "preferred_email",
                        "preferred_username",
                        "username",
                        "name",
                    ):
                        val = getattr(u, attr, None)
                        if isinstance(val, str) and "@" in val:
                            user_email = val.strip()
                            break
            except Exception:
                logger.debug("MaintenanceMiddleware: error reading request.state.user", exc_info=True)

        # 2) Try auth cookie
        if not user_email:
            user_email = _email_from_auth_cookie(request)
            if user_email:
                logger.debug("MaintenanceMiddleware: email from auth cookie: %s", user_email)

        # 3) Try token claims
        if not user_email and token:
            email_from_token = _email_from_token_claims(token)
            if email_from_token:
                user_email = email_from_token
                logger.debug("MaintenanceMiddleware: email from token claims: %s", user_email)

        # Normalize for comparison
        normalized_email = user_email.strip().lower() if user_email else None
        admin_set = {str(e).strip().lower() for e in (settings.ADMIN_EMAILS or [])}

        # Debug log before decision
        logger.info(
            f"[MaintenanceMiddleware] MAINTENANCE_MODE={settings.MAINTENANCE_MODE}, "
            f"user_email={user_email!r}, normalized={normalized_email!r}, "
            f"ADMIN_EMAILS={admin_set}"
        )

        # --- Maintenance Mode Check ---
        if settings.MAINTENANCE_MODE and (not normalized_email or normalized_email not in admin_set):
            headers = _cors_headers(request)
            headers["Retry-After"] = "3600"

            accept = request.headers.get("accept", "")
            if "text/html" in accept:
                if MAINT_PAGE_PATH.exists():
                    html = MAINT_PAGE_PATH.read_text(encoding="utf-8")
                else:
                    html = "<h1>Platform is in maintenance mode.</h1><p>Please check back shortly.</p>"
                return HTMLResponse(content=html, status_code=503, headers=headers)

            return JSONResponse(
                {"detail": "Platform is in maintenance mode."},
                status_code=503,
                headers=headers,
            )

        return await call_next(request)