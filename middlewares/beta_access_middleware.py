# middlewares/beta_access_middleware.py
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse, HTMLResponse, Response
import json
import urllib.parse
import logging
from typing import Optional

from config.settings import settings

logger = logging.getLogger("BetaAccessMiddleware")

# optional: try to import jose for unverified claims parsing
try:
    from jose import jwt as jose_jwt  # type: ignore
except Exception:
    jose_jwt = None
    logger.debug("python-jose not available; token claim parsing disabled")

FORBIDDEN_HTML = "<h1>Access restricted — beta testing only.</h1>"

def _cors_headers(request: Request) -> dict:
    origin = request.headers.get("origin", "*")
    return {
        "Access-Control-Allow-Origin": origin,
        "Access-Control-Allow-Credentials": "true",
        "Access-Control-Allow-Methods": "GET,POST,PUT,PATCH,DELETE,OPTIONS",
        "Access-Control-Allow-Headers": "Authorization,Content-Type",
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

class BetaAccessMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        path = request.url.path or "/"

        # Allow static files and auth/health whitelist immediately (uploads NOT here)
        if (
            path.startswith("/static")
            or path in {
                "/api/auth/login",
                "/api/auth/register",
                "/api/auth/register/verify",
                "/api/auth/refresh",
                "/api/auth/logout",
                "/api/auth/otp/send",
                "/api/auth/forgot-password-request",
                "/api/auth/forgot-password-verify",
                "/health",
                "/forbidden.html",
            }
        ):
            response = await call_next(request)
            for k, v in _cors_headers(request).items():
                response.headers.setdefault(k, v)
            return response

        # Preflight CORS
        if request.method == "OPTIONS":
            return Response(status_code=204, headers=_cors_headers(request))

        # If beta gating is disabled, allow everything (still NOT allowing uploads bypass here)
        if not getattr(settings, "BETA_ACCESS_MODE", False):
            response = await call_next(request)
            for k, v in _cors_headers(request).items():
                response.headers.setdefault(k, v)
            return response

        # Extract token early
        token = _get_token_from_header(request)
        upload_service_token = getattr(settings, "UPLOAD_ACCESS_TOKEN", None)
        
        # --- STRICT /uploads handling: only allow if service token matches and method is GET/HEAD
        if path.startswith("/uploads"):
            raw_auth = request.headers.get("authorization") or request.headers.get("Authorization")
            logger.info("[BetaAccessMiddleware] raw Authorization header received: %r", raw_auth)
            logger.info("[BetaAccessMiddleware] upload query params: %r", dict(request.query_params))

            beta_tester_emails = set(getattr(settings, "BETA_TESTER_EMAILS", []) or [])
            upload_service_token = getattr(settings, "UPLOAD_ACCESS_TOKEN", None)

            # Get bearer token (if present)
            token = _get_token_from_header(request)

            # Try to identify user email
            user_email = getattr(request.state, "user_email", None)
            if not user_email:
                user_email = _email_from_auth_cookie(request)
            if not user_email and token:
                user_email = _email_from_token_claims(token)

            # Allow if service token matches
            allowed_for_upload = (
                token
                and upload_service_token
                and str(token) == str(upload_service_token)
                and request.method in ("GET", "HEAD")
            )

            # Or allow if beta tester email matches
            if user_email and user_email in beta_tester_emails and request.method in ("GET", "HEAD"):
                allowed_for_upload = True
                logger.info(f"BetaAccessMiddleware: user {user_email} is in BETA_TESTER_EMAILS; allowing /uploads request")

            if allowed_for_upload:
                logger.info("BetaAccessMiddleware: access allowed to /uploads")
                response = await call_next(request)
                for k, v in _cors_headers(request).items():
                    response.headers.setdefault(k, v)
                return response

            # Deny if neither rule matched
            headers = _cors_headers(request)
            logger.info("[BetaAccessMiddleware] token from header: %r, expected: %r", token, upload_service_token)
            logger.info(f"[BetaAccessMiddleware] Denying /uploads access. path={path}, token_present={bool(token)}, user_email={user_email}")
            accept = request.headers.get("accept", "")
            if "text/html" in accept:
                return HTMLResponse(FORBIDDEN_HTML, status_code=403, headers=headers)
            return JSONResponse({"detail": "Beta access only"}, status_code=403, headers=headers)
        # 1) Try request.state.user (if auth middleware set it)
        user_email: Optional[str] = None
        if hasattr(request.state, "user") and request.state.user:
            try:
                u = request.state.user
                if isinstance(u, str) and "@" in u:
                    user_email = u.strip()
                else:
                    for attr in ("email", "user_email", "preferred_email", "preferred_username", "username", "name"):
                        val = getattr(u, attr, None)
                        if isinstance(val, str) and "@" in val:
                            user_email = val.strip()
                            break
            except Exception:
                logger.debug("BetaAccessMiddleware: error reading request.state.user", exc_info=True)

        # 2) Try auth cookie
        if not user_email:
            user_email = _email_from_auth_cookie(request)
            if user_email:
                logger.debug("BetaAccessMiddleware: email from auth cookie: %s", user_email)

        # 3) Try token claims
        if not user_email and token:
            email_from_token = _email_from_token_claims(token)
            if email_from_token:
                user_email = email_from_token
                logger.debug("BetaAccessMiddleware: email from token claims: %s", user_email)

        # Check whitelist
        allowed = False
        if user_email:
            normalized = user_email.strip().lower()
            allowed_set = {str(x).strip().lower() for x in getattr(settings, "BETA_TESTER_EMAILS", []) or []}
            if normalized in allowed_set:
                allowed = True
            else:
                logger.info(f"[BetaAccessMiddleware] email found but not in whitelist: {user_email}")

        if allowed:
            response = await call_next(request)
            for k, v in _cors_headers(request).items():
                response.headers.setdefault(k, v)
            return response

        # Deny all other requests
        headers = _cors_headers(request)
        accept = request.headers.get("accept", "")
        logger.info("Headers at /api: %s", dict(request.headers))
        logger.info("Cookies at /api: %s", request.cookies)
        logger.info(f"[BetaAccessMiddleware] Access denied. path={path}, user_email={user_email}")
        if "text/html" in accept:
            return HTMLResponse(FORBIDDEN_HTML, status_code=403, headers=headers)
        return JSONResponse({"detail": "Beta access only"}, status_code=403, headers=headers)
