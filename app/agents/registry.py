from dataclasses import asdict
from dataclasses import dataclass
from typing import Dict
from typing import List


@dataclass(frozen=True)
class AgentSpec:
    id: str
    implementation: str
    stage: str
    responsibility: str
    outputs: List[str]

    def to_dict(self) -> Dict:
        return asdict(self)


AGENT_CATALOG = (
    AgentSpec(
        id="supervisor",
        implementation="SupervisorAgent",
        stage="orchestration",
        responsibility="识别请求意图并选择停车、预约、价格或售后分支。",
        outputs=["next_agent", "intent", "workflow_plan"],
    ),
    AgentSpec(
        id="parking",
        implementation="ParkingAgent",
        stage="business_specialist",
        responsibility=(
            "调用车位和路线 Tool，生成确定性的空位与导航答复。"
        ),
        outputs=["api_result", "tool_results", "draft_response"],
    ),
    AgentSpec(
        id="reservation",
        implementation="ReservationAgent",
        stage="business_specialist",
        responsibility=(
            "检索预约资料并解释预约、修改和取消规则。"
        ),
        outputs=["retrieved_context", "draft_response"],
    ),
    AgentSpec(
        id="pricing",
        implementation="PricingAgent",
        stage="business_specialist",
        responsibility=(
            "检索价格资料并解释价格与计费规则。"
        ),
        outputs=["retrieved_context", "draft_response"],
    ),
    AgentSpec(
        id="support",
        implementation="SupportAgent",
        stage="business_specialist",
        responsibility=(
            "检索服务资料并处理设施、营业时间和一般售后问题。"
        ),
        outputs=["retrieved_context", "draft_response"],
    ),
    AgentSpec(
        id="judge",
        implementation="JudgeAgent",
        stage="audit",
        responsibility=(
            "结合确定性风险策略和结构化模型审核，标记待人工核实。"
        ),
        outputs=["audit_result", "requires_human"],
    ),
    AgentSpec(
        id="response",
        implementation="ResponseAgent",
        stage="response_and_policy",
        responsibility=(
            "合成最终答复、追加人工提示、执行 Guardrail 并保存。"
        ),
        outputs=["response", "human_review_status", "guardrail_failures"],
    ),
)


def get_agent_catalog() -> List[Dict]:
    return [spec.to_dict() for spec in AGENT_CATALOG]
