from __future__ import annotations

import logging
from typing import Annotated, TypedDict

from langchain_core.documents import Document
from langchain_core.messages import (
    AIMessage,
    BaseMessage,
    HumanMessage,
)
from operator import add

from langgraph.graph import (
    END,
    START,
    StateGraph,
)

from helpdesk_agent.guardrails import (
    GuardrailViolation,
    Guardrails,
)
from helpdesk_agent.llm import (
    LLMGateway,
)
from helpdesk_agent.memory import (
    SessionMemory,
)
from helpdesk_agent.prompts import (
    RAG_PROMPT,
)
from helpdesk_agent.retrieval import (
    VectorStore,
)


LOGGER = logging.getLogger(
    "helpdesk_agent.agent"
)


class HelpdeskState(TypedDict, total=False):

    question: str

    messages: Annotated[
        list[BaseMessage],
        add
    ]

    context: str

    documents: list[Document]

    answer: str

    sources: list[str]

    error: str


class HelpdeskGraph:

    def __init__(
        self,
        vector_store: VectorStore | None = None,
        llm_gateway: LLMGateway | None = None,
        guardrails: Guardrails | None = None,
        memory: SessionMemory | None = None,
    ):

        self.vector_store = (
            vector_store
            or VectorStore()
        )

        self.llm_gateway = (
            llm_gateway
            or LLMGateway()
        )

        self.guardrails = (
            guardrails
            or Guardrails()
        )

        self.memory = (
            memory
            or SessionMemory()
        )

        self.graph = self._build_graph()

    def _build_graph(self):

        workflow = StateGraph(
            HelpdeskState
        )

        workflow.add_node(
            "validate_input",
            self.validate_input,
        )

        workflow.add_node(
            "retrieve",
            self.retrieve,
        )

        workflow.add_node(
            "generate",
            self.generate,
        )

        workflow.add_node(
            "validate_output",
            self.validate_output,
        )

        workflow.add_edge(
            START,
            "validate_input",
        )

        workflow.add_edge(
            "validate_input",
            "retrieve",
        )

        workflow.add_edge(
            "retrieve",
            "generate",
        )

        workflow.add_edge(
            "generate",
            "validate_output",
        )

        workflow.add_edge(
            "validate_output",
            END,
        )

        return workflow.compile(
            checkpointer=(
                self.memory
                .get_checkpointer()
            )
        )

    def validate_input(
        self,
        state: HelpdeskState,
    ) -> dict:

        question = state.get(
            "question",
            "",
        )

        try:

            validated_question = (
                self.guardrails
                .validate_question(
                    question
                )
            )

        except GuardrailViolation as exc:

            LOGGER.warning(
                "Input guardrail blocked request: %s",
                exc,
            )

            raise

        return {
            "question": validated_question,
            "messages": [
                HumanMessage(
                    content=validated_question
                )
            ],
        }

    def retrieve(
        self,
        state: HelpdeskState,
    ) -> dict:

        question = state[
            "question"
        ]

        documents = (
            self.vector_store
            .similarity_search(
                question
            )
        )

        documents = (
            self.guardrails
            .validate_retrieval(
                documents
            )
        )

        if not documents:

            LOGGER.info(
                "No relevant documents found."
            )

            return {
                "documents": [],
                "context": "",
                "sources": [],
            }

        context_parts: list[str] = []
        sources: list[str] = []

        for index, document in enumerate(
            documents,
            start=1,
        ):

            source = str(
                document.metadata.get(
                    "source",
                    "unknown",
                )
            )

            page = document.metadata.get(
                "page"
            )

            if page is not None:

                source_label = (
                    f"{source} "
                    f"(page {page + 1})"
                )

            else:

                source_label = source

            sources.append(
                source_label
            )

            context_parts.append(
                f"[Document {index}]\n"
                f"Source: {source_label}\n"
                f"{document.page_content}"
            )

        context = "\n\n".join(
            context_parts
        )

        context = (
            self.guardrails
            .validate_context(
                context
            )
        )

        LOGGER.info(
            "Retrieved %d documents.",
            len(documents),
        )

        return {
            "documents": documents,
            "context": context,
            "sources": sources,
        }

    def generate(
        self,
        state: HelpdeskState,
    ) -> dict:

        context = state.get(
            "context",
            "",
        )

        question = state[
            "question"
        ]

        chat_history = (
            state.get(
                "messages",
                []
            )
        )

        if not context:

            answer = (
                "I couldn't find enough "
                "information in the college "
                "knowledge base to answer "
                "your question."
            )

            return {
                "answer": answer,
                "messages": [
                    AIMessage(
                        content=answer
                    )
                ],
            }

        history = (
            chat_history[:-1]
            if chat_history
            else []
        )

        chain = (
            RAG_PROMPT
            | self.llm_gateway.get_model()
        )

        response = chain.invoke(
            {
                "context": context,
                "question": question,
                "chat_history": history,
            }
        )

        answer = str(
            response.content
        ).strip()

        LOGGER.info(
            "Generated helpdesk response."
        )

        return {
            "answer": answer,
            "messages": [
                AIMessage(
                    content=answer
                )
            ],
        }

    def validate_output(
        self,
        state: HelpdeskState,
    ) -> dict:

        answer = state.get(
            "answer",
            "",
        )

        try:

            validated_answer = (
                self.guardrails
                .validate_output(
                    answer
                )
            )

        except GuardrailViolation as exc:

            LOGGER.error(
                "Output guardrail blocked response: %s",
                exc,
            )

            raise

        return {
            "answer": validated_answer,
        }

    def invoke(
        self,
        question: str,
        session_id: str = "default",
    ) -> dict:

        config = (
            self.memory
            .build_config(
                session_id
            )
        )

        result = self.graph.invoke(
            {
                "question": question,
            },
            config=config,
        )

        return result

    def stream(
        self,
        question: str,
        session_id: str = "default",
    ):

        config = (
            self.memory
            .build_config(
                session_id
            )
        )

        return self.graph.stream(
            {
                "question": question,
            },
            config=config,
        )