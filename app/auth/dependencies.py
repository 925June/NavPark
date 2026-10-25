from urllib.parse import urlsplit

from fastapi import HTTPException
from fastapi import Request

from app.auth.service import auth_service
from app.config import settings


def get_current_user(request: Request):
    token = request.cookies.get(settings.AUTH_COOKIE_NAME)
    user = auth_service.authenticate_session(token)
    if not user:
        raise HTTPException(
            status_code=401,
            detail="请先登录后再使用此功能。",
        )
    return user


def require_same_origin(request: Request):
    origin = request.headers.get("origin")
    host = request.headers.get("host")
    if origin and urlsplit(origin).netloc != host:
        raise HTTPException(
            status_code=403,
            detail="请求来源校验失败。",
        )
