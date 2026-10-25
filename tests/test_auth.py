import time
from uuid import uuid4

from fastapi.testclient import TestClient

from app.database import database
from main import app


def unique_phone():
    return f"138{time.time_ns() % 100_000_000:08d}"


def test_chat_requires_phone_login():
    client = TestClient(app)

    response = client.post(
        "/chat",
        json={"question": "离我最近的空车位在哪里"},
    )

    assert response.status_code == 401


def test_phone_registration_creates_authenticated_user(auth_client):
    me = auth_client.get("/auth/me")

    assert me.status_code == 200
    payload = me.json()["user"]
    assert payload["phone"] == f"+86{auth_client.auth_phone}"
    assert payload["display_name"] == "Test User"
    assert payload["id"] == auth_client.auth_identity["id"]


def test_sms_request_has_resend_cooldown(auth_client):
    response = auth_client.post(
        "/auth/sms/request",
        json={
            "phone": auth_client.auth_phone,
            "purpose": "login",
        },
    )

    assert response.status_code == 429
    assert "秒后重试" in response.json()["detail"]


def test_logout_revokes_session_and_phone_can_login_again(auth_client):
    phone = auth_client.auth_phone

    assert auth_client.post("/auth/logout").status_code == 200
    assert auth_client.get("/auth/me").status_code == 401

    with database.connection() as connection:
        connection.execute(
            """
            UPDATE sms_codes
            SET created_at = created_at - 61
            WHERE phone = ?
            """,
            (f"+86{phone}",),
        )

    requested = auth_client.post(
        "/auth/sms/request",
        json={"phone": phone, "purpose": "login"},
    )
    assert requested.status_code == 200, requested.text
    code = requested.json()["debug_code"]
    verified = auth_client.post(
        "/auth/sms/verify",
        json={
            "phone": phone,
            "code": code,
            "purpose": "login",
        },
    )

    assert verified.status_code == 200
    assert verified.json()["is_new_user"] is False
    assert auth_client.get("/auth/me").status_code == 200


def test_wrong_code_does_not_authenticate_user():
    client = TestClient(app)
    phone = unique_phone()
    requested = client.post(
        "/auth/sms/request",
        json={"phone": phone, "purpose": "register"},
    )
    code = requested.json()["debug_code"]
    wrong_code = "000000" if code != "000000" else "111111"

    response = client.post(
        "/auth/sms/verify",
        json={
            "phone": phone,
            "code": wrong_code,
            "purpose": "register",
        },
    )

    assert response.status_code == 400
    assert "验证码错误" in response.json()["detail"]
    assert client.get("/auth/me").status_code == 401


def test_conversation_ids_are_isolated_between_users(
    auth_client,
    second_auth_client,
):
    requested_session_id = str(uuid4())

    first = auth_client.post(
        "/chat",
        json={
            "question": "离我最近的空车位在哪里",
            "session_id": requested_session_id,
        },
    )
    second = second_auth_client.post(
        "/chat",
        json={
            "question": "离我最近的空车位在哪里",
            "session_id": requested_session_id,
        },
    )

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["session_id"] == requested_session_id
    assert second.json()["session_id"] != requested_session_id
