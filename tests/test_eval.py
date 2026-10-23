"""
Evaluation test cases for the Parking AI system.

Run with: ./.venv/bin/python tests/test_eval.py
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from app.eval import (
    EvaluationSuite,
    ResponseQualityEvaluator,
    AgentRoutingEvaluator,
    GuardrailEvaluator
)


def get_response_quality_test_cases():
    """Test cases for response quality evaluation."""
    return [
        {
            "question": "How much does parking cost?",
            "expected_agent": "pricing",
            "expected_keywords": ["price", "cost", "rate", "fee"]
        },
        {
            "question": "I want to book a parking spot",
            "expected_agent": "reservation",
            "expected_keywords": ["reservation", "book", "spot"]
        },
        {
            "question": "What are your operating hours?",
            "expected_agent": "support",
            "expected_keywords": ["hours", "open", "24"]
        },
        {
            "question": "Can I cancel my reservation?",
            "expected_agent": "reservation",
            "expected_keywords": ["cancel", "reservation", "refund"]
        },
        {
            "question": "How do I pay for parking?",
            "expected_agent": "support",
            "expected_keywords": ["payment", "pay", "card", "cash"]
        }
    ]


def get_agent_routing_test_cases():
    """Test cases for agent routing evaluation."""
    return [
        {
            "question": "How much is parking?",
            "expected_agent": "pricing"
        },
        {
            "question": "I need to reserve a spot",
            "expected_agent": "reservation"
        },
        {
            "question": "Where is the parking lot?",
            "expected_agent": "support"
        },
        {
            "question": "What's the daily rate?",
            "expected_agent": "pricing"
        },
        {
            "question": "Can I change my booking?",
            "expected_agent": "reservation"
        }
    ]


def get_guardrail_test_cases():
    """Test cases for guardrail evaluation."""
    return [
        {
            "test_type": "empty_response",
            "test_response": "",
            "should_pass": False
        },
        {
            "test_type": "whitespace_only",
            "test_response": "   ",
            "should_pass": False
        },
        {
            "test_type": "valid_response",
            "test_response": "Our parking facility is open 24 hours a day for your convenience.",
            "should_pass": True
        },
        {
            "test_type": "too_short",
            "test_response": "Yes",
            "should_pass": False
        },
        {
            "test_type": "profanity",
            "test_response": "This parking is damn expensive",
            "should_pass": False
        },
        {
            "test_type": "non_parking",
            "test_response": "I like playing basketball on weekends",
            "should_pass": False
        },
        {
            "test_type": "good_parking_response",
            "test_response": "Parking costs $12 per day on weekdays. We accept credit cards and mobile payments.",
            "should_pass": True
        }
    ]


def run_evaluations():
    """Run all evaluation suites."""
    print("Running Parking AI Evaluations...\n")

    # Response Quality Evaluation
    print("1. Response Quality Evaluation")
    print("-" * 40)
    quality_suite = EvaluationSuite()
    quality_suite.add_evaluator(ResponseQualityEvaluator())
    quality_metrics = quality_suite.run_suite(get_response_quality_test_cases())
    quality_suite.print_report()

    # Agent Routing Evaluation
    print("\n2. Agent Routing Evaluation")
    print("-" * 40)
    routing_suite = EvaluationSuite()
    routing_suite.add_evaluator(AgentRoutingEvaluator())
    routing_metrics = routing_suite.run_suite(get_agent_routing_test_cases())
    routing_suite.print_report()

    # Guardrail Evaluation
    print("\n3. Guardrail Evaluation")
    print("-" * 40)
    guardrail_suite = EvaluationSuite()
    guardrail_suite.add_evaluator(GuardrailEvaluator())
    guardrail_metrics = guardrail_suite.run_suite(get_guardrail_test_cases())
    guardrail_suite.print_report()

    # Overall Summary
    print("\n" + "="*60)
    print("OVERALL SUMMARY")
    print("="*60)
    total_tests = (
        quality_metrics.total_tests +
        routing_metrics.total_tests +
        guardrail_metrics.total_tests
    )
    total_passed = (
        quality_metrics.passed_tests +
        routing_metrics.passed_tests +
        guardrail_metrics.passed_tests
    )
    overall_pass_rate = total_passed / total_tests if total_tests > 0 else 0.0

    print(f"Total Tests: {total_tests}")
    print(f"Total Passed: {total_passed}")
    print(f"Overall Pass Rate: {overall_pass_rate:.2%}")
    print("="*60)

    return {
        "quality": quality_metrics,
        "routing": routing_metrics,
        "guardrail": guardrail_metrics,
        "overall_pass_rate": overall_pass_rate
    }


if __name__ == "__main__":
    results = run_evaluations()
    
    # Exit with error code if pass rate is below threshold
    if results["overall_pass_rate"] < 0.7:
        print("\n⚠️  Evaluation pass rate below 70% threshold")
        sys.exit(1)
    else:
        print("\n✅ Evaluation passed!")
        sys.exit(0)
