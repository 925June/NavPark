from abc import ABC
from abc import abstractmethod
from typing import Dict
from typing import List
from typing import Any
from dataclasses import dataclass
from dataclasses import field


@dataclass
class EvalResult:
    """Result of a single evaluation test."""
    test_name: str
    passed: bool
    score: float
    details: Dict[str, Any] = field(default_factory=dict)
    error: str = ""


@dataclass
class EvalMetrics:
    """Aggregated metrics from evaluation runs."""
    total_tests: int = 0
    passed_tests: int = 0
    failed_tests: int = 0
    pass_rate: float = 0.0
    average_score: float = 0.0
    guardrail_pass_rate: float = 0.0
    average_response_time: float = 0.0
    results: List[EvalResult] = field(default_factory=list)

    def calculate(self):
        """Calculate aggregated metrics from results."""
        self.total_tests = len(self.results)
        self.passed_tests = sum(1 for r in self.results if r.passed)
        self.failed_tests = self.total_tests - self.passed_tests
        self.pass_rate = self.passed_tests / self.total_tests if self.total_tests > 0 else 0.0
        self.average_score = sum(r.score for r in self.results) / self.total_tests if self.total_tests > 0 else 0.0
        
        guardrail_results = [r for r in self.results if "guardrail_pass" in r.details]
        if guardrail_results:
            self.guardrail_pass_rate = sum(
                r.details["guardrail_pass"] for r in guardrail_results
            ) / len(guardrail_results)
        
        response_times = [r.details.get("response_time", 0) for r in self.results]
        if response_times:
            self.average_response_time = sum(response_times) / len(response_times)


class BaseEvaluator(ABC):

    @abstractmethod
    def evaluate(self, test_case: Dict) -> EvalResult:
        """Run a single evaluation test case."""
        pass

    @abstractmethod
    def get_name(self) -> str:
        """Get the name of this evaluator."""
        pass


class EvaluationSuite:

    def __init__(self):
        self.evaluators: List[BaseEvaluator] = []
        self.metrics = EvalMetrics()

    def add_evaluator(self, evaluator: BaseEvaluator):
        self.evaluators.append(evaluator)

    def run_suite(self, test_cases: List[Dict]) -> EvalMetrics:
        """Run all evaluators against all test cases."""
        self.metrics.results = []

        for test_case in test_cases:
            for evaluator in self.evaluators:
                result = evaluator.evaluate(test_case)
                self.metrics.results.append(result)

        self.metrics.calculate()
        return self.metrics

    def print_report(self):
        """Print a human-readable evaluation report."""
        print("\n" + "="*60)
        print("EVALUATION REPORT")
        print("="*60)
        print(f"Total Tests: {self.metrics.total_tests}")
        print(f"Passed: {self.metrics.passed_tests}")
        print(f"Failed: {self.metrics.failed_tests}")
        print(f"Pass Rate: {self.metrics.pass_rate:.2%}")
        print(f"Average Score: {self.metrics.average_score:.2f}")
        print(f"Guardrail Pass Rate: {self.metrics.guardrail_pass_rate:.2%}")
        print(f"Average Response Time: {self.metrics.average_response_time:.3f}s")
        print("="*60)

        if self.metrics.failed_tests > 0:
            print("\nFailed Tests:")
            for result in self.metrics.results:
                if not result.passed:
                    print(f"  - {result.test_name}: {result.error or result.details}")
