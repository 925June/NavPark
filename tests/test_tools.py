from datetime import datetime
from datetime import timedelta
from datetime import timezone

from app.tools import calculate_parking_fee
from app.tools import get_parking_availability
from app.tools import get_tool_catalog
from app.tools import plan_parking_route
from app.tools import validate_reservation_request
from app.tools.knowledge import create_knowledge_search_tool


def test_availability_tool_returns_structured_success():
    result = get_parking_availability.invoke({})

    assert result["ok"] is True
    assert result["source"] == "parking_service"
    assert result["data"]["nearest_spot"]["id"] == "B1-A-018"
    assert result["as_of"]
    assert result["error"] is None


def test_parking_tool_rejects_partial_coordinates():
    result = get_parking_availability.invoke({
        "latitude": 31.23075,
        "longitude": None,
    })

    assert result["ok"] is False
    assert result["error_code"] == "parking_availability_failed"


def test_route_tool_supports_cross_floor_route():
    result = plan_parking_route.invoke({
        "spot_id": "B2-A-035",
    })

    assert result["ok"] is True
    assert result["data"]["destination"]["spot_id"] == "B2-A-035"
    assert result["data"]["floor_changes"] == 1
    assert result["metadata"]["algorithm"] == "a_star"


def test_route_tool_returns_failure_for_unavailable_spot():
    result = plan_parking_route.invoke({
        "spot_id": "B1-B-006",
    })

    assert result["ok"] is False
    assert result["error_code"] == "parking_route_unavailable"


def test_knowledge_tool_uses_injected_retriever():
    class StubRetriever:
        def retrieve(self, query, top_k=3):
            assert query == "停车价格"
            assert top_k == 2
            return ["标准车位每小时 10 元。"]

    tool = create_knowledge_search_tool(StubRetriever())
    result = tool.invoke({
        "query": "停车价格",
        "top_k": 2,
    })

    assert result["ok"] is True
    assert result["source"] == "parking_knowledge_base"
    assert result["data"]["documents"][0]["content"] == (
        "标准车位每小时 10 元。"
    )


def test_fee_tool_applies_minimum_and_daily_cap():
    minimum = calculate_parking_fee.invoke({
        "hourly_rate": 10,
        "duration_minutes": 30,
        "minimum_charge": 8,
    })
    capped = calculate_parking_fee.invoke({
        "hourly_rate": 10,
        "duration_minutes": 1200,
        "daily_cap": 60,
    })

    assert minimum["data"]["estimated_total"] == 8.0
    assert minimum["data"]["minimum_charge_applied"] is True
    assert capped["data"]["estimated_total"] == 60.0
    assert capped["data"]["daily_cap_applied"] is True


def test_reservation_validator_never_claims_reservation_created():
    start = datetime(2026, 10, 26, 9, 0, tzinfo=timezone.utc)
    result = validate_reservation_request.invoke({
        "parking_lot_id": "navpark-xinghe-001",
        "start_time": start.isoformat(),
        "end_time": (start + timedelta(hours=2)).isoformat(),
        "vehicle_plate": "沪A12345",
    })

    assert result["ok"] is True
    assert result["data"]["is_valid"] is True
    assert result["data"]["reservation_created"] is False


def test_reservation_validator_rejects_reversed_time_range():
    start = datetime(2026, 10, 26, 9, 0, tzinfo=timezone.utc)
    result = validate_reservation_request.invoke({
        "parking_lot_id": "navpark-xinghe-001",
        "start_time": start.isoformat(),
        "end_time": (start - timedelta(hours=1)).isoformat(),
    })

    assert result["ok"] is False
    assert result["error_code"] == "reservation_validation_failed"


def test_tool_catalog_declares_least_privilege_owners():
    catalog = get_tool_catalog()
    by_id = {item["id"]: item for item in catalog}

    assert set(by_id) == {
        "get_parking_availability",
        "plan_parking_route",
        "search_parking_knowledge",
        "calculate_parking_fee",
        "validate_reservation_request",
    }
    assert by_id["get_parking_availability"]["allowed_agents"] == [
        "ParkingAgent",
    ]
    assert by_id["calculate_parking_fee"]["wired"] is False
    assert by_id["validate_reservation_request"]["wired"] is False
