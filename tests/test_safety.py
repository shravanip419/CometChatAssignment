import pytest
from app.agent.safety_validator import SafetyValidator
from app.models.schemas import AgentResponse


def test_safety_validator_redacts_email_leak():
    validator = SafetyValidator()
    leak_response = AgentResponse(
        answer="The customer's email address is test.user@example.test for order ORD-1001.",
        sources=[],
        handoff=False
    )
    validated = validator.validate(leak_response)
    assert "test.user@example.test" not in validated.answer
    assert "privacy and data security" in validated.answer
    assert validated.handoff is True


def test_safety_validator_catches_action_hallucination():
    validator = SafetyValidator()
    hallucination_response = AgentResponse(
        answer="I have cancelled your order ORD-1002 and issued a full refund.",
        sources=[],
        handoff=False
    )
    validated = validator.validate(hallucination_response)
    assert "cannot directly execute order modifications" in validated.answer
    assert validated.handoff is True


def test_safety_validator_passes_clean_response():
    validator = SafetyValidator()
    clean_response = AgentResponse(
        answer="Customers on the standard plan may request a return within 30 calendar days of delivery.",
        sources=[],
        handoff=False
    )
    validated = validator.validate(clean_response)
    assert validated.answer == clean_response.answer
    assert validated.handoff is False
