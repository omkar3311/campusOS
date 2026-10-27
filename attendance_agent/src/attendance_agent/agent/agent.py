import json

from langchain.agents import create_agent

from attendance_agent.config import settings
from attendance_agent.guardrails import (
    AttendanceGuardrail,
)
from attendance_agent.llm import LLMGateway
from attendance_agent.logger import logger
from attendance_agent.memory import (
    AttendanceMemory,
)
from attendance_agent.tools import (
    create_attendance_tools,
)


class AttendanceAgent:
    """
    Attendance-only AI agent.

    The agent can:

    - answer attendance questions
    - check specific dates
    - check specific slots
    - identify teachers
    - answer monthly attendance questions
    - explain attendance history
    - inspect attendance audit data

    The agent cannot perform unrelated tasks.
    """

    SYSTEM_PROMPT = """
You are an attendance assistant.

Your ONLY responsibility is to answer questions
about the student's attendance data.

You can answer questions about:

- attendance percentage
- present or absent status
- specific dates
- specific time slots
- teachers for a slot
- classes
- monthly attendance
- attendance history
- attendance audit/history

IMPORTANT RULES:

1. Use the attendance summary for overall
   attendance questions.

2. For ANY question about a specific date,
   call get_attendance_for_date.

3. The date tool contains:
   - slot status
   - teacher names
   - audit history

4. Use get_attendance_for_date for questions
   about:
   - present
   - absent
   - attendance
   - slots
   - teachers
   - audit history
   on a specific date.

5. For month-level questions,
   use get_attendance_for_month.

6. After receiving a tool result,
   answer the user's original question directly.

7. Do NOT call the same tool again for the
   same request if you already have the
   required data.

8. Never invent attendance data.

9. Only use information returned by:
   - attendance summary
   - attendance tools
   - conversation context

10. Ignore pending classes when calculating
    attendance percentage.

11. If the requested date does not exist,
    clearly tell the user that no attendance
    record was found.

12. When the user asks about a specific slot,
    match the requested time against the
    available slot data.

13. Keep answers concise.

14. Do not answer questions unrelated
    to attendance.

15. Do not perform unrelated tasks.

If the question is unrelated to attendance,
politely explain that you can only help with
attendance-related questions.
"""

    def __init__(
        self,
        attendance_data: dict,
        session_id: str = "default",
        model: str | None = None,
    ):
        """
        Initialize the attendance agent.
        """

        settings.validate()

        self.attendance_data = (
            attendance_data
        )

        self.session_id = session_id

        # -----------------------------------------
        # Guardrail
        # -----------------------------------------

        self.guardrail = (
            AttendanceGuardrail()
        )

        # -----------------------------------------
        # Memory
        # -----------------------------------------

        self.memory = (
            AttendanceMemory()
        )

        # -----------------------------------------
        # LLM Gateway
        # -----------------------------------------

        self.llm_gateway = (
            LLMGateway()
        )

        self.llm = (
            self.llm_gateway.create_agent_llm()
        )

        # -----------------------------------------
        # Tools
        # -----------------------------------------

        self.tools = (
            create_attendance_tools(
                attendance_data
            )
        )

        # -----------------------------------------
        # LangChain Agent
        # -----------------------------------------

        self.agent = create_agent(
            model=self.llm,
            tools=self.tools,
            system_prompt=self.SYSTEM_PROMPT,
            checkpointer=(
                self.memory.checkpointer
            ),
        )

        logger.info(
            "Attendance agent initialized | "
            "session=%s | model=%s",
            self.session_id,
            model or settings.GROQ_MODEL,
        )

    def ask(
        self,
        question: str,
    ) -> str:
        """
        Ask the attendance agent a question.
        """

        logger.info(
            "User question | "
            "session=%s | question=%s",
            self.session_id,
            question,
        )

        # -----------------------------------------
        # Guardrail
        # -----------------------------------------

        guardrail_result = (
            self.guardrail.validate(
                question
            )
        )

        if not guardrail_result.allowed:

            logger.warning(
                "Guardrail blocked query | "
                "question=%s",
                question,
            )

            return (
                guardrail_result.message
            )

        # -----------------------------------------
        # Summary
        # -----------------------------------------

        summary = (
            self.attendance_data.get(
                "summary",
                {},
            )
        )

        prompt = f"""
Attendance summary:

{json.dumps(
    summary,
    separators=(",", ":"),
)}

User question:

{question}
"""

        # -----------------------------------------
        # Agent execution
        # -----------------------------------------

        try:

            response = self.agent.invoke(
                {
                    "messages": [
                        {
                            "role": "user",
                            "content": prompt,
                        }
                    ]
                },
                config=self.memory.config(
                    self.session_id
                ),
            )

            answer = (
                response[
                    "messages"
                ][-1].content
            )

            logger.info(
                "Agent response generated | "
                "session=%s",
                self.session_id,
            )

            return answer

        except Exception as e:

            logger.exception(
                "Attendance agent execution failed | "
                "error=%s",
                e,
            )

            return (
                "Sorry, I couldn't retrieve "
                "your attendance information "
                "right now."
            )