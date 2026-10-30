from __future__ import annotations

import logging

from langchain_core.messages import (
    BaseMessage,
    HumanMessage,
)

from langchain_core.prompts import (
    ChatPromptTemplate,
)

from helpdesk_agent.llm import (
    LLMGateway,
)


LOGGER = logging.getLogger(
    "helpdesk_agent.memory"
)


class SessionMemory:

    def __init__(self):

        self._checkpointer = None

    def get_checkpointer(self):

        if self._checkpointer is None:

            from langgraph.checkpoint.memory import (
                MemorySaver,
            )

            self._checkpointer = (
                MemorySaver()
            )

            LOGGER.info(
                "Session memory initialized."
            )

        return self._checkpointer

    @staticmethod
    def build_config(
        session_id: str,
    ) -> dict:

        if not session_id:

            raise ValueError(
                "session_id cannot be empty."
            )

        return {
            "configurable": {
                "thread_id": session_id,
            }
        }


class SessionSummarizer:

    def __init__(
        self,
        llm_gateway: LLMGateway | None = None,
    ):

        self.llm_gateway = (
            llm_gateway
            or LLMGateway(
                temperature=0.0
            )
        )

    def summarize(
        self,
        messages: list[BaseMessage],
    ) -> str:

        if not messages:

            return ""

        conversation = "\n".join(
            self._format_message(
                message
            )
            for message in messages
        )

        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    """
Summarize the following college helpdesk
conversation.

Preserve useful user-specific context,
questions, unresolved issues, and important
facts.

Do not invent information.

Keep the summary concise.
""",
                ),
                (
                    "human",
                    "{conversation}",
                ),
            ]
        )

        chain = (
            prompt
            | self.llm_gateway.get_model()
        )

        response = chain.invoke(
            {
                "conversation": conversation
            }
        )

        return str(
            response.content
        ).strip()

    @staticmethod
    def _format_message(
        message: BaseMessage,
    ) -> str:

        role = message.__class__.__name__

        content = (
            message.content
            if isinstance(
                message.content,
                str,
            )
            else str(message.content)
        )

        return f"{role}: {content}"