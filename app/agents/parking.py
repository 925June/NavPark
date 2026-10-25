from app.agents.base import BaseAgent
from app.agents.base import record_agent_event
from app.parking import find_parking_spot_id
from app.tools.parking import get_parking_availability
from app.tools.parking import plan_parking_route


class ParkingAgent(BaseAgent):
    """Handle parking availability and deterministic A* guidance."""

    name = "ParkingAgent"
    responsibility = (
        "Use parking tools to select a vacant spot and produce route guidance."
    )

    def __init__(
        self,
        llm=None,
        availability_tool=None,
        route_tool=None,
    ):
        super().__init__(llm)
        self.availability_tool = (
            availability_tool or get_parking_availability
        )
        self.route_tool = route_tool or plan_parking_route

    def execute(self, state):
        location = state.get("location") or {}
        requested_spot_id = find_parking_spot_id(state["question"])
        availability_result = self.availability_tool.invoke({
            "latitude": location.get("latitude"),
            "longitude": location.get("longitude"),
        })
        if not availability_result["ok"]:
            raise RuntimeError(
                availability_result.get("error")
                or "停车位查询工具执行失败"
            )

        availability = availability_result["data"]
        state["parking_lot_id"] = availability["lot"]["id"]
        state["intent"] = "parking_availability"
        state["confidence"] = 1.0
        state["tool_results"]["parking_availability"] = {
            "ok": True,
            "source": availability_result["source"],
            "as_of": availability_result["as_of"],
            "available_count": availability["counts"]["available"],
        }

        nearest = availability.get("nearest_spot")
        target_spot_id = requested_spot_id or (nearest or {}).get("id")
        navigation = {}
        route_error = None
        if nearest:
            route_result = self.route_tool.invoke({
                "spot_id": target_spot_id,
                "latitude": location.get("latitude"),
                "longitude": location.get("longitude"),
            })
            if route_result["ok"]:
                navigation = route_result["data"]
                availability["navigation"] = navigation
                state["tool_results"]["route_plan"] = {
                    "ok": True,
                    "source": route_result["source"],
                    "as_of": route_result["as_of"],
                    "distance_m": navigation.get("distance_m"),
                    "spot_id": target_spot_id,
                }
            else:
                route_error = (
                    route_result.get("error")
                    or "停车路线工具执行失败"
                )
                availability["navigation"] = None
                state["tool_results"]["route_plan"] = {
                    "ok": False,
                    "source": route_result.get("source"),
                    "as_of": route_result.get("as_of"),
                    "error_code": route_result.get("error_code"),
                    "error": route_error,
                    "spot_id": target_spot_id,
                }
        else:
            availability["navigation"] = None

        availability["requested_spot_id"] = requested_spot_id
        state["api_result"] = {
            "parking_availability": availability,
        }
        state["tool_results"]["navigation"] = {
            "algorithm": navigation.get("algorithm"),
            "distance_m": navigation.get("distance_m"),
            "estimated_drive_seconds": navigation.get(
                "estimated_drive_seconds"
            ),
            "step_count": len(navigation.get("steps", [])),
            "spot_id": target_spot_id,
            "requested": bool(requested_spot_id),
            "live_refresh": bool(navigation),
        }

        if route_error:
            state["draft_response"] = self._format_route_error(
                availability,
                requested_spot_id,
                route_error,
            )
        else:
            state["draft_response"] = self._format_response(
                availability,
                requested_spot_id=requested_spot_id,
            )

        record_agent_event(
            state,
            self.name,
            (
                "生成实时室内导航地图与路线草稿"
                if navigation
                else "完成车位查询，未生成路线"
            ),
            metadata={
                "available_count": availability["counts"]["available"],
                "nearest_spot": (nearest or {}).get("id"),
                "requested_spot": requested_spot_id,
                "route_generated": bool(navigation),
                "tools": [
                    tool_name
                    for tool_name in (
                        self.availability_tool.name,
                        self.route_tool.name if target_spot_id else None,
                    )
                    if tool_name
                ],
            },
        )
        return state

    @staticmethod
    def _format_response(availability, requested_spot_id=None):
        nearest = availability["nearest_spot"]
        location = availability["location"]
        navigation = availability["navigation"]
        level_counts = availability["counts"]["by_level"]
        level_summary = "，".join(
            f"{level} {values['available']}/{values['total']} 个空位"
            for level, values in level_counts.items()
        )

        if not nearest:
            return (
                f"{availability['lot']['name']} 当前显示没有可用的标准车位。"
                f"场内共有 {availability['counts']['total']} 个车位，"
                "请稍后刷新，或前往服务台询问临时安排。"
            )

        destination = navigation["destination"]
        route_steps = "\n".join(
            f"{index}. {step['instruction']}"
            for index, step in enumerate(navigation["steps"], start=1)
        )
        heading = (
            f"导航目标已设为 {destination['label']}。"
            if requested_spot_id
            else f"推荐最近的空车位是 {nearest['label']}。"
        )
        return (
            f"{heading}"
            f"从{('你当前定位' if location['accepted'] else '停车场入口')}"
            f"出发，A* 推荐路线约 {navigation['distance_m']:.0f} 米，"
            f"预计驾车 {navigation['estimated_drive_seconds']} 秒。\n\n"
            f"导航步骤：\n{route_steps}\n\n"
            f"实时室内地图已生成，可切换 B1–B3 楼层查看高亮路线"
            f"（共 {navigation['floor_changes']} 次楼层变化）。\n\n"
            f"当前实时空位：{level_summary}，"
            f"共 {availability['counts']['available']} 个。\n"
            f"{location['message']}"
        )

    @staticmethod
    def _format_route_error(
        availability,
        requested_spot_id,
        route_error,
    ):
        nearest = availability.get("nearest_spot")
        target = requested_spot_id or "推荐车位"
        message = f"无法为 {target} 生成实时路线：{route_error}"
        if nearest:
            message += (
                f"\n\n当前最近空位是 {nearest['label']}。"
                f"你可以说“导航到 {nearest['id']}”重新规划。"
            )
        return message
