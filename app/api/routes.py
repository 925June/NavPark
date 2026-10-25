from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field
from typing import Optional

from app.auth.dependencies import get_current_user
from app.auth.dependencies import require_same_origin
from app.agents import get_agent_catalog
from app.tools import get_tool_catalog
from app.tools import get_tool_bindings
from app.graph.workflow import graph
from app.memory import memory_store
from app.metrics import metrics_collector, MetricEvent
from app.config import settings
from app.parking import parking_service
from app.llm.deepseek_provider import DeepSeekConfigurationError
from app.state import create_workflow_state
import time

router = APIRouter()


class GeoPoint(BaseModel):

    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)


class ChatRequest(BaseModel):

    question: str = Field(min_length=1, max_length=2000)
    session_id: Optional[str] = None
    location: Optional[GeoPoint] = None


@router.post("/chat")
def chat(
    request: ChatRequest,
    http_request: Request,
    user=Depends(get_current_user),
    _same_origin=Depends(require_same_origin),
):
    start_time = time.time()
    
    session_id = memory_store.resolve_session(
        user["id"],
        request.session_id,
    )

    state = create_workflow_state(
        question=request.question,
        user_id=user["id"],
        session_id=session_id,
        history=memory_store.get_history(
            session_id,
            user_id=user["id"],
        ),
        location=(
            request.location.model_dump()
            if request.location
            else None
        ),
    )

    # Record request start
    metrics_collector.record_event(
        MetricEvent(
            timestamp=time.time(),
            event_type="request",
            session_id=session_id,
            success=True,
            metadata={"question_length": len(request.question)}
        )
    )

    try:
        result = graph.invoke(state)
    except DeepSeekConfigurationError as exc:
        duration = time.time() - start_time
        metrics_collector.record_event(
            MetricEvent(
                timestamp=time.time(),
                event_type="request_complete",
                session_id=session_id,
                duration=duration,
                success=False,
                metadata={"error": "deepseek_not_configured"}
            )
        )
        raise HTTPException(
            status_code=503,
            detail="问题已收到，但 DeepSeek 尚未配置。请设置 DEEPSEEK_API_KEY 后重启服务。"
        ) from exc
    except Exception as exc:
        duration = time.time() - start_time
        metrics_collector.record_event(
            MetricEvent(
                timestamp=time.time(),
                event_type="request_complete",
                session_id=session_id,
                duration=duration,
                success=False,
                metadata={"error": "deepseek_request_failed"}
            )
        )
        raise HTTPException(
            status_code=502,
            detail="DeepSeek 服务暂时不可用，请检查 API 配置或稍后重试。"
        ) from exc
    
    # Record request completion
    duration = time.time() - start_time
    metrics_collector.record_event(
        MetricEvent(
            timestamp=time.time(),
            event_type="request_complete",
            session_id=session_id,
            duration=duration,
            success=True,
            metadata={
                "agent": result.get("next_agent"),
                "requires_human": result.get("requires_human")
            }
        )
    )

    return {
        "session_id": result["session_id"],
        "response": result["response"],
        "navigation": result.get("api_result", {})
        .get("parking_availability", {})
        .get("navigation"),
        "next_agent": result.get("next_agent"),
        "intent": result.get("intent"),
        "confidence": result.get("confidence"),
        "requires_human": result.get("requires_human", False),
        "human_review_status": result.get("human_review_status"),
        "audit_result": result.get("audit_result", {}),
        "api_result": result.get("api_result", {}),
        "tool_results": result.get("tool_results", {}),
        "workflow": {
            "plan": result.get("workflow_plan", []),
            "trace": result.get("agent_trace", []),
        },
    }


@router.get("/parking/availability")
def get_parking_availability(
    latitude: Optional[float] = Query(default=None, ge=-90, le=90),
    longitude: Optional[float] = Query(default=None, ge=-180, le=180),
):
    """Return the current snapshot and its A* recommended route."""
    if (latitude is None) != (longitude is None):
        raise HTTPException(
            status_code=400,
            detail="latitude 和 longitude 需要同时提供。",
        )
    return parking_service.get_availability(latitude, longitude)


@router.get("/parking/route")
def get_parking_route(
    spot_id: Optional[str] = Query(default=None),
    latitude: Optional[float] = Query(default=None, ge=-90, le=90),
    longitude: Optional[float] = Query(default=None, ge=-180, le=180),
):
    """Build an A* route to the best or explicitly selected vacant spot."""
    if (latitude is None) != (longitude is None):
        raise HTTPException(
            status_code=400,
            detail="latitude 和 longitude 需要同时提供。",
        )
    try:
        return parking_service.get_route(
            spot_id=spot_id,
            latitude=latitude,
            longitude=longitude,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/parking/map")
def get_parking_map():
    """Return the current indoor map, floor network, and spot snapshot."""
    return parking_service.get_lot_map()


@router.get("/metrics")
def get_metrics():
    """Get current metrics summary."""
    return metrics_collector.get_summary()


@router.post("/metrics/reset")
def reset_metrics():
    """Reset all metrics."""
    metrics_collector.reset()
    return {"message": "Metrics reset successfully"}


@router.get("/config")
def get_runtime_config():
    """Expose non-secret LLM and voice-input configuration."""
    return {
        "llm_provider": settings.LLM_PROVIDER,
        "model": settings.DEEPSEEK_MODEL,
        "configured": bool(settings.DEEPSEEK_API_KEY),
        "voice_input": "browser_web_speech",
        "parking_availability": "in_memory_demo",
        "parking_navigation": "a_star",
        "parking_map": "live_indoor_svg",
        "workflow_engine": "langgraph",
        "workflow_version": "2.1",
        "agent_count": len(get_agent_catalog()),
        "tool_count": len(get_tool_catalog()),
    }


@router.get("/agents")
def get_agent_workflow():
    """Describe the responsibilities and outputs of every workflow agent."""
    return {
        "workflow_engine": "langgraph",
        "version": "2.1",
        "agents": get_agent_catalog(),
    }


@router.get("/tools")
def get_tool_registry():
    """Describe registered tools and their least-privilege owners."""
    return {
        "tools": get_tool_catalog(),
        "bindings": get_tool_bindings(),
        "execution_policy": (
            "Agents call only their declared tools; "
            "write tools are not enabled in this demo."
        ),
    }
