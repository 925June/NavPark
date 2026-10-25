from datetime import datetime
from datetime import timezone
from typing import Any
from typing import Dict
from typing import Optional


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def tool_success(
    data: Any,
    source: str,
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Create a consistent, serializable tool success envelope."""
    return {
        "ok": True,
        "data": data,
        "source": source,
        "as_of": _now_iso(),
        "error": None,
        "error_code": None,
        "metadata": metadata or {},
    }


def tool_failure(
    error: str,
    source: str,
    error_code: str = "tool_error",
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Create a consistent failure envelope without raising across the graph."""
    return {
        "ok": False,
        "data": None,
        "source": source,
        "as_of": _now_iso(),
        "error": error,
        "error_code": error_code,
        "metadata": metadata or {},
    }
