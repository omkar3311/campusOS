from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field


LOGGER = logging.getLogger(
    "helpdesk_agent.guardrails"
)


class GuardrailViolation(Exception):
    """
    Raised when a guardrail blocks
    a request or response.
    """

    pass


@dataclass
class GuardrailConfig:

    max_question_length: int = 3000

    max_context_length: int = 12000

    max_answer_length: int = 8000

    redact_pii: bool = True

    prompt_injection_patterns: list[str] = field(
        default_factory=lambda: [

            r"\bignore\s+(all\s+)?previous\s+instructions\b",

            r"\bignore\s+(all\s+)?prior\s+instructions\b",

            r"\bignore\s+(all\s+)?system\s+instructions\b",

            r"\bdisregard\s+(all\s+)?previous\s+instructions\b",

            r"\bdisregard\s+(all\s+)?prior\s+instructions\b",

            r"\bforget\s+(all\s+)?previous\s+instructions\b",

            r"\boverride\s+(the\s+)?system\s+instructions\b",

            r"\bignore\s+the\s+retrieved\s+(documents|context)\b",

            r"\bdisregard\s+the\s+retrieved\s+(documents|context)\b",

            r"\breveal\s+(your\s+)?system\s+prompt\b",

            r"\bshow\s+(me\s+)?(your\s+)?system\s+prompt\b",

            r"\bprint\s+(your\s+)?system\s+prompt\b",

            r"\bdisplay\s+(your\s+)?system\s+prompt\b",

            r"\bwhat\s+are\s+your\s+system\s+instructions\b",

            r"\bwhat\s+are\s+your\s+hidden\s+instructions\b",

            r"\breveal\s+(your\s+)?hidden\s+prompt\b",

            r"\bbypass\s+(your\s+)?guardrails\b",

            r"\bdisable\s+(your\s+)?guardrails\b",

            r"\bremove\s+(your\s+)?restrictions\b",

            r"\bjailbreak\b",

            r"\bdan\s+mode\b",

            r"\bdeveloper\s+mode\b",
        ]
    )

    blocked_patterns: list[str] = field(
        default_factory=lambda: [

            r"\bhow\s+to\s+make\s+(?:a\s+)?bomb\b",

            r"\bhow\s+to\s+build\s+(?:a\s+)?bomb\b",

            r"\bhow\s+to\s+make\s+(?:an\s+)?explosive\b",

            r"\bhow\s+to\s+build\s+(?:an\s+)?explosive\b",

            r"\bhow\s+to\s+hack\b",

            r"\bhow\s+to\s+break\s+into\b",

            r"\bgenerate\s+malware\b",

            r"\bwrite\s+(?:a\s+)?virus\b",

            r"\bwrite\s+(?:a\s+)?ransomware\b",

            r"\bcreate\s+(?:a\s+)?keylogger\b",

            r"\bsteal\s+(?:a\s+)?password\b",

            r"\bsteal\s+(?:someone's\s+)?credentials\b",
        ]
    )

    unsafe_output_patterns: list[str] = field(
        default_factory=lambda: [

            r"\bhere\s+is\s+how\s+to\s+make\s+(?:a\s+)?bomb\b",

            r"\bhere\s+is\s+how\s+to\s+hack\b",

            r"\bhere\s+is\s+the\s+malware\b",

            r"\bhere\s+is\s+the\s+virus\b",

            r"\bhere\s+is\s+the\s+ransomware\b",
        ]
    )


