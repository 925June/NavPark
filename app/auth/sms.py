from abc import ABC
from abc import abstractmethod

import httpx

from app.config import settings


class SmsDeliveryError(RuntimeError):
    pass


class SmsProvider(ABC):
    @abstractmethod
    def send_code(
        self,
        phone: str,
        code: str,
        purpose: str,
        expires_in: int,
    ) -> None:
        pass


class ConsoleSmsProvider(SmsProvider):
    """Development provider: the code appears in logs and the API response."""

    def send_code(
        self,
        phone: str,
        code: str,
        purpose: str,
        expires_in: int,
    ) -> None:
        print(
            f"[NAVPARK SMS] phone={phone} purpose={purpose} "
            f"code={code} expires_in={expires_in}s"
        )


class WebhookSmsProvider(SmsProvider):
    """Forward OTP delivery to an external SMS gateway."""

    def send_code(
        self,
        phone: str,
        code: str,
        purpose: str,
        expires_in: int,
    ) -> None:
        if not settings.SMS_WEBHOOK_URL:
            raise SmsDeliveryError("SMS_WEBHOOK_URL is not configured")

        headers = {"Content-Type": "application/json"}
        if settings.SMS_WEBHOOK_TOKEN:
            headers["Authorization"] = (
                f"Bearer {settings.SMS_WEBHOOK_TOKEN}"
            )

        try:
            response = httpx.post(
                settings.SMS_WEBHOOK_URL,
                json={
                    "phone": phone,
                    "code": code,
                    "purpose": purpose,
                    "expires_in": expires_in,
                    "template": "navpark_login_code",
                },
                headers=headers,
                timeout=10,
            )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise SmsDeliveryError("SMS gateway request failed") from exc


def get_sms_provider() -> SmsProvider:
    if settings.SMS_PROVIDER == "console":
        return ConsoleSmsProvider()
    if settings.SMS_PROVIDER == "webhook":
        return WebhookSmsProvider()
    raise SmsDeliveryError(
        f"Unsupported SMS_PROVIDER: {settings.SMS_PROVIDER}"
    )
