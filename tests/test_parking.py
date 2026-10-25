from fastapi.testclient import TestClient

from app.graph.workflow import llm
from main import app


client = TestClient(app)


def test_parking_availability_returns_nearest_vacant_spot():
    response = client.get("/parking/availability")

    assert response.status_code == 200
    payload = response.json()
    assert payload["is_demo_data"] is True
    assert payload["counts"]["available"] > 0
    assert payload["nearest_spot"]["id"] == "B1-A-018"
    assert payload["nearest_spot"]["status"] == "available"
    assert payload["location"]["source"] == "parking_entrance"
    assert payload["navigation"]["algorithm"] == "a_star"
    assert payload["navigation"]["selection"] == "minimum_route_distance"
    assert payload["navigation"]["distance_m"] > 0
    assert payload["navigation"]["steps"][-1]["instruction"].endswith(
        "B1 层 A 区 018 号"
    )


def test_chat_answers_nearest_spot_without_calling_llm(
    monkeypatch,
    auth_client,
):
    def fail_if_llm_is_called(_prompt):
        raise AssertionError("Parking availability lookup must not call the LLM")

    monkeypatch.setattr(llm, "invoke", fail_if_llm_is_called)

    response = auth_client.post(
        "/chat",
        json={
            "question": "离我最近的空车位在哪里",
            "session_id": "parking-chat-entrance",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["next_agent"] == "parking"
    assert payload["intent"] == "parking_availability"
    assert payload["requires_human"] is False
    assert payload["tool_results"]["parking_availability"]["ok"] is True
    assert payload["tool_results"]["route_plan"]["ok"] is True
    assert "最近的空车位" in payload["response"]
    assert "B1 层 A 区 018 号" in payload["response"]
    assert "按停车场入口计算" in payload["response"]
    assert "A* 推荐路线" in payload["response"]
    assert "导航步骤" in payload["response"]


def test_chat_uses_browser_location_when_it_is_inside_the_lot(
    auth_client,
):
    availability = client.get("/parking/availability").json()
    coordinates = availability["nearest_spot"]["coordinates"]

    response = auth_client.post(
        "/chat",
        json={
            "question": "离我最近的空车位在哪里",
            "session_id": "parking-chat-location",
            "location": coordinates,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    parking_data = payload["api_result"]["parking_availability"]
    assert parking_data["location"]["source"] == "user_location"
    assert parking_data["navigation"]["algorithm"] == "a_star"
    assert (
        parking_data["navigation"]["start"]["node_id"]
        == "user-start"
    )
    assert parking_data["location"]["navigation_start"]["level_assumed"] is True
    assert "起点按 B1 层估算" in payload["response"]


def test_route_endpoint_supports_cross_floor_navigation():
    response = client.get(
        "/parking/route",
        params={"spot_id": "B2-A-035"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["algorithm"] == "a_star"
    assert payload["destination"]["spot_id"] == "B2-A-035"
    assert payload["floor_changes"] == 1
    assert any("坡道下行至 B2" in step["instruction"] for step in payload["steps"])


def test_route_endpoint_rejects_unavailable_spot():
    response = client.get(
        "/parking/route",
        params={"spot_id": "B1-B-006"},
    )

    assert response.status_code == 404


def test_parking_map_endpoint_returns_floors_network_and_spots():
    response = client.get("/parking/map")

    assert response.status_code == 200
    payload = response.json()
    assert payload["is_demo_data"] is True
    assert payload["refresh_after_seconds"] >= 5
    assert [level["id"] for level in payload["levels"]] == [
        "B1",
        "B2",
        "B3",
    ]
    assert any(
        node["id"] == "b1-entry"
        for node in payload["levels"][0]["nodes"]
    )
    assert any(
        spot["id"] == "B2-A-035"
        for spot in payload["levels"][1]["spots"]
    )
    assert payload["floor_links"][0]["from"] == "B1"


def test_chat_navigates_to_explicit_spot_from_natural_language(
    monkeypatch,
    auth_client,
):
    def fail_if_llm_is_called(_prompt):
        raise AssertionError("Explicit parking navigation must stay deterministic")

    monkeypatch.setattr(llm, "invoke", fail_if_llm_is_called)
    response = auth_client.post(
        "/chat",
        json={
            "question": "帮我导航到 B2 层 A 区 035 号",
            "session_id": "parking-chat-explicit-map",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    navigation = payload["navigation"]
    assert payload["next_agent"] == "parking"
    assert navigation["destination"]["spot_id"] == "B2-A-035"
    assert navigation["floor_changes"] == 1
    assert navigation["path"][0]["node_id"] == "b1-entry"
    assert payload["api_result"]["parking_availability"][
        "requested_spot_id"
    ] == "B2-A-035"
    assert "导航目标已设为 B2 层 A 区 035 号" in payload["response"]
    assert payload["tool_results"]["navigation"]["live_refresh"] is True


def test_chat_reports_unavailable_explicit_spot_without_broken_route(
    auth_client,
):
    response = auth_client.post(
        "/chat",
        json={
            "question": "帮我导航到 B1 B006",
            "session_id": "parking-chat-unavailable-map",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["navigation"] is None
    assert payload["tool_results"]["route_plan"]["ok"] is False
    assert "无法为 B1-B-006 生成实时路线" in payload["response"]
    assert "当前最近空位" in payload["response"]
