from fastapi.testclient import TestClient

from app.agents.registry import get_agent_catalog
from app.graph.workflow import graph
from app.guardrails import PIIGuardrail
from app.state import create_workflow_state
from main import app


client = TestClient(app)


def test_parking_graph_runs_explicit_specialized_nodes():
    state = create_workflow_state(
        question="离我最近的空车位在哪里？",
        session_id="workflow-parking-test",
    )

    result = graph.invoke(state)

    assert result["next_agent"] == "parking"
    assert result["requires_human"] is False
    assert result["audit_result"]["source"] == "deterministic_parking_facts"
    assert result["draft_response"] == result["response"]
    assert result["tool_results"]["parking_availability"]["ok"] is True
    assert result["tool_results"]["route_plan"]["ok"] is True

    parking_trace = result["agent_trace"][1]
    assert parking_trace["metadata"]["tools"] == [
        "get_parking_availability",
        "plan_parking_route",
    ]

    assert [item["agent"] for item in result["agent_trace"]] == [
        "SupervisorAgent",
        "ParkingAgent",
        "JudgeAgent",
        "ResponseAgent",
    ]


def test_agent_catalog_has_unique_single_responsibility_nodes():
    catalog = get_agent_catalog()

    assert len(catalog) == 7
    assert len({item["id"] for item in catalog}) == len(catalog)
    assert all(item["responsibility"] for item in catalog)
    assert {
        "supervisor",
        "parking",
        "reservation",
        "pricing",
        "support",
        "judge",
        "response",
    }.issubset({item["id"] for item in catalog})


def test_agent_catalog_endpoint_describes_workflow():
    response = client.get("/agents")

    assert response.status_code == 200
    payload = response.json()
    assert payload["workflow_engine"] == "langgraph"
    assert payload["version"] == "2.1"
    assert len(payload["agents"]) == 7


def test_tool_registry_endpoint_describes_least_privilege():
    response = client.get("/tools")

    assert response.status_code == 200
    payload = response.json()
    assert len(payload["tools"]) == 5
    assert payload["bindings"]["JudgeAgent"] == []
    assert payload["bindings"]["ParkingAgent"] == [
        "get_parking_availability",
        "plan_parking_route",
    ]
    assert "write tools are not enabled" in payload["execution_policy"]


def test_runtime_config_reports_multi_agent_workflow():
    response = client.get("/config")

    assert response.status_code == 200
    payload = response.json()
    assert payload["workflow_engine"] == "langgraph"
    assert payload["workflow_version"] == "2.1"
    assert payload["agent_count"] == 7
    assert payload["tool_count"] == 5


def test_pii_guardrail_blocks_chinese_phone_number():
    passed, reason = PIIGuardrail().validate(
        "请联系 13800138000，停车场会为您安排。",
    )

    assert passed is False
    assert "Chinese phone number" in reason
