from typing import Optional

from langchain_core.tools import tool
from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field

from app.tools.base import tool_failure
from app.tools.base import tool_success


class ParkingFeeInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    hourly_rate: float = Field(ge=0, le=10000)
    duration_minutes: int = Field(gt=0, le=44640)
    minimum_charge: float = Field(default=0, ge=0, le=100000)
    daily_cap: Optional[float] = Field(
        default=None,
        ge=0,
        le=100000,
    )


@tool(
    "calculate_parking_fee",
    args_schema=ParkingFeeInput,
)
def calculate_parking_fee(
    hourly_rate: float,
    duration_minutes: int,
    minimum_charge: float = 0,
    daily_cap: Optional[float] = None,
) -> dict:
    """Calculate an estimate from explicitly supplied pricing inputs."""
    try:
        unbounded = hourly_rate * duration_minutes / 60
        before_cap = max(unbounded, minimum_charge)
        total = (
            min(before_cap, daily_cap)
            if daily_cap is not None
            else before_cap
        )
        return tool_success(
            {
                "estimated_total": round(total, 2),
                "unbounded_total": round(unbounded, 2),
                "minimum_charge_applied": before_cap > unbounded,
                "daily_cap_applied": (
                    daily_cap is not None and before_cap > daily_cap
                ),
                "currency": "CNY",
                "is_estimate": True,
            },
            source="deterministic_fee_calculator",
            metadata={
                "hourly_rate": hourly_rate,
                "duration_minutes": duration_minutes,
            },
        )
    except Exception as exc:
        return tool_failure(
            str(exc),
            source="deterministic_fee_calculator",
            error_code="fee_calculation_failed",
        )
