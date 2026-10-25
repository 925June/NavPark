from fastapi.testclient import TestClient

from app.config import settings
from main import app


client = TestClient(app)


def test_mobile_access_page_is_available():
    response = client.get("/mobile")

    assert response.status_code == 200
    assert "PHONE ACCESS" in response.text
    assert "/mobile/qr.svg" in response.text
    assert "/static/mobile.js" in response.text


def test_desktop_page_links_to_mobile_access():
    response = client.get("/")

    assert response.status_code == 200
    assert 'href="/mobile"' in response.text
    assert "手机访问" in response.text


def test_mobile_info_uses_lan_address_when_opened_locally():
    response = client.get(
        "/mobile/info",
        headers={"host": "127.0.0.1:8000"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["url"].startswith("http://")
    assert payload["url"].endswith(":8000")
    assert payload["secure_context"] is False
    assert "文字聊天可用" in payload["message"]


def test_mobile_info_prefers_configured_https_origin(monkeypatch):
    monkeypatch.setattr(
        settings,
        "MOBILE_BASE_URL",
        "https://navpark.example.com",
    )

    response = client.get("/mobile/info")
    payload = response.json()

    assert payload["url"] == "https://navpark.example.com"
    assert payload["secure_context"] is True
    assert payload["voice_supported"] is True


def test_mobile_qr_returns_svg():
    response = client.get("/mobile/qr.svg")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("image/svg+xml")
    assert response.content.startswith(b"<?xml")
    assert b"<svg" in response.content
