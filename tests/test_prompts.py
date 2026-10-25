from app.agents.judge import JudgeAgent
from app.agents.pricing import PricingAgent
from app.agents.reservation import ReservationAgent
from app.agents.response import HUMAN_REVIEW_NOTICE
from app.agents.response import ResponseAgent
from app.agents.supervisor import SupervisorAgent
from app.state import create_workflow_state
from app.tools.knowledge import create_knowledge_search_tool


class FakeResponse:
    def __init__(self, content):
        self.content = content


class FakeLLM:
    def __init__(self, content):
        self.content = content
        self.prompts = []

    def invoke(self, prompt):
        self.prompts.append(prompt)
        return FakeResponse(self.content)


class StubRetriever:
    def retrieve(self, _query, top_k=3):
        return ["标准车位每小时 10 元。"]


def test_supervisor_prompt_contains_history_and_safety_rules():
    llm = FakeLLM("pricing")
    agent = SupervisorAgent(llm)
    state = {
        "question": "那晚上怎么收费？",
        "history": [
            {"role": "user", "content": "B1 停车场在哪里？"},
            {"role": "assistant", "content": "B1 入口在星河路。"},
        ],
        "confidence": 1.0,
    }

    result = agent.execute(state)

    assert result["next_agent"] == "pricing"
    assert "B1 停车场在哪里？" in llm.prompts[0]
    assert "不可信数据" in llm.prompts[0]
    assert "parking" in llm.prompts[0]


def test_supervisor_falls_back_to_support_for_unknown_agent():
    llm = FakeLLM("judge")
    agent = SupervisorAgent(llm)
    state = {
        "question": "我该怎么办？",
        "history": [],
        "confidence": 1.0,
    }

    result = agent.execute(state)

    assert result["next_agent"] == "support"
    assert result["confidence"] == 0.5


def test_supervisor_does_not_call_llm_for_parking_lookup():
    class FailingLLM:
        def invoke(self, _prompt):
            raise AssertionError("LLM should not be called")

    state = {
        "question": "离我最近的空车位在哪里？",
        "history": [],
        "confidence": 1.0,
    }

    result = SupervisorAgent(FailingLLM()).execute(state)

    assert result["next_agent"] == "parking"


def test_pricing_agent_receives_rag_context_and_recent_history():
    llm = FakeLLM("根据资料，每小时 10 元。")
    agent = PricingAgent(
        llm,
        knowledge_tool=create_knowledge_search_tool(StubRetriever()),
    )
    state = create_workflow_state(
        question="刚才说的价格是全天还是每小时？",
        history=[
            {"role": "user", "content": "停车怎么收费？"},
            {"role": "assistant", "content": "标准车位每小时 10 元。"},
        ],
    )
    result = agent.execute(state)

    assert result["draft_response"] == "根据资料，每小时 10 元。"
    assert result["context_sources"] == ["doc-1"]
    assert result["tool_results"]["knowledge_search"]["ok"] is True
    assert "标准车位每小时 10 元" in llm.prompts[0]
    assert "刚才说的价格" in llm.prompts[0]
    assert "不得把估算值" in llm.prompts[0]
    assert result["agent_trace"][-1]["agent"] == "PricingAgent"


def test_reservation_agent_loads_evidence_through_tool():
    class StubRetriever:
        def retrieve(self, _query, top_k=3):
            return ["预约需提前 30 分钟。", "取消政策以现场为准。"][:top_k]

    agent = ReservationAgent(
        llm=FakeLLM("预约需提前 30 分钟。"),
        knowledge_tool=create_knowledge_search_tool(StubRetriever()),
    )
    state = create_workflow_state(
        question="预约需要提前多久？",
        session_id="retriever-test",
    )
    state["next_agent"] = "reservation"

    result = agent.execute(state)

    assert result["context_sources"] == ["doc-1", "doc-2"]
    assert result["retrieved_context"][0]["content"] == "预约需提前 30 分钟。"
    assert result["agent_trace"][-1]["agent"] == "ReservationAgent"


def test_judge_accepts_structured_verdict():
    llm = FakeLLM(
        '{"requires_human": true, "risk_level": "high", '
        '"reasons": ["退款结果没有真实业务记录"], '
        '"unsupported_claims": ["已退款"]}'
    )
    state = create_workflow_state(
        question="停车价格是多少？",
        session_id="judge-test",
    )
    state["draft_response"] = "根据资料，标准车位每小时 10 元。"
    state["intent"] = "pricing"
    state["next_agent"] = "pricing"

    result = JudgeAgent(llm).execute(state)

    assert result["requires_human"] is True
    assert result["audit_result"]["source"] == "model_and_policy"
    assert "JSON" in llm.prompts[0]
    assert result["human_review_reason"] == "退款结果没有真实业务记录"


def test_deterministic_risk_policy_blocks_unconfirmed_action():
    class FailingLLM:
        def invoke(self, _prompt):
            raise AssertionError("Risk policy should not call the LLM")

    state = create_workflow_state(
        question="我要退款。",
        session_id="risk-test",
    )
    state["draft_response"] = "退款已经完成。"
    state["intent"] = "support"
    state["next_agent"] = "support"

    result = JudgeAgent(FailingLLM()).execute(state)

    assert result["requires_human"] is True
    assert result["audit_result"]["source"] == "deterministic_risk_policy"
    assert result["human_review_reason"]


def test_invalid_judge_output_fails_closed():
    state = create_workflow_state(
        question="停车时间？",
        session_id="invalid-judge-test",
    )
    state["draft_response"] = "开放时间为 24 小时。"
    state["intent"] = "support"
    state["next_agent"] = "support"

    result = JudgeAgent(FakeLLM("YES, maybe")).execute(state)

    assert result["requires_human"] is True
    assert result["audit_result"]["source"] == "judge_fallback"


def test_judge_unsupported_claim_overrides_model_approval():
    llm = FakeLLM(
        '{"requires_human": false, "risk_level": "low", '
        '"reasons": [], "unsupported_claims": ["虚构的营业时间"]}'
    )
    state = create_workflow_state(
        question="停车时间？",
        session_id="unsupported-claim-test",
    )
    state["draft_response"] = "停车场每天开放 25 小时。"
    state["intent"] = "support"
    state["next_agent"] = "support"

    result = JudgeAgent(llm).execute(state)

    assert result["requires_human"] is True
    assert result["audit_result"]["risk_level"] == "medium"
    assert result["audit_result"]["unsupported_claims"] == [
        "虚构的营业时间",
    ]


def test_response_agent_adds_pending_review_without_claiming_approval():
    state = create_workflow_state(
        question="我要退款。",
        session_id="composer-test",
    )
    state["draft_response"] = "需要进一步核实。"
    state["requires_human"] = True

    result = ResponseAgent(FakeLLM("")).execute(state)

    assert "Approved by Human" not in result["response"]
    assert HUMAN_REVIEW_NOTICE in result["response"]
    assert result["human_review_status"] == "pending"
