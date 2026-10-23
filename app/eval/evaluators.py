import time
from typing import Dict
from app.eval.base import BaseEvaluator, EvalResult
from app.graph.workflow import graph
from app.guardrails import GuardrailManager, EmptyResponseGuardrail, ParkingDomainGuardrail


class ResponseQualityEvaluator(BaseEvaluator):
    """Evaluates the quality of agent responses."""

    def __init__(self):
        self.guardrail_manager = GuardrailManager()
        self.guardrail_manager.add_guardrail(EmptyResponseGuardrail())
        self.guardrail_manager.add_guardrail(ParkingDomainGuardrail())

    def get_name(self) -> str:
        return "Response Quality"

    def evaluate(self, test_case: Dict) -> EvalResult:
        question = test_case["question"]
        expected_agent = test_case.get("expected_agent")
        expected_keywords = test_case.get("expected_keywords", [])

        start_time = time.time()
        
        try:
            state = {
                "question": question,
                "session_id": "eval_session",
                "history": [],
                "next_agent": None,
                "customer_id": None,
                "parking_lot_id": None,
                "reservation_id": None,
                "vehicle_plate": None,
                "intent": None,
                "confidence": 1,
                "api_result": {},
                "requires_human": False,
                "response": None
            }

            result = graph.invoke(state)
            response_time = time.time() - start_time

            response = result.get("response", "")
            
            # Check guardrails
            guardrail_passed, _ = self.guardrail_manager.validate_all(response)
            
            # Check for expected keywords
            keyword_matches = sum(
                1 for kw in expected_keywords
                if kw.lower() in response.lower()
            )
            keyword_score = keyword_matches / len(expected_keywords) if expected_keywords else 1.0

            # Calculate overall score
            score = 0.0
            if guardrail_passed:
                score += 0.5
            score += keyword_score * 0.5

            passed = score >= 0.7 and guardrail_passed

            return EvalResult(
                test_name=f"{self.get_name()}: {question[:50]}",
                passed=passed,
                score=score,
                details={
                    "response": response,
                    "guardrail_pass": guardrail_passed,
                    "keyword_matches": keyword_matches,
                    "response_time": response_time,
                    "expected_agent": expected_agent,
                    "actual_agent": result.get("next_agent")
                }
            )

        except Exception as e:
            return EvalResult(
                test_name=f"{self.get_name()}: {question[:50]}",
                passed=False,
                score=0.0,
                error=str(e),
                details={"response_time": time.time() - start_time}
            )


class AgentRoutingEvaluator(BaseEvaluator):
    """Evaluates if the supervisor routes to the correct agent."""

    def get_name(self) -> str:
        return "Agent Routing"

    def evaluate(self, test_case: Dict) -> EvalResult:
        question = test_case["question"]
        expected_agent = test_case.get("expected_agent")

        start_time = time.time()

        try:
            state = {
                "question": question,
                "session_id": "eval_session",
                "history": [],
                "next_agent": None,
                "customer_id": None,
                "parking_lot_id": None,
                "reservation_id": None,
                "vehicle_plate": None,
                "intent": None,
                "confidence": 1,
                "api_result": {},
                "requires_human": False,
                "response": None
            }

            result = graph.invoke(state)
            response_time = time.time() - start_time

            actual_agent = result.get("next_agent")
            passed = actual_agent == expected_agent
            score = 1.0 if passed else 0.0

            return EvalResult(
                test_name=f"{self.get_name()}: {question[:50]}",
                passed=passed,
                score=score,
                details={
                    "expected_agent": expected_agent,
                    "actual_agent": actual_agent,
                    "response_time": response_time
                }
            )

        except Exception as e:
            return EvalResult(
                test_name=f"{self.get_name()}: {question[:50]}",
                passed=False,
                score=0.0,
                error=str(e),
                details={"response_time": time.time() - start_time}
            )


class GuardrailEvaluator(BaseEvaluator):
    """Tests guardrail effectiveness with edge cases."""

    def __init__(self):
        from app.guardrails import (
            EmptyResponseGuardrail,
            MinLengthGuardrail,
            ProfanityGuardrail,
            ParkingDomainGuardrail
        )
        self.guardrail_manager = GuardrailManager()
        self.guardrail_manager.add_guardrail(EmptyResponseGuardrail())
        self.guardrail_manager.add_guardrail(MinLengthGuardrail(min_length=10))
        self.guardrail_manager.add_guardrail(ProfanityGuardrail())
        self.guardrail_manager.add_guardrail(ParkingDomainGuardrail())

    def get_name(self) -> str:
        return "Guardrail"

    def evaluate(self, test_case: Dict) -> EvalResult:
        test_type = test_case.get("test_type", "response")
        test_response = test_case.get("test_response", "")
        should_pass = test_case.get("should_pass", True)

        start_time = time.time()

        try:
            passed, reasons = self.guardrail_manager.validate_all(test_response)
            response_time = time.time() - start_time

            # Test passes if the guardrail behavior matches expectation
            test_passed = (passed == should_pass)
            score = 1.0 if test_passed else 0.0

            return EvalResult(
                test_name=f"{self.get_name()}: {test_type}",
                passed=test_passed,
                score=score,
                details={
                    "should_pass": should_pass,
                    "actual_pass": passed,
                    "reasons": reasons,
                    "response_time": response_time,
                    "guardrail_pass": passed
                }
            )

        except Exception as e:
            return EvalResult(
                test_name=f"{self.get_name()}: {test_type}",
                passed=False,
                score=0.0,
                error=str(e),
                details={"response_time": time.time() - start_time}
            )
