from typing import Literal
from typing import Optional

from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from fastapi import Request
from fastapi import Response
from pydantic import BaseModel
from pydantic import Field

from app.auth.dependencies import get_current_user
from app.auth.dependencies import require_same_origin
from app.auth.service import AuthServiceError
from app.auth.service import auth_service
from app.config import settings


router = APIRouter(prefix="/auth", tags=["authentication"])


class SmsCodeRequest(BaseModel):
    phone: str = Field(min_length=6, max_length=24)
    purpose: Literal["register", "login"]


class SmsCodeVerifyRequest(BaseModel):
    phone: str = Field(min_length=6, max_length=24)
    code: str = Field(min_length=6, max_length=6)
    purpose: Literal["register", "login"]
    display_name: Optional[str] = Field(
        default=None,
        max_length=40,
    )


def _raise_auth_error(exc: AuthServiceError):
    raise HTTPException(
        status_code=exc.status_code,
        detail=exc.message,
    ) from exc


def _set_session_cookie(
    response: Response,
    raw_token: str,
):
    response.set_cookie(
        key=settings.AUTH_COOKIE_NAME,
        value=raw_token,
        max_age=settings.AUTH_SESSION_DAYS * 86_400,
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite="lax",
        path="/",
    )


@router.post(
    "/sms/request",
    dependencies=[Depends(require_same_origin)],
)
def request_sms_code(payload: SmsCodeRequest):
    try:
        return auth_service.request_code(
            payload.phone,
            payload.purpose,
        )
    except AuthServiceError as exc:
        _raise_auth_error(exc)


@router.post(
    "/sms/verify",
    dependencies=[Depends(require_same_origin)],
)
def verify_sms_code(
    payload: SmsCodeVerifyRequest,
    response: Response,
):
    try:
        result = auth_service.verify_code(
            payload.phone,
            payload.code,
            payload.purpose,
            payload.display_name,
        )
    except AuthServiceError as exc:
        _raise_auth_error(exc)

    _set_session_cookie(response, result["raw_token"])
    return {
        "user": result["user"],
        "is_new_user": result["is_new_user"],
        "expires_at": result["expires_at"],
    }


@router.get("/me")
def current_user(user=Depends(get_current_user)):
    return {"user": user}


@router.post(
    "/logout",
    dependencies=[Depends(require_same_origin)],
)
def logout(request: Request, response: Response):
    token = request.cookies.get(settings.AUTH_COOKIE_NAME)
    auth_service.revoke_session(token)
    response.delete_cookie(
        key=settings.AUTH_COOKIE_NAME,
        path="/",
        secure=settings.COOKIE_SECURE,
        httponly=True,
        samesite="lax",
    )
    return {"message": "已退出登录。"}
