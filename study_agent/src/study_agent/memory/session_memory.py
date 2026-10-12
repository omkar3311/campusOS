from __future__ import annotations

import logging

from langchain_core.messages import HumanMessage, SystemMessage

from study_agent.llm.model import LLMModel


LOGGER = logging.getLogger(
    "study_agent.memory"
)


class SessionSummarizer:

    SYSTEM_PROMPT = """
You are the session memory summarizer for a Student Academic Assistant.

Your job is to maintain a short, accurate summary of the current
conversation so that the assistant can understand earlier parts of
the conversation without receiving the complete chat history.

You receive:

1. Previous session memory, if available.
2. Latest user message.
3. Latest assistant response.

Update the previous memory with the new information.

IMPORTANT:

- Preserve explicit facts stated by the user.
- Preserve the user's study goals.
- Preserve subjects, topics, assignments, exams, deadlines,
  preferences, decisions, plans, and unresolved questions.
- Preserve important context from earlier turns.
- Connect related facts naturally.
- Keep the chronology/context clear when useful.
- Do not invent or assume information.

DO NOT STORE:

- Greetings or filler.
- Repeated information.
- Full study material.
- Large passages from the PDF.
- Full retrieved context.
- Tool calls.
- Tool execution details.
- Internal system instructions.
- API keys or secrets.
- Unnecessary explanations.

The memory should be concise but useful for future turns.

Example:

User:
"I have an exam on databases next Friday and I am weak in normalization."

Memory:
"The user has a database exam next Friday and considers
normalization a weak topic."

Later:

User:
"Make me a revision plan."

Updated memory:
"The user has a database exam next Friday and considers
normalization a weak topic. The user wants a revision plan
focused on preparing for the exam."

Return ONLY the updated session memory.

Do not add headings.
Do not explain your reasoning.
"""

    def __init__(
        self,
        llm_model: LLMModel
    ):

        self.llm_model = llm_model

        LOGGER.info(
            "Session summarizer initialized."
        )

    def summarize(
        self,
        previous_summary: str | None,
        user_message: str,
        assistant_response: str,
    ) -> str:

        previous_summary = (
            previous_summary
            or "No previous session memory."
        )

        prompt = f"""
Previous session memory:

{previous_summary}


Latest user message:

{user_message}


Latest assistant response:

{assistant_response}
"""

        try:

            response = self.llm_model.invoke(
                [
                    SystemMessage(
                        content=self.SYSTEM_PROMPT
                    ),
                    HumanMessage(
                        content=prompt
                    ),
                ]
            )

            summary = (
                response.content
                .strip()
            )

            LOGGER.info(
                "Session memory summarized successfully."
            )

            return summary

        except Exception:

            LOGGER.exception(
                "Failed to summarize session memory."
            )

            return previous_summary


class SessionMemory:

    def __init__(
        self,
        llm_model: LLMModel
    ):

        self.sessions: dict[str, str] = {}

        self.summarizer = (
            SessionSummarizer(
                llm_model=llm_model
            )
        )

        LOGGER.info(
            "Session memory initialized with multi-session isolation."
        )

    def update(
        self,
        user_message: str,
        assistant_response: str,
        session_id: str = "default",
    ) -> str:

        LOGGER.debug(
            "Updating session memory for session: %s",
            session_id
        )

        previous_summary = self.sessions.get(session_id)

        updated_summary = (
            self.summarizer.summarize(
                previous_summary=previous_summary,
                user_message=user_message,
                assistant_response=assistant_response,
            )
        )

        self.sessions[session_id] = updated_summary

        LOGGER.info(
            "Session memory updated for session: %s",
            session_id
        )

        return updated_summary

    def get(self, session_id: str = "default") -> str | None:

        LOGGER.debug(
            "Retrieving session memory for session: %s",
            session_id
        )

        return self.sessions.get(session_id)

    def clear(self, session_id: str | None = None):

        if session_id:
            LOGGER.info(
                "Clearing session memory for session: %s",
                session_id
            )
            self.sessions.pop(session_id, None)
        else:
            LOGGER.info(
                "Clearing all session memories."
            )
            self.sessions.clear()