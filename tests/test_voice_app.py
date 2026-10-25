from fastapi.testclient import TestClient

from app.api import routes
from app.llm.deepseek_provider import (
    DeepSeekConfigurationError,
    DeepSeekProvider,
)
from app.llm.factory import LLMFactory
from main import app


client = TestClient(app)


def test_root_serves_voice_console():
    response = client.get("/")

    assert response.status_code == 200
    assert "voice-button" in response.text
    assert "route-map-svg" in response.text
    assert "route-map-floor-tabs" in response.text
    assert "DeepSeek" in response.text
    assert "NavPark" in response.text


def test_static_voice_client_is_available():
    response = client.get("/static/app.js")

    assert response.status_code == 200
    assert "webkitSpeechRecognition" in response.text
    assert "recognition.stop()" in response.text
    assert "recognition?.abort()" in response.text
    assert "scheduleRecognitionStopFallback" in response.text
    assert "window.isSecureContext" in response.text


def test_voice_client_has_cache_busted_script():
    response = client.get("/")

    assert response.status_code == 200
    assert "/static/app.js?v=20261025-mic-fix-live-map" in response.text


def test_live_route_map_client_is_available():
    response = client.get("/static/route-map.js")

    assert response.status_code == 200
    assert 'fetch("/parking/map"' in response.text
    assert "navigator.geolocation.watchPosition" in response.text
    assert "window.NavParkRouteMap" in response.text
    assert "refreshRoute" in response.text


def test_runtime_config_uses_deepseek_without_exposing_key():
    response = client.get("/config")

    assert response.status_code == 200
    payload = response.json()
    assert payload["llm_provider"] == "deepseek"
    assert payload["model"]
    assert payload["voice_input"] == "browser_web_speech"
    assert payload["parking_navigation"] == "a_star"
    assert "api_key" not in payload


def test_every_workflow_uses_the_deepseek_factory_provider():
    assert isinstance(LLMFactory.create(), DeepSeekProvider)


def test_chat_returns_actionable_error_when_deepseek_is_not_configured(
    monkeypatch,
    auth_client,
):
    def raise_missing_key(_state):
        raise DeepSeekConfigurationError("DEEPSEEK_API_KEY is not configured")

    monkeypatch.setattr(routes.graph, "invoke", raise_missing_key)
    response = auth_client.post(
        "/chat",
        json={"question": "停车多少钱？"},
    )

    assert response.status_code == 503
    assert "DEEPSEEK_API_KEY" in response.json()["detail"]
