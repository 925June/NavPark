from app.agents.base import BaseAgent
from app.agents.base import record_agent_event
from app.parking import find_parking_spot_id
from app.prompts import build_supervisor_prompt


class SupervisorAgent(BaseAgent):
    name = "SupervisorAgent"
    responsibility = "Route each request to one specialist branch."

    def execute(self, state):
        question = state["question"].strip().lower()
        if self._is_parking_availability_question(question):
            is_navigation = self._is_parking_navigation_question(question)
            self._set_route(
                state,
                agent="parking",
                intent="parking_availability",
                reason=(
                    "命中确定性停车导航规则"
                    if is_navigation
                    else "命中确定性实时车位查询规则"
                ),
                plan=[
                    "解析目标车位",
                    "查询停车位快照",
                    "验证 A* 导航路线",
                    "审核事实与风险",
                    "生成最终答复",
                ],
            )
            return state

        prompt = build_supervisor_prompt(
            state["question"],
            state.get("history", []),
        )
        response = self.llm.invoke(prompt)

        candidate = (
            response.content.strip().lower().split()[0]
            .strip(".,:;!?`'\"")
            if response.content.strip()
            else ""
        )
        if candidate not in {
            "parking",
            "reservation",
            "pricing",
            "support",
        }:
            candidate = "support"
            state["confidence"] = min(
                state.get("confidence", 1.0),
                0.5,
            )

        labels = {
            "parking": ("parking_availability", "实时车位查询"),
            "reservation": ("reservation", "预约规则咨询"),
            "pricing": ("pricing", "价格与计费咨询"),
            "support": ("support", "服务、售后或无法明确分类的问题"),
        }
        intent, label = labels[candidate]
        self._set_route(
            state,
            agent=candidate,
            intent=intent,
            reason=f"主管模型将问题识别为{label}",
            plan=self._plan_for(candidate),
        )

        return state

    @staticmethod
    def _set_route(state, agent, intent, reason, plan):
        state["next_agent"] = agent
        state["intent"] = intent
        state["route_reason"] = reason
        state["workflow_plan"] = plan
        record_agent_event(
            state,
            "SupervisorAgent",
            f"已路由到 {agent}",
            metadata={"next_agent": agent, "intent": intent},
        )

    @staticmethod
    def _plan_for(agent):
        if agent == "parking":
            return [
                "查询停车位快照",
                "验证 A* 导航路线",
                "审核事实与风险",
                "生成最终答复",
            ]
        if agent == "reservation":
            return [
                "检索预约知识",
                "生成预约规则草稿",
                "审核事实与风险",
                "生成最终答复",
            ]
        if agent == "pricing":
            return [
                "检索价格知识",
                "生成计费说明草稿",
                "审核事实与风险",
                "生成最终答复",
            ]
        return [
            "检索服务知识",
            "生成服务支持草稿",
            "审核事实与风险",
            "生成最终答复",
        ]

    @staticmethod
    def _is_parking_availability_question(question: str) -> bool:
        direct_phrases = (
            "空车位",
            "空闲车位",
            "有空位",
            "哪有车位",
            "车位在哪",
            "最近的车位",
            "附近车位",
            "available spot",
            "available parking",
            "free spot",
            "nearest parking",
            "nearest spot",
        )
        if any(phrase in question for phrase in direct_phrases):
            return True

        asks_for_location = any(
            term in question
            for term in ("最近", "附近", "哪里", "哪儿", "nearest", "where")
        )
        is_parking = any(
            term in question
            for term in ("车位", "空位", "停车", "parking", "spot")
        )
        if asks_for_location and is_parking:
            return True

        return SupervisorAgent._is_parking_navigation_question(question)

    @staticmethod
    def _is_parking_navigation_question(question: str) -> bool:
        navigation_terms = (
            "导航",
            "带我去",
            "怎么去",
            "怎么走",
            "路线",
            "场内引导",
            "navigate",
            "directions",
            "route to",
        )
        parking_terms = (
            "车位",
            "空位",
            "停车",
            "车库",
            "parking",
            "spot",
        )
        spot_reference = find_parking_spot_id(question)
        asks_for_navigation = any(
            term in question for term in navigation_terms
        )
        mentions_parking = any(term in question for term in parking_terms)
        return asks_for_navigation and bool(
            mentions_parking or spot_reference
        )
