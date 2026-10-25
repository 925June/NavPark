from dataclasses import asdict
from dataclasses import dataclass
from typing import Dict
from typing import List


@dataclass(frozen=True)
class ToolSpec:
    id: str
    implementation: str
    access: str
    allowed_agents: List[str]
    wired: bool
    purpose: str

    def to_dict(self) -> Dict:
        return asdict(self)


TOOL_CATALOG = (
    ToolSpec(
        id="get_parking_availability",
        implementation="app.tools.parking.get_parking_availability",
        access="read",
        allowed_agents=["ParkingAgent"],
        wired=True,
        purpose="读取演示停车场车位快照、数量与推荐车位。",
    ),
    ToolSpec(
        id="plan_parking_route",
        implementation="app.tools.parking.plan_parking_route",
        access="read",
        allowed_agents=["ParkingAgent"],
        wired=True,
        purpose="通过 A* 计算到推荐或指定空车位的路线。",
    ),
    ToolSpec(
        id="search_parking_knowledge",
        implementation="app.tools.knowledge.search_parking_knowledge",
        access="read",
        allowed_agents=[
            "ReservationAgent",
            "PricingAgent",
            "SupportAgent",
        ],
        wired=True,
        purpose="检索预约、价格和售后正式资料，形成共享证据。",
    ),
    ToolSpec(
        id="calculate_parking_fee",
        implementation="app.tools.billing.calculate_parking_fee",
        access="compute",
        allowed_agents=["PricingAgent"],
        wired=False,
        purpose="仅根据调用方明确提供的费率计算停车费用估算。",
    ),
    ToolSpec(
        id="validate_reservation_request",
        implementation="app.tools.reservation.validate_reservation_request",
        access="validate",
        allowed_agents=["ReservationAgent"],
        wired=False,
        purpose="校验预约时间、停车场和车牌参数，不创建预约。",
    ),
)


def get_tool_catalog() -> List[Dict]:
    return [spec.to_dict() for spec in TOOL_CATALOG]
