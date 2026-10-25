import io
import ipaddress
import re
import socket
from pathlib import Path
from urllib.parse import urlsplit

import qrcode
from fastapi import APIRouter
from fastapi import HTTPException
from fastapi import Request
from fastapi.responses import FileResponse
from fastapi.responses import Response
from qrcode.image.svg import SvgPathImage

from app.config import settings


router = APIRouter()

STATIC_DIR = Path(__file__).resolve().parent / "static"


def get_lan_ip() -> str:
    """Find the IPv4 address used for the default outbound route."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as probe:
            probe.connect(("1.1.1.1", 80))
            candidate = probe.getsockname()[0]
        if _is_lan_address(candidate):
            return candidate
    except OSError:
        pass

    try:
        candidate = socket.gethostbyname(socket.gethostname())
        if _is_lan_address(candidate):
            return candidate
    except OSError:
        pass

    return "127.0.0.1"


def resolve_mobile_base_url(request: Request) -> str:
    if settings.MOBILE_BASE_URL:
        return settings.MOBILE_BASE_URL

    forwarded_host = request.headers.get("x-forwarded-host")
    request_host = forwarded_host or request.headers.get("host", "")
    hostname = _hostname_without_port(request_host)
    if request_host and not _is_local_hostname(hostname):
        scheme = (
            request.headers.get("x-forwarded-proto")
            or request.url.scheme
            or "http"
        )
        return f"{scheme}://{request_host}".rstrip("/")

    port = request.url.port or 8000
    return f"http://{get_lan_ip()}:{port}"


def mobile_access_info(request: Request) -> dict:
    url = resolve_mobile_base_url(request)
    parsed = urlsplit(url)
    secure_context = parsed.scheme == "https" or _is_local_hostname(
        parsed.hostname or ""
    )
    return {
        "url": url,
        "local_ip": get_lan_ip(),
        "secure_context": secure_context,
        "voice_supported": secure_context,
        "message": (
            "当前地址支持麦克风和定位。"
            if secure_context
            else "当前为局域网 HTTP 地址，文字聊天可用；"
            "手机浏览器通常会限制麦克风和定位，需使用 HTTPS。"
        ),
    }


@router.get("/mobile", include_in_schema=False)
def mobile_access_page():
    return FileResponse(STATIC_DIR / "mobile.html")


@router.get("/mobile/info")
def get_mobile_access_info(request: Request):
    return mobile_access_info(request)


@router.get("/mobile/qr.svg")
def get_mobile_qr(request: Request):
    url = resolve_mobile_base_url(request)
    try:
        qr = qrcode.QRCode(
            version=None,
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=10,
            border=3,
        )
        qr.add_data(url)
        qr.make(fit=True)
        image = qr.make_image(image_factory=SvgPathImage)
        output = io.BytesIO()
        image.save(output)
    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail="二维码生成失败，请确认 qrcode 依赖已安装。",
        ) from exc

    svg = re.sub(
        rb'width="[\d.]+mm"\s+height="[\d.]+mm"',
        b'width="640" height="640"',
        output.getvalue(),
        count=1,
    )
    return Response(
        content=svg,
        media_type="image/svg+xml",
        headers={"Cache-Control": "no-store"},
    )


def _hostname_without_port(host: str) -> str:
    value = (host or "").strip()
    if value.startswith("["):
        end = value.find("]")
        return value[1:end] if end > 0 else value
    return value.rsplit(":", 1)[0] if ":" in value else value


def _is_local_hostname(hostname: str) -> bool:
    normalized = (hostname or "").strip().lower()
    return normalized in {
        "localhost",
        "127.0.0.1",
        "::1",
        "0.0.0.0",
    }


def _is_lan_address(value: str) -> bool:
    try:
        address = ipaddress.ip_address(value)
    except ValueError:
        return False
    return (
        address.version == 4
        and not address.is_loopback
        and not address.is_unspecified
        and (address.is_private or address.is_link_local)
    )
