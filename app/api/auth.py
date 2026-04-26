# app/api/auth.py
"""Authentication routes: login, verify."""
from fastapi import APIRouter, Response, Request
from app.models import LoginRequest, LoginResponse, VerifyResponse
from app.auth import verify_password, generate_token, verify_token, get_token_from_request
from app.config import TOKEN_EXPIRY, USERS

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login", response_model=LoginResponse)
async def login(data: LoginRequest, response: Response):
    """POST /api/auth/login — authenticate and return JWT."""
    username = data.username.strip()
    password = data.password

    if not username or not password:
        return LoginResponse(success=False, message="请填写账号和密码")

    user = USERS.get(username)
    if not user or not verify_password(password, user["password_hash"]):
        return LoginResponse(success=False, message="账号或密码错误")

    token = generate_token(username)
    response.set_cookie(
        key="kb_token",
        value=token,
        httponly=True,
        samesite="lax",
        max_age=TOKEN_EXPIRY,
        path="/",
    )
    return LoginResponse(success=True, message="登录成功", token=token)


@router.get("/verify")
async def verify_endpoint(request: Request):
    """GET /api/auth/verify — validate current token."""
    token = get_token_from_request(request)
    if not token:
        return VerifyResponse(valid=False, message="未提供认证令牌")

    payload = verify_token(token)
    if not payload:
        return VerifyResponse(valid=False, message="令牌无效或已过期")

    return VerifyResponse(valid=True, user=payload.get("sub", ""))
