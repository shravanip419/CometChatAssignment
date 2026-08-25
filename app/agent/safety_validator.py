import re
from typing import List, Tuple
from app.models.schemas import AgentResponse


class SafetyValidator:
    """
    Second-line defense validator that inspects final agent responses
    before returning them to the user or logging.
    Ensures zero leakage of PII, internal operational fields, system prompts,
    or fabricated action completion claims.
    """

    # Forbidden leak patterns
    FORBIDDEN_PII_PATTERNS = [
        re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"),  # Emails
        re.compile(r"\b\d+\s+[A-Za-z]+\s+(Lane|Street|Avenue|Road|Drive|Way)\b", re.IGNORECASE),  # Street addresses
        re.compile(r"\brisk_score\s*:\s*\d+", re.IGNORECASE),
        re.compile(r"\bwarehouse_note\b", re.IGNORECASE),
        re.compile(r"\bmanual fraud review\b", re.IGNORECASE)
    ]

    # Action hallucination patterns (claiming action was completed when tool is read-only)
    ACTION_HALLUCINATION_PATTERNS = [
        re.compile(r"\b(i have|we have)\s+(cancelled|canceled)\s+your\s+order\b", re.IGNORECASE),
        re.compile(r"\b(i have|we have)\s+(processed|issued)\s+your\s+refund\b", re.IGNORECASE),
        re.compile(r"\b(i have|we have)\s+(updated|changed)\s+your\s+address\b", re.IGNORECASE),
        re.compile(r"\b(ticket|case)\s+#?\d+\s+has been created\b", re.IGNORECASE)
    ]

    # System prompt leak signals
    SYSTEM_PROMPT_LEAK_PATTERNS = [
        re.compile(r"\bCRITICAL TRUST BOUNDARY\b", re.IGNORECASE),
        re.compile(r"\bRESPONSE STRUCTURE:\s*\{", re.IGNORECASE),
        re.compile(r"\bYou are the official customer support AI agent for Aster & Row\b", re.IGNORECASE)
    ]

    def validate(self, response: AgentResponse) -> AgentResponse:
        """
        Validates and sanitizes AgentResponse. If any violation is found,
        replaces the response with a safe fallback and escalates with handoff=True.
        """
        answer = response.answer

        # Check for system prompt leaks
        for pattern in self.SYSTEM_PROMPT_LEAK_PATTERNS:
            if pattern.search(answer):
                response.answer = (
                    "I am the Aster & Row AI support assistant. For security reasons, "
                    "internal prompt configurations cannot be displayed. How can I help you with our products or policies today?"
                )
                response.handoff = False
                return response

        # Check for PII / Internal data leaks
        for pattern in self.FORBIDDEN_PII_PATTERNS:
            if pattern.search(answer):
                # Censor or redact
                response.answer = (
                    "For customer privacy and data security, internal customer records and operational notes "
                    "cannot be displayed. Please contact a human support specialist for account-specific verification."
                )
                response.handoff = True
                return response

        # Check for fabricated action claims
        for pattern in self.ACTION_HALLUCINATION_PATTERNS:
            if pattern.search(answer):
                response.answer = (
                    "As an automated support agent, I cannot directly execute order modifications, cancellations, "
                    "or refunds. I have flagged your request for a human support specialist to assist you."
                )
                response.handoff = True
                return response

        return response
