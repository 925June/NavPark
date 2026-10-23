from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional

from app.graph.workflow import graph
from app.memory import memory_store
from app.metrics import metrics_collector, MetricEvent
import time

router = APIRouter()


class ChatRequest(BaseModel):

    question: str
    session_id: Optional[str] = None


@router.post("/chat")
def chat(request: ChatRequest):
    start_time = time.time()
    
    session_id = request.session_id or memory_store.create_session_id()

    state = {

        "question": request.question,

        "session_id": session_id,

        "history": memory_store.get_history(session_id),

        "next_agent": None,

        "customer_id": None,

        "parking_lot_id": None,

        "reservation_id": None,

        "vehicle_plate": None,

        "intent": None,

        "confidence": 1,

        "api_result": {},

        "requires_human": False,

        "response": None

    }

    # Record request start
    metrics_collector.record_event(
        MetricEvent(
            timestamp=time.time(),
            event_type="request",
            session_id=session_id,
            success=True,
            metadata={"question": request.question}
        )
    )

    result = graph.invoke(state)
    
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

    return result


@router.get("/metrics")
def get_metrics():
    """Get current metrics summary."""
    return metrics_collector.get_summary()


@router.post("/metrics/reset")
def reset_metrics():
    """Reset all metrics."""
    metrics_collector.reset()
    return {"message": "Metrics reset successfully"}
