import re


class GuardrailResult:
    """Result returned by the attendance guardrail."""

    def __init__(
        self,
        allowed: bool,
        message: str = "",
    ):
        self.allowed = allowed
        self.message = message


class AttendanceGuardrail:
    """
    Keeps the agent focused only on attendance-related queries.
    """

    ATTENDANCE_KEYWORDS = {
        "attendance",
        "present",
        "absent",
        "absence",
        "attended",
        "teacher",
        "teachers",
        "professor",
        "faculty",
        "class",
        "classes",
        "slot",
        "slots",
        "period",
        "periods",
        "audit",
        "history",
        "marked",
        "percentage",
        "percent",
        "today",
        "yesterday",
        "tomorrow",
        "date",
        "month",
        "monthly",
        "week",
        "weekly",
    }

    def validate(
        self,
        question: str,
    ) -> GuardrailResult:
        """
        Validate whether a question is attendance-related.
        """

        if not question or not question.strip():
            return GuardrailResult(
                allowed=False,
                message=(
                    "Please ask an "
                    "attendance-related question."
                ),
            )

        normalized = (
            question
            .lower()
            .strip()
        )

        words = set(
            re.findall(
                r"\b[a-zA-Z]+\b",
                normalized,
            )
        )

        # Direct attendance-related question.
        if words.intersection(
            self.ATTENDANCE_KEYWORDS
        ):
            return GuardrailResult(
                allowed=True
            )

        # Allow questions containing dates.
        has_date = bool(
            re.search(
                r"\b\d{1,4}[-/]\d{1,2}[-/]\d{1,4}\b",
                normalized,
            )
        )

        # Allow questions containing time.
        has_time = bool(
            re.search(
                r"\b\d{1,2}\s*(am|pm)?\b",
                normalized,
            )
        )

        if has_date or has_time:
            return GuardrailResult(
                allowed=True
            )

        return GuardrailResult(
            allowed=False,
            message=(
                "I can only help with your "
                "attendance, classes, slots, "
                "teachers, or attendance history."
            ),
        )