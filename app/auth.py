# app/auth.py
"""JWT authentication middleware for FastAPI."""
import hmac
import hashlib
import secrets
import time
import jwt
from fastapi import Request, HTTPException, status
from fastapi.responses import RedirectResponse, JSONResponse
from app.config import JWT_SECRET, TOKEN_EXPIRY, USERS


def hash_password(password: str) -> str:
    """Hash password with random salt using SHA-256."""
    salt = secrets.token_hex(16)
    pwd_hash = hashlib.sha256((salt + password).encode()).hexdigest()
    return f"sha256:{salt}:{pwd_hash}"


def verify_password(password: str, stored_hash: str) -> bool:
    """Verify password against stored hash."""
    parts = stored_hash.split(":")
    if len(parts) != 3 or parts[0] != "sha256":
        return False
    salt = parts[1]
    pwd_hash = hashlib.sha256((salt + password).encode()).hexdigest()
    return hmac.compare_digest(pwd_hash, parts[2])


def generate_token(username: str) -> str:
    """Generate JWT token for authenticated user."""
    payload = {
        "sub": username,
        "exp": int(time.time()) + TOKEN_EXPIRY,
    }
    return jwt.encode(payload, JWT_SECRET, algorithm="HS256")


def verify_token(token: str) -> dict | None:
    """Verify and decode JWT token. Returns payload or None."""
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
        return None


# Routes that don't require authentication
PUBLIC_PATHS = {
    "/", "/login", "/login.html", "/favicon.ico", "/robots.txt",
    "/api/auth/login", "/api/auth/verify",
    "/api/index", "/api/graph", "/api/wiki-path-map",
    "/docsify-theme.css",
}


def get_token_from_request(request: Request) -> str | None:
    """Extract Bearer token from Authorization header or cookie."""
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        return auth_header[7:]
    cookie = request.headers.get("Cookie", "")
    for part in cookie.split(";"):
        part = part.strip()
        if part.startswith("kb_token="):
            return part[len("kb_token="):]
    return None


async def auth_middleware(request: Request, call_next):
    """FastAPI middleware: redirect unauthenticated users to /login."""
    path = request.url.path.split("?")[0]

    # Public paths
    if path in PUBLIC_PATHS or path.startswith("/raw-file/") or path.startswith("/wiki/"):
        return await call_next(request)

    token = get_token_from_request(request)
    if not token or not verify_token(token):
        if path.startswith("/api/"):
            return JSONResponse(
                status_code=401,
                content={"success": False, "message": "未提供认证令牌或令牌已过期"}
            )
        return RedirectResponse(url="/login")

    return await call_next(request)
