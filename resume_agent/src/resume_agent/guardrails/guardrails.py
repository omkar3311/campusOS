"""
guardrails.py — CampusOS ResumeIQ Agent Guardrails

Guardrails for the CampusOS ResumeIQ Agent.

Responsibilities
----------------
INPUT:
    - Validate user questions
    - Validate job descriptions
    - Reject empty input
    - Enforce input length limits
    - Detect common prompt-injection attempts
    - Detect explicitly harmful requests

OUTPUT:
    - Validate generated responses
    - Remove accidental PII from user-facing responses
    - Detect obviously unsafe generated content
    - Never truncate valid responses

This component does not:
    - Modify internal resume or RAG evidence
    - Truncate LLM responses
    - Replace the LangChain system prompt
    - Replace tool-level authorization
    - Guarantee factual correctness of an LLM response
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import List


LOGGER = logging.getLogger(__name__)


class GuardrailViolation(ValueError):
    """
    Raised when a CampusOS ResumeIQ Agent guardrail blocks a request.
    """

    pass


@dataclass
class GuardrailsConfig:
    """
    Configuration for CampusOS ResumeIQ Agent guardrails.
    """

    max_question_chars: int = 2000
    max_job_description_chars: int = 15000
    enable_output_pii_redaction: bool = True

    domain_keywords: List[str] = field(
        default_factory=lambda: [
            "resume",
            "cv",
            "curriculum vitae",
            "ats",
            "job",
            "job description",
            "jd",
            "career",
            "placement",
            "interview",
            "skill",
            "skills",
            "skill gap",
            "experience",
            "project",
            "projects",
            "education",
            "degree",
            "certification",
            "certificate",
            "internship",
            "internships",
            "candidate",
            "eligibility",
            "eligible",
            "role",
            "roles",
            "hiring",
            "recruiter",
            "recruitment",
            "shortlist",
            "shortlisted",
            "application",
            "professional summary",
            "objective",
            "ats score",
            "match",
            "matching",
            "leetcode",
            "dsa",
            "coding practice",
        ]
    )

    injection_patterns: List[str] = field(
        default_factory=lambda: [
            r"\bignore\s+(all\s+)?previous\s+instructions\b",
            r"\bignore\s+(all\s+)?prior\s+instructions\b",
            r"\bignore\s+(all\s+)?system\s+instructions\b",
            r"\bdisregard\s+(all\s+)?previous\s+instructions\b",
            r"\bdisregard\s+(all\s+)?prior\s+instructions\b",
            r"\bforget\s+(all\s+)?previous\s+instructions\b",
            r"\boverride\s+(the\s+)?system\s+instructions\b",
            r"\breveal\s+(your\s+)?system\s+prompt\b",
            r"\bshow\s+(me\s+)?(your\s+)?system\s+prompt\b",
            r"\bprint\s+(your\s+)?system\s+prompt\b",
            r"\bdisplay\s+(your\s+)?system\s+prompt\b",
            r"\bwhat\s+are\s+your\s+system\s+instructions\b",
            r"\bwhat\s+are\s+your\s+hidden\s+instructions\b",
            r"\bbypass\s+(your\s+)?guardrails\b",
            r"\bdisable\s+(your\s+)?guardrails\b",
            r"\bremove\s+(your\s+)?restrictions\b",
            r"\bignore\s+(your\s+)?safety\s+rules\b",
            r"\bbypass\s+(your\s+)?safety\s+rules\b",
            r"\byou\s+are\s+now\s+(?:a|an)\b",
            r"\bpretend\s+you\s+are\b",
            r"\bact\s+as\s+(?:a|an)\b",
            r"\broleplay\s+as\b",
            r"\bjailbreak\b",
            r"\bdan\s+mode\b",
            r"\bdeveloper\s+mode\b",
        ]
    )

    blocked_request_patterns: List[str] = field(
        default_factory=lambda: [
            r"\bhow\s+to\s+make\s+(?:a\s+)?bomb\b",
            r"\bhow\s+to\s+build\s+(?:a\s+)?bomb\b",
            r"\bhow\s+to\s+make\s+(?:an\s+)?explosive\b",
            r"\bhow\s+to\s+hack\b",
            r"\bhow\s+to\s+break\s+into\b",
            r"\bgenerate\s+malware\b",
            r"\bwrite\s+(?:a\s+)?virus\b",
            r"\bwrite\s+(?:a\s+)?ransomware\b",
            r"\bcreate\s+(?:a\s+)?keylogger\b",
        ]
    )

    output_block_patterns: List[str] = field(
        default_factory=lambda: [
            r"\bhere\s+is\s+how\s+to\s+make\s+(?:a\s+)?bomb\b",
            r"\bhere\s+is\s+how\s+to\s+hack\b",
            r"\bhere\s+is\s+the\s+malware\b",
            r"\bhere\s+is\s+the\s+virus\b",
        ]
    )


class Guardrails:
    """
    Guardrail layer for the CampusOS ResumeIQ Agent.

    Example
    -------
    guardrails = Guardrails()

    question = guardrails.check_question(question)

    job_description = guardrails.check_job_description(job_description)

    answer = guardrails.check_output(answer)
    """

    def __init__(
        self,
        config: GuardrailsConfig | None = None,
    ) -> None:
        self.config = config or GuardrailsConfig()

        self._injection_patterns = [
            re.compile(pattern, re.IGNORECASE)
            for pattern in self.config.injection_patterns
        ]

        self._blocked_request_patterns = [
            re.compile(pattern, re.IGNORECASE)
            for pattern in self.config.blocked_request_patterns
        ]

        self._output_block_patterns = [
            re.compile(pattern, re.IGNORECASE)
            for pattern in self.config.output_block_patterns
        ]

        LOGGER.info("CampusOS ResumeIQ Agent guardrails initialized.")

    def check_question(self, question: str) -> str:
        """
        Validate a user question.

        Returns
        -------
        str
            Cleaned question.

        Raises
        ------
        GuardrailViolation
            If the question violates a guardrail.
        """

        if not isinstance(question, str):
            raise GuardrailViolation(
                "Question must be a string."
            )

        question = question.strip()

        if not question:
            raise GuardrailViolation(
                "Question cannot be empty."
            )

        if len(question) > self.config.max_question_chars:
            LOGGER.warning(
                "Question blocked because it exceeded maximum length."
            )

            raise GuardrailViolation(
                "Your question is too long. "
                f"Please keep it under "
                f"{self.config.max_question_chars} characters."
            )

        self._check_prompt_injection(question)
        self._check_blocked_request(question)

        return self._normalize_whitespace(question)

    def check_job_description(
        self,
        job_description: str | None,
    ) -> str | None:
        """
        Validate a supplied job description.

        Job descriptions have a larger length limit than normal questions.
        """

        if job_description is None:
            return None

        if not isinstance(job_description, str):
            raise GuardrailViolation(
                "Job description must be a string."
            )

        job_description = job_description.strip()

        if not job_description:
            return None

        if len(job_description) > self.config.max_job_description_chars:
            LOGGER.warning(
                "Job description blocked because it exceeded maximum length."
            )

            raise GuardrailViolation(
                "The job description is too long. "
                f"Please keep it under "
                f"{self.config.max_job_description_chars} characters."
            )

        self._check_prompt_injection(job_description)
        self._check_blocked_request(job_description)

        return self._normalize_whitespace(job_description)

    def check_domain(
        self,
        question: str,
        *,
        allow_general: bool = True,
    ) -> bool:
        """
        Perform a lightweight CampusOS ResumeIQ Agent domain check.

        This is intentionally not a strict keyword whitelist.

        The LLM system prompt remains responsible for semantic
        domain classification.

        Returns
        -------
        bool
            True if the question appears relevant to the agent.

        Notes
        -----
        A question such as:

            "Why am I not getting shortlisted?"

        is clearly career-related even though it does not contain
        the word "resume".

        Therefore this method should be treated as an additional
        signal rather than the sole domain decision mechanism.
        """

        if allow_general:
            return True

        lower_question = question.lower()

        return any(
            keyword in lower_question
            for keyword in self.config.domain_keywords
        )

    def check_output(self, answer: str) -> str:
        """
        Validate and sanitize the final LLM response.

        This method does not truncate output.

        A valid response should never be cut in the middle of a
        sentence simply because it exceeded an arbitrary character
        limit.
        """

        if answer is None:
            return ""

        if not isinstance(answer, str):
            answer = str(answer)

        answer = answer.strip()

        if not answer:
            LOGGER.warning(
                "CampusOS ResumeIQ Agent returned an empty response."
            )

            return (
                "I could not produce a response from the available "
                "resume evidence."
            )

        self._check_output_safety(answer)

        if self.config.enable_output_pii_redaction:
            answer = self._redact_output_pii(answer)

        return answer

    def _check_prompt_injection(
        self,
        text: str,
    ) -> None:
        """
        Detect common prompt-injection attempts.
        """

        for pattern in self._injection_patterns:
            if pattern.search(text):
                LOGGER.warning(
                    "Prompt injection attempt detected."
                )

                raise GuardrailViolation(
                    "Your request contains an instruction pattern "
                    "that cannot be processed."
                )

    def _check_blocked_request(
        self,
        text: str,
    ) -> None:
        """
        Detect explicitly harmful requests.
        """

        for pattern in self._blocked_request_patterns:
            if pattern.search(text):
                LOGGER.warning(
                    "Blocked harmful request detected."
                )

                raise GuardrailViolation(
                    "This request is outside the capabilities "
                    "of the CampusOS ResumeIQ Agent."
                )

    def _check_output_safety(
        self,
        answer: str,
    ) -> None:
        """
        Check for obviously unsafe generated content.

        This is a final safety layer and does not replace
        the agent system prompt.
        """

        for pattern in self._output_block_patterns:
            if pattern.search(answer):
                LOGGER.error(
                    "Unsafe content detected in agent output."
                )

                raise GuardrailViolation(
                    "The generated response could not be returned."
                )

    def _redact_output_pii(
        self,
        text: str,
    ) -> str:
        """
        Redact common PII from the final user-facing response.

        This method should not be applied to internal RAG evidence.

        Resume information needs to remain intact internally because
        ATS scoring, matching, and resume analysis may legitimately
        require access to it.
        """

        patterns = [
            (
                re.compile(
                    r"\b[A-Za-z0-9._%+-]+"
                    r"@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"
                ),
                "[EMAIL REDACTED]",
            ),
            (
                re.compile(
                    r"(?<!\d)"
                    r"(?:\+91[\s-]?)?"
                    r"[6-9]\d{9}"
                    r"(?!\d)"
                ),
                "[PHONE REDACTED]",
            ),
            (
                re.compile(
                    r"(?<!\d)"
                    r"(?:\+?1[\s.-]?)?"
                    r"\(?\d{3}\)?[\s.-]"
                    r"\d{3}[\s.-]\d{4}"
                    r"(?!\d)"
                ),
                "[PHONE REDACTED]",
            ),
            (
                re.compile(
                    r"\b\d{3}-\d{2}-\d{4}\b"
                ),
                "[SSN REDACTED]",
            ),
        ]

        for pattern, replacement in patterns:
            text = pattern.sub(replacement, text)

        return text

    @staticmethod
    def _normalize_whitespace(
        text: str,
    ) -> str:
        """
        Normalize excessive whitespace without changing meaning.
        """

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

    @staticmethod
    def get_violation_response(
        reason: str,
    ) -> dict:
        """
        Return a consistent JSON-safe response for API usage.
        """

        return {
            "answer": (
                "I couldn't process that request. "
                f"{reason}"
            ),
            "sources": [],
            "guardrail_blocked": True,
        }
