from app.agents.base import BaseAgent
from app.memory import memory_store
from app.guardrails import (
    GuardrailManager,
    EmptyResponseGuardrail,
    MinLengthGuardrail,
    MaxLengthGuardrail,
    ProfanityGuardrail,
    ParkingDomainGuardrail
)
from app.metrics import metrics_collector, MetricEvent
import time


class ResponseAgent(BaseAgent):

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
        self.guardrail_manager.add_guardrail(ParkingDomainGuardrail())

    def execute(self, state):
        start_time = time.time()
        response = state.get("response", "")

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
            response = "I apologize, but I couldn't provide a complete answer. Please contact our support team for assistance with this specific inquiry."
            state["response"] = response
        else:
            state["guardrail_failures"] = []

        memory_store.append_turn(
            state["session_id"],
            state["question"],
            response
        )

        state["history"] = memory_store.get_history(
            state["session_id"]
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