class Guardrails:

    def __init__(
        self,
        config: GuardrailConfig | None = None,
    ):

        self.config = (
            config
            or GuardrailConfig()
        )

        self.injection_patterns = [
            re.compile(
                pattern,
                re.IGNORECASE,
            )
            for pattern
            in self.config.prompt_injection_patterns
        ]

        self.blocked_patterns = [
            re.compile(
                pattern,
                re.IGNORECASE,
            )
            for pattern
            in self.config.blocked_patterns
        ]

        self.unsafe_output_patterns = [
            re.compile(
                pattern,
                re.IGNORECASE,
            )
            for pattern
            in self.config.unsafe_output_patterns
        ]

        LOGGER.info(
            "Helpdesk guardrails initialized."
        )

    def validate_question(
        self,
        question: str,
    ) -> str:

        if not isinstance(
            question,
            str,
        ):

            raise GuardrailViolation(
                "Question must be text."
            )

        question = question.strip()

        if not question:

            raise GuardrailViolation(
                "Question cannot be empty."
            )

        if len(question) > (
            self.config.max_question_length
        ):

            LOGGER.warning(
                "Question exceeded maximum length."
            )

            raise GuardrailViolation(
                "Question is too long."
            )

        self._check_prompt_injection(
            question
        )

        self._check_blocked_request(
            question
        )

        return self._normalize(
            question
        )

    def validate_context(
        self,
        context: str,
    ) -> str:

        if not context:

            raise GuardrailViolation(
                "No relevant college information "
                "was found."
            )

        context = context.strip()

        if not context:

            raise GuardrailViolation(
                "No relevant college information "
                "was found."
            )

        if len(context) > (
            self.config.max_context_length
        ):

            LOGGER.warning(
                "Retrieved context exceeded limit."
            )

            context = context[
                :self.config.max_context_length
            ]

        return context

    def validate_output(
        self,
        answer: str,
    ) -> str:

        if not answer:

            return (
                "I could not generate a response "
                "to your question."
            )

        answer = str(answer).strip()

        if len(answer) > (
            self.config.max_answer_length
        ):

            LOGGER.warning(
                "LLM answer exceeded maximum length."
            )

            answer = answer[
                :self.config.max_answer_length
            ].rstrip()

        self._check_unsafe_output(
            answer
        )

        if self.config.redact_pii:

            answer = self._redact_pii(
                answer
            )

        return answer

    def validate_retrieval(
        self,
        documents: list,
    ) -> list:

        if not documents:

            LOGGER.info(
                "No documents returned from retrieval."
            )

            return []

        return documents

    def _check_prompt_injection(
        self,
        text: str,
    ):

        for pattern in self.injection_patterns:

            if pattern.search(text):

                LOGGER.warning(
                    "Prompt injection detected."
                )

                raise GuardrailViolation(
                    "Your request contains an "
                    "instruction pattern that "
                    "cannot be processed."
                )

    def _check_blocked_request(
        self,
        text: str,
    ):

        for pattern in self.blocked_patterns:

            if pattern.search(text):

                LOGGER.warning(
                    "Blocked request detected."
                )

                raise GuardrailViolation(
                    "This request is outside "
                    "the capabilities of the "
                    "College Helpdesk Agent."
                )

    def _check_unsafe_output(
        self,
        text: str,
    ):

        for pattern in self.unsafe_output_patterns:

            if pattern.search(text):

                LOGGER.error(
                    "Unsafe LLM output detected."
                )

                raise GuardrailViolation(
                    "The generated response "
                    "could not be returned."
                )

    def _redact_pii(
        self,
        text: str,
    ) -> str:

        email_pattern = re.compile(
            r"\b[A-Za-z0-9._%+-]+"
            r"@[A-Za-z0-9.-]+\."
            r"[A-Za-z]{2,}\b"
        )

        phone_pattern = re.compile(
            r"(?<!\d)"
            r"(?:\+91[\s-]?)?"
            r"[6-9]\d{9}"
            r"(?!\d)"
        )

        text = email_pattern.sub(
            "[EMAIL REDACTED]",
            text,
        )

        text = phone_pattern.sub(
            "[PHONE REDACTED]",
            text,
        )

        return text

    @staticmethod
    def _normalize(
        text: str,
    ) -> str:

        text = re.sub(
            r"[ \t]+",
            " ",
            text,
        )

        text = re.sub(
            r"\n{3,}",
            "\n\n",
            text,
        )

        return text.strip()