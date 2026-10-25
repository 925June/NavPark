import time

import pytest
from fastapi.testclient import TestClient

from main import app


def create_authenticated_client(display_name="Test User"):
    client = TestClient(app)
    phone = f"139{time.time_ns() % 100_000_000:08d}"

    requested = client.post(
        "/auth/sms/request",
        json={"phone": phone, "purpose": "register"},
    )
    assert requested.status_code == 200, requested.text
    code = requested.json()["debug_code"]

    verified = client.post(
        "/auth/sms/verify",
        json={
            "phone": phone,
            "code": code,
            "purpose": "register",
            "display_name": display_name,
        },
    )
    assert verified.status_code == 200, verified.text
    assert client.cookies.get("navpark_session")

    client.auth_phone = phone
    client.auth_identity = verified.json()["user"]
    return client


@pytest.fixture
def auth_client():
    return create_authenticated_client()


@pytest.fixture
def second_auth_client():
    return create_authenticated_client("Second User")
