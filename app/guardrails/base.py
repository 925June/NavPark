from abc import ABC
from abc import abstractmethod
from typing import Dict
from typing import List


class BaseGuardrail(ABC):

    @abstractmethod
    def validate(
        self,
        response: str,
        context: Dict = None
    ) -> tuple[bool, str]:
        """
        Validate a response.
        
        Returns:
            (is_valid, reason) - tuple where is_valid is True if response passes,
            and reason explains why it failed if is_valid is False
        """
        pass


class GuardrailManager:

    def __init__(self):
        self.guardrails: List[BaseGuardrail] = []

    def add_guardrail(self, guardrail: BaseGuardrail):
        self.guardrails.append(guardrail)

    def validate_all(
        self,
        response: str,
        context: Dict = None
    ) -> tuple[bool, List[str]]:
        """
        Run all guardrails on a response.
        
        Returns:
            (all_passed, failure_reasons) - tuple where all_passed is True only
            if all guardrails pass, and failure_reasons contains reasons for any failures
        """
        all_passed = True
        failure_reasons = []

        for guardrail in self.guardrails:
            passed, reason = guardrail.validate(response, context)
            if not passed:
                all_passed = False
                failure_reasons.append(reason)

        return all_passed, failure_reasons
