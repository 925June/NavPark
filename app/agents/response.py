from app.agents.base import BaseAgent
from app.agents.base import record_agent_event
from app.memory import memory_store
from app.guardrails import (
    GuardrailManager,
    EmptyResponseGuardrail,
    MinLengthGuardrail,
    MaxLengthGuardrail,
    ProfanityGuardrail,
    PIIGuardrail,
    ParkingDomainGuardrail
)
from app.metrics import metrics_collector, MetricEvent
import time

HUMAN_REVIEW_NOTICE = (
    "该问题需要人工进一步核实。"
    "当前系统尚未完成真实人工审核，请联系现场服务台。"
)


class ResponseAgent(BaseAgent):
    name = "ResponseAgent"
    responsibility = (
        "Compose the final answer, apply guardrails, and persist the turn."
    )

    def __init__(self, llm):
        super().__init__(llm)
        self.guardrail_manager = GuardrailManager()
        self._setup_guardrails()

    def _setup_guardrails(self):
        """Configure guardrails for response validation."""
        self.guardrail_manager.add_guardrail(EmptyResponseGuardrail())
        self.guardrail_manager.add_guardrail(MinLengthGuardrail(min_length=10))
        self.guardrail_manager.add_guardrail(MaxLengthGuardrail(max_length=1000))
        self.guardrail_manager.add_guardrail(ProfanityGuardrail())
        self.guardrail_manager.add_guardrail(PIIGuardrail())
        self.guardrail_manager.add_guardrail(ParkingDomainGuardrail())

    def execute(self, state):
        start_time = time.time()
        response = (
            state.get("draft_response")
            or state.get("response")
            or "暂时无法生成完整答复，请稍后重试或联系现场服务台。"
        ).strip()

        if state.get("requires_human"):
            state["human_review_status"] = "pending"
            if HUMAN_REVIEW_NOTICE not in response:
                response = f"{response}\n\n{HUMAN_REVIEW_NOTICE}"
        else:
            state["human_review_status"] = None
        state["response"] = response

        # Validate response through guardrails
        all_passed, failure_reasons = self.guardrail_manager.validate_all(
            response,
            {"question": state["question"]}
        )

        # Record guardrail check
        metrics_collector.record_event(
            MetricEvent(
                timestamp=time.time(),
                event_type="guardrail_check",
                session_id=state.get("session_id"),
                success=all_passed,
                metadata={"failures": failure_reasons}
            )
        )

        if not all_passed:
            # Log guardrail failures
            state["guardrail_failures"] = failure_reasons
            for reason in failure_reasons:
                metrics_collector.record_guardrail_failure(reason)
            # Provide fallback response
            response = (
                "抱歉，这次答复未通过内容安全检查。"
                "请换一种方式描述需求，或联系现场服务台进一步处理。"
            )
            state["response"] = response
        else:
            state["guardrail_failures"] = []

        record_agent_event(
            state,
            self.name,
            (
                "完成答复合成、Guardrail 检查并保存"
                if all_passed
                else "答复触发 Guardrail，已使用安全兜底并保存"
            ),
            metadata={
                "failure_count": len(failure_reasons),
            },
        )

        for trace_event in state.get("agent_trace", []):
            metrics_collector.record_event(
                MetricEvent(
                    timestamp=time.time(),
                    event_type="agent_step",
                    agent=trace_event.get("agent"),
                    session_id=state.get("session_id"),
                    success=trace_event.get("status") == "completed",
                    metadata=trace_event.get("metadata", {}),
                )
            )

        memory_store.append_turn(
            state["session_id"],
            state["question"],
            response,
            user_id=state.get("user_id"),
        )

        state["history"] = memory_store.get_history(
            state["session_id"],
            user_id=state.get("user_id"),
        )

        # Record response completion
        duration = time.time() - start_time
        metrics_collector.record_event(
            MetricEvent(
                timestamp=time.time(),
                event_type="response_complete",
                session_id=state.get("session_id"),
                duration=duration,
                success=True
            )
        )

        return state
