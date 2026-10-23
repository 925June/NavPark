from typing import Dict
from app.guardrails.base import BaseGuardrail


class EmptyResponseGuardrail(BaseGuardrail):
    """Ensures responses are not empty or whitespace-only."""

    def validate(
        self,
        response: str,
        context: Dict = None
    ) -> tuple[bool, str]:
        if not response or not response.strip():
            return False, "Response is empty or contains only whitespace"
        return True, ""


class MinLengthGuardrail(BaseGuardrail):
    """Ensures responses meet minimum length requirements."""

    def __init__(self, min_length: int = 10):
        self.min_length = min_length

    def validate(
        self,
        response: str,
        context: Dict = None
    ) -> tuple[bool, str]:
        if len(response.strip()) < self.min_length:
            return False, f"Response is too short (minimum {self.min_length} characters)"
        return True, ""


class MaxLengthGuardrail(BaseGuardrail):
    """Prevents responses from being too long."""

    def __init__(self, max_length: int = 1000):
        self.max_length = max_length

    def validate(
        self,
        response: str,
        context: Dict = None
    ) -> tuple[bool, str]:
        if len(response) > self.max_length:
            return False, f"Response is too long (maximum {self.max_length} characters)"
        return True, ""


class ProfanityGuardrail(BaseGuardrail):
    """Basic profanity filter."""

    def __init__(self):
        self.profanity_list = {
            "damn", "hell", "ass", "shit", "fuck",
            "bitch", "bastard", "crap"
        }

    def validate(
        self,
        response: str,
        context: Dict = None
    ) -> tuple[bool, str]:
        words = response.lower().split()
        found_profanity = [
            word for word in words
            if word in self.profanity_list
        ]
        
        if found_profanity:
            return False, f"Response contains prohibited language: {', '.join(found_profanity)}"
        return True, ""


class PIIGuardrail(BaseGuardrail):
    """Detects potential PII in responses (email, phone, SSN patterns)."""

    def __init__(self):
        import re
        self.email_pattern = re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b')
        self.phone_pattern = re.compile(r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b')
        self.ssn_pattern = re.compile(r'\b\d{3}[-.]?\d{2}[-.]?\d{4}\b')

    def validate(
        self,
        response: str,
        context: Dict = None
    ) -> tuple[bool, str]:
        issues = []

        if self.email_pattern.search(response):
            issues.append("email address")
        if self.phone_pattern.search(response):
            issues.append("phone number")
        if self.ssn_pattern.search(response):
            issues.append("SSN")

        if issues:
            return False, f"Response may contain PII: {', '.join(issues)}"
        return True, ""


class ParkingDomainGuardrail(BaseGuardrail):
    """Ensures responses are relevant to parking domain."""

    def __init__(self):
        self.parking_keywords = {
            "parking", "reservation", "price", "cost", "fee", "rate",
            "vehicle", "car", "spot", "lot", "garage", "payment",
            "ticket", "booking", "cancel", "hour", "day", "month",
            "location", "facility", "security", "electric", "charging"
        }

    def validate(
        self,
        response: str,
        context: Dict = None
    ) -> tuple[bool, str]:
        response_lower = response.lower()
        has_parking_context = any(
            keyword in response_lower
            for keyword in self.parking_keywords
        )

        if not has_parking_context:
            return False, "Response does not appear to be parking-related"
        return True, ""
