import re
from datetime import datetime
from typing import Optional

from langchain_core.tools import tool
from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field

from app.tools.base import tool_failure
from app.tools.base import tool_success


class ReservationValidationInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    parking_lot_id: str = Field(min_length=1, max_length=80)
    start_time: datetime
    end_time: datetime
    vehicle_plate: Optional[str] = Field(
        default=None,
        min_length=1,
        max_length=20,
    )


@tool(
    "validate_reservation_request",
    args_schema=ReservationValidationInput,
)
def validate_reservation_request(
    parking_lot_id: str,
    start_time: datetime,
    end_time: datetime,
    vehicle_plate: Optional[str] = None,
) -> dict:
    """Validate reservation parameters without creating a reservation."""
    try:
        if start_time.tzinfo is None or end_time.tzinfo is None:
            raise ValueError("预约起止时间必须包含时区")
        if end_time <= start_time:
            raise ValueError("预约结束时间必须晚于开始时间")
        if (end_time - start_time).total_seconds() > 30 * 86400:
            raise ValueError("单次预约不能超过 30 天")

        plate = None
        if vehicle_plate:
            plate = re.sub(r"\s+", "", vehicle_plate).upper()
            if not re.fullmatch(r"[\u4e00-\u9fffA-Z0-9]{5,12}", plate):
                raise ValueError("车牌格式包含不支持的字符")

        return tool_success(
            {
                "parking_lot_id": parking_lot_id.strip(),
                "start_time": start_time.isoformat(),
                "end_time": end_time.isoformat(),
                "vehicle_plate": plate,
                "duration_minutes": int(
                    (end_time - start_time).total_seconds() // 60
                ),
                "is_valid": True,
                "reservation_created": False,
            },
            source="reservation_validator",
        )
    except (TypeError, ValueError) as exc:
        return tool_failure(
            str(exc),
            source="reservation_validator",
            error_code="reservation_validation_failed",
        )
