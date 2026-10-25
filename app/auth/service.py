import hashlib
import hmac
import re
import secrets
import time
from typing import Dict
from typing import Optional
from uuid import uuid4

from app.auth.sms import SmsDeliveryError
from app.auth.sms import get_sms_provider
from app.config import settings
from app.database import database


class AuthServiceError(Exception):
    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


class AuthService:
    MAX_CODE_ATTEMPTS = 5
    MAX_CODES_PER_HOUR = 5
    PHONE_PATTERN = re.compile(r"^1[3-9]\d{9}$")
    CODE_PATTERN = re.compile(r"^\d{6}$")

    def __init__(self):
        if (
            settings.APP_ENV == "production"
            and settings.AUTH_SECRET
            == "development-only-change-this-secret"
        ):
            raise RuntimeError(
                "AUTH_SECRET must be changed in production"
            )

    @staticmethod
    def _now() -> int:
        return int(time.time())

    def normalize_phone(self, phone: str) -> str:
        compact = re.sub(r"[\s-]", "", phone or "")
        if compact.startswith("+86"):
            compact = compact[3:]
        elif compact.startswith("0086"):
            compact = compact[4:]

        if not self.PHONE_PATTERN.fullmatch(compact):
            raise AuthServiceError("请输入有效的中国大陆手机号。")
        return f"+86{compact}"

    def request_code(
        self,
        phone: str,
        purpose: str,
    ) -> Dict:
        normalized_phone = self.normalize_phone(phone)
        if purpose not in {"register", "login"}:
            raise AuthServiceError("不支持的验证码用途。")
        if (
            settings.APP_ENV == "production"
            and settings.SMS_PROVIDER == "console"
        ):
            raise AuthServiceError("生产环境未配置短信服务。", 503)

        now = self._now()
        code = f"{secrets.randbelow(1_000_000):06d}"
        code_hash = self._hash_code(normalized_phone, purpose, code)
        expires_at = now + settings.SMS_CODE_TTL_SECONDS

        with database.connection() as connection:
            user = connection.execute(
                "SELECT id FROM users WHERE phone = ?",
                (normalized_phone,),
            ).fetchone()
            if purpose == "register" and user:
                raise AuthServiceError("该手机号已注册，请直接登录。")
            if purpose == "login" and not user:
                raise AuthServiceError("该手机号尚未注册，请先注册。")

            latest = connection.execute(
                """
                SELECT created_at
                FROM sms_codes
                WHERE phone = ?
                ORDER BY id DESC
                LIMIT 1
                """,
                (normalized_phone,),
            ).fetchone()
            if latest:
                elapsed = now - latest["created_at"]
                if elapsed < settings.SMS_RESEND_COOLDOWN_SECONDS:
                    remaining = (
                        settings.SMS_RESEND_COOLDOWN_SECONDS - elapsed
                    )
                    raise AuthServiceError(
                        f"操作过于频繁，请在 {remaining} 秒后重试。",
                        429,
                    )

            hourly_count = connection.execute(
                """
                SELECT COUNT(*) AS count
                FROM sms_codes
                WHERE phone = ? AND created_at > ?
                """,
                (normalized_phone, now - 3600),
            ).fetchone()["count"]
            if hourly_count >= self.MAX_CODES_PER_HOUR:
                raise AuthServiceError(
                    "该手机号一小时内验证码次数过多，请稍后再试。",
                    429,
                )

            connection.execute(
                """
                UPDATE sms_codes
                SET consumed_at = ?
                WHERE phone = ? AND consumed_at IS NULL
                """,
                (now, normalized_phone),
            )
            connection.execute(
                """
                INSERT INTO sms_codes(
                    phone, purpose, code_hash, expires_at, created_at
                )
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    normalized_phone,
                    purpose,
                    code_hash,
                    expires_at,
                    now,
                ),
            )

        try:
            get_sms_provider().send_code(
                normalized_phone,
                code,
                purpose,
                settings.SMS_CODE_TTL_SECONDS,
            )
        except SmsDeliveryError as exc:
            with database.connection() as connection:
                connection.execute(
                    """
                    UPDATE sms_codes
                    SET consumed_at = ?
                    WHERE phone = ? AND consumed_at IS NULL
                    """,
                    (self._now(), normalized_phone),
                )
            raise AuthServiceError("短信发送失败，请稍后重试。", 502) from exc

        result = {
            "message": "验证码已发送。",
            "phone": normalized_phone,
            "expires_in": settings.SMS_CODE_TTL_SECONDS,
            "resend_after": settings.SMS_RESEND_COOLDOWN_SECONDS,
        }
        if (
            settings.SMS_PROVIDER == "console"
            and settings.APP_ENV != "production"
        ):
            result["debug_code"] = code
        return result

    def verify_code(
        self,
        phone: str,
        code: str,
        purpose: str,
        display_name: Optional[str] = None,
    ):
        normalized_phone = self.normalize_phone(phone)
        if purpose not in {"register", "login"}:
            raise AuthServiceError("不支持的验证码用途。")
        if not self.CODE_PATTERN.fullmatch(code or ""):
            raise AuthServiceError("请输入 6 位数字验证码。")

        now = self._now()
        with database.connection() as connection:
            record = connection.execute(
                """
                SELECT *
                FROM sms_codes
                WHERE phone = ?
                  AND purpose = ?
                  AND consumed_at IS NULL
                ORDER BY id DESC
                LIMIT 1
                """,
                (normalized_phone, purpose),
            ).fetchone()
            if not record:
                raise AuthServiceError("验证码不存在或已失效，请重新获取。")
            if record["expires_at"] < now:
                connection.execute(
                    "UPDATE sms_codes SET consumed_at = ? WHERE id = ?",
                    (now, record["id"]),
                )
                raise AuthServiceError("验证码已过期，请重新获取。")
            if record["attempts"] >= self.MAX_CODE_ATTEMPTS:
                connection.execute(
                    "UPDATE sms_codes SET consumed_at = ? WHERE id = ?",
                    (now, record["id"]),
                )
                raise AuthServiceError("验证码尝试次数过多，请重新获取。", 429)

            expected_hash = self._hash_code(
                normalized_phone,
                purpose,
                code,
            )
            if not hmac.compare_digest(
                record["code_hash"],
                expected_hash,
            ):
                connection.execute(
                    """
                    UPDATE sms_codes
                    SET attempts = attempts + 1
                    WHERE id = ?
                    """,
                    (record["id"],),
                )
                remaining = self.MAX_CODE_ATTEMPTS - record["attempts"] - 1
                raise AuthServiceError(
                    f"验证码错误，还可尝试 {remaining} 次。"
                )

            connection.execute(
                "UPDATE sms_codes SET consumed_at = ? WHERE id = ?",
                (now, record["id"]),
            )
            user = connection.execute(
                "SELECT * FROM users WHERE phone = ?",
                (normalized_phone,),
            ).fetchone()

            is_new_user = False
            if purpose == "register":
                if user:
                    raise AuthServiceError("该手机号已注册，请直接登录。")
                user_id = str(uuid4())
                safe_name = self._clean_display_name(display_name)
                connection.execute(
                    """
                    INSERT INTO users(
                        id, phone, display_name, status,
                        created_at, last_login_at
                    )
                    VALUES (?, ?, ?, 'active', ?, ?)
                    """,
                    (
                        user_id,
                        normalized_phone,
                        safe_name,
                        now,
                        now,
                    ),
                )
                is_new_user = True
            else:
                if not user:
                    raise AuthServiceError("该手机号尚未注册，请先注册。")
                if user["status"] != "active":
                    raise AuthServiceError("该账号当前不可用。", 403)
                connection.execute(
                    "UPDATE users SET last_login_at = ? WHERE id = ?",
                    (now, user["id"]),
                )

            user = connection.execute(
                "SELECT * FROM users WHERE phone = ?",
                (normalized_phone,),
            ).fetchone()
            raw_token = secrets.token_urlsafe(48)
            token_hash = self._hash_token(raw_token)
            session_expires_at = (
                now + settings.AUTH_SESSION_DAYS * 86_400
            )
            connection.execute(
                """
                INSERT INTO auth_sessions(
                    id, user_id, token_hash, created_at,
                    expires_at, last_seen_at
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    str(uuid4()),
                    user["id"],
                    token_hash,
                    now,
                    session_expires_at,
                    now,
                ),
            )

        return {
            "user": self._serialize_user(user),
            "is_new_user": is_new_user,
            "raw_token": raw_token,
            "expires_at": session_expires_at,
        }

    def authenticate_session(self, raw_token: str) -> Optional[Dict]:
        if not raw_token:
            return None

        token_hash = self._hash_token(raw_token)
        now = self._now()
        with database.connection() as connection:
            session = connection.execute(
                """
                SELECT
                    s.id AS session_id,
                    s.expires_at,
                    u.id,
                    u.phone,
                    u.display_name,
                    u.status,
                    u.created_at,
                    u.last_login_at
                FROM auth_sessions s
                JOIN users u ON u.id = s.user_id
                WHERE s.token_hash = ?
                  AND s.revoked_at IS NULL
                  AND s.expires_at > ?
                  AND u.status = 'active'
                """,
                (token_hash, now),
            ).fetchone()
            if not session:
                return None
            connection.execute(
                """
                UPDATE auth_sessions
                SET last_seen_at = ?
                WHERE id = ?
                """,
                (now, session["session_id"]),
            )
            return self._serialize_user(session)

    def revoke_session(self, raw_token: str) -> None:
        if not raw_token:
            return
        with database.connection() as connection:
            connection.execute(
                """
                UPDATE auth_sessions
                SET revoked_at = ?
                WHERE token_hash = ? AND revoked_at IS NULL
                """,
                (self._now(), self._hash_token(raw_token)),
            )

    def _hash_code(
        self,
        phone: str,
        purpose: str,
        code: str,
    ) -> str:
        payload = f"{phone}:{purpose}:{code}".encode("utf-8")
        return hmac.new(
            settings.AUTH_SECRET.encode("utf-8"),
            payload,
            hashlib.sha256,
        ).hexdigest()

    @staticmethod
    def _hash_token(raw_token: str) -> str:
        return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()

    @staticmethod
    def _clean_display_name(display_name: Optional[str]) -> str:
        name = (display_name or "").strip()
        if len(name) > 40:
            raise AuthServiceError("昵称不能超过 40 个字符。")
        return name or "NavPark 用户"

    @staticmethod
    def _serialize_user(user) -> Dict:
        return {
            "id": user["id"],
            "phone": user["phone"],
            "display_name": user["display_name"],
            "created_at": user["created_at"],
            "last_login_at": user["last_login_at"],
        }


auth_service = AuthService()
