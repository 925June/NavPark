import json
import re

from app.agents.base import BaseAgent
from app.agents.base import record_agent_event
from app.policies import assess_request_risk
from app.prompts import build_judge_prompt


class JudgeAgent(BaseAgent):
    name = "JudgeAgent"
    responsibility = "Combine risk policy and model review into an audit result."

    def execute(self, state):
        if state.get("intent") == "parking_availability":
            self._set_audit(
                state,
                requires_human=False,
                risk_level="low",
                reasons=[],
                source="deterministic_parking_facts",
            )
            record_agent_event(
                state,
                self.name,
                "结构化车位与路线事实通过审核",
            )
            return state

        draft = state.get("draft_response") or state.get("response") or ""
        deterministic = assess_request_risk(
            state["question"],
            draft,
        )
        if deterministic.requires_human:
            self._set_audit(
                state,
                requires_human=True,
                risk_level=deterministic.risk_level,
                reasons=deterministic.reasons,
                source="deterministic_risk_policy",
            )
            record_agent_event(
                state,
                self.name,
                "确定性风险策略要求人工复核",
                metadata={"reason_count": len(deterministic.reasons)},
            )
            return state

        prompt = build_judge_prompt(
            state["question"],
            draft,
            {
                "agent": state.get("next_agent"),
                "intent": state.get("intent"),
                "api_result": state.get("api_result", {}),
                "tool_results": state.get("tool_results", {}),
            },
            state.get("retrieved_context", []),
        )

        result = self.llm.invoke(prompt)
        try:
            verdict = self._parse_verdict(result.content)
        except (ValueError, TypeError, json.JSONDecodeError):
            self._set_audit(
                state,
                requires_human=True,
                risk_level="medium",
                reasons=["审核模型未返回可解析的结构化结果"],
                source="judge_fallback",
            )
            record_agent_event(
                state,
                self.name,
                "审核输出不可解析，按保守策略转入人工",
            )
            return state

        model_requires_human = verdict["requires_human"]
        model_reasons = verdict["reasons"]
        self._set_audit(
            state,
            requires_human=model_requires_human,
            risk_level=verdict["risk_level"],
            reasons=model_reasons,
            source="model_and_policy",
            unsupported_claims=verdict["unsupported_claims"],
        )
        record_agent_event(
            state,
            self.name,
            (
                "审核要求人工复核"
                if model_requires_human
                else "审核通过"
            ),
            metadata={
                "risk_level": verdict["risk_level"],
                "reason_count": len(model_reasons),
            },
        )

        return state

    @staticmethod
    def _parse_verdict(content):
        text = (content or "").strip()
        start = text.find("{")
        end = text.rfind("}")
        if start < 0 or end < start:
            raise ValueError("Judge response does not contain JSON")

        payload = json.loads(text[start:end + 1])
        requires_human = payload.get("requires_human")
        if not isinstance(requires_human, bool):
            raise ValueError("requires_human must be a boolean")

        risk_level = str(payload.get("risk_level", "medium")).lower()
        if risk_level not in {"low", "medium", "high"}:
            risk_level = "medium"

        raw_reasons = payload.get("reasons", [])
        if not isinstance(raw_reasons, list):
            raw_reasons = [str(raw_reasons)]
        reasons = [
            re.sub(r"\s+", " ", str(reason)).strip()[:200]
            for reason in raw_reasons
            if str(reason).strip()
        ][:5]

        raw_unsupported = payload.get("unsupported_claims", [])
        if not isinstance(raw_unsupported, list):
            raw_unsupported = [str(raw_unsupported)]
        unsupported_claims = [
            re.sub(r"\s+", " ", str(claim)).strip()[:200]
            for claim in raw_unsupported
            if str(claim).strip()
        ][:5]

        if unsupported_claims:
            requires_human = True
            reasons.append("回答包含没有证据支持的关键陈述")

        if risk_level == "high":
            requires_human = True

        if requires_human and risk_level == "low":
            risk_level = "medium"

        if requires_human and not reasons:
            reasons = ["审核模型判断需要人工复核"]

        return {
            "requires_human": requires_human,
            "risk_level": risk_level,
            "reasons": reasons,
            "unsupported_claims": unsupported_claims,
        }

    @staticmethod
    def _set_audit(
        state,
        requires_human,
        risk_level,
        reasons,
        source,
        unsupported_claims=None,
    ):
        state["requires_human"] = requires_human
        state["human_review_reason"] = (
            reasons[0] if requires_human and reasons else None
        )
        state["audit_result"] = {
            "decision": (
                "human_review" if requires_human else "approved"
            ),
            "risk_level": risk_level,
            "reasons": list(reasons),
            "source": source,
            "unsupported_claims": list(unsupported_claims or []),
        }
