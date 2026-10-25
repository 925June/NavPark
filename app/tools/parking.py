from typing import Optional

from langchain_core.tools import tool
from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field

from app.parking import parking_service
from app.tools.base import tool_failure
from app.tools.base import tool_success


class ParkingAvailabilityInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    latitude: Optional[float] = Field(default=None, ge=-90, le=90)
    longitude: Optional[float] = Field(default=None, ge=-180, le=180)


class ParkingRouteInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    spot_id: Optional[str] = Field(default=None, min_length=1, max_length=32)
    latitude: Optional[float] = Field(default=None, ge=-90, le=90)
    longitude: Optional[float] = Field(default=None, ge=-180, le=180)


def _validate_coordinate_pair(latitude, longitude):
    if (latitude is None) != (longitude is None):
        raise ValueError("latitude 和 longitude 必须同时提供")


@tool(
    "get_parking_availability",
    args_schema=ParkingAvailabilityInput,
)
def get_parking_availability(
    latitude: Optional[float] = None,
    longitude: Optional[float] = None,
) -> dict:
    """Read the current parking snapshot and nearest available spot."""
    try:
        _validate_coordinate_pair(latitude, longitude)
        data = parking_service.get_availability(latitude, longitude)
        return tool_success(
            data,
            source="parking_service",
            metadata={
                "is_demo_data": data.get("is_demo_data", False),
                "available_count": data.get("counts", {}).get("available"),
            },
        )
    except Exception as exc:
        return tool_failure(
            str(exc),
            source="parking_service",
            error_code="parking_availability_failed",
        )


@tool(
    "plan_parking_route",
    args_schema=ParkingRouteInput,
)
def plan_parking_route(
    spot_id: Optional[str] = None,
    latitude: Optional[float] = None,
    longitude: Optional[float] = None,
) -> dict:
    """Plan an A* route to the best or explicitly selected vacant spot."""
    try:
        _validate_coordinate_pair(latitude, longitude)
        data = parking_service.get_route(
            spot_id=spot_id,
            latitude=latitude,
            longitude=longitude,
        )
        return tool_success(
            data,
            source="parking_navigation_service",
            metadata={
                "algorithm": data.get("algorithm"),
                "distance_m": data.get("distance_m"),
            },
        )
    except ValueError as exc:
        return tool_failure(
            str(exc),
            source="parking_navigation_service",
            error_code="parking_route_unavailable",
        )
    except Exception as exc:
        return tool_failure(
            str(exc),
            source="parking_navigation_service",
            error_code="parking_route_failed",
        )
