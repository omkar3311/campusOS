from __future__ import annotations

import logging
import os

from langchain_core.embeddings import Embeddings
from langchain_core.language_models.chat_models import (
    BaseChatModel,
)
from langchain_groq import ChatGroq
from langchain_google_genai import (
    ChatGoogleGenerativeAI,
)

from helpdesk_agent.logger import LOGGER


LOGGER = logging.getLogger(
    "helpdesk_agent.llm"
)


class LLMGateway:

    def __init__(self):

        LOGGER.info(
            "Initializing LLM fallback chain."
        )

        self.model = self._create_model()

        LOGGER.info(
            "LLM fallback chain initialized successfully."
        )

    def _create_model(
        self,
    ) -> BaseChatModel:

        groq1_key = os.getenv(
            "GROQ_API_KEY"
        )

        groq2_key = os.getenv(
            "GROQ_API_KEY0"
        )

        gemini_key = os.getenv(
            "GEMINI_API_KEY"
        )

        if not groq1_key:

            LOGGER.warning(
                "GROQ_API_KEY is not configured."
            )

        if not groq2_key:

            LOGGER.warning(
                "GROQ_API_KEY0 is not configured."
            )

        if not gemini_key:

            LOGGER.warning(
                "GEMINI_API_KEY is not configured."
            )

        groq1 = ChatGroq(
            model="openai/gpt-oss-20b",
            temperature=0,
            api_key=groq1_key,
        )

        groq2 = ChatGroq(
            model="openai/gpt-oss-20b",
            temperature=0,
            api_key=groq2_key,
        )

        gemini = ChatGoogleGenerativeAI(
            model="gemini-2.5-flash",
            temperature=0,
            google_api_key=gemini_key,
        )

        LOGGER.info(
            "Configured LLM fallback order: "
            "Groq-1 -> Groq-2 -> Gemini."
        )

        return groq1.with_fallbacks(
            [
                groq2,
                gemini,
            ]
        )

    def get_model(
        self,
    ) -> BaseChatModel:

        return self.model

    def invoke(
        self,
        messages,
    ):

        LOGGER.debug(
            "Invoking LLM fallback chain."
        )

        try:

            response = self.model.invoke(
                messages
            )

            LOGGER.debug(
                "LLM invocation successful."
            )

            return response

        except Exception:

            LOGGER.exception(
                "All configured LLM fallbacks failed."
            )

            raise


class EmbeddingGateway:

    def __init__(
        self,
        model: str | None = None,
    ):

        from helpdesk_agent.config import (
            get_settings,
        )

        settings = get_settings()

        self.provider = (
            settings.embedding_provider.lower()
        )

        self.model_name = (
            model
            or settings.embedding_model
        )

        self._embeddings: Embeddings | None = None

    def get_embeddings(
        self,
    ) -> Embeddings:

        if self._embeddings is not None:

            return self._embeddings

        if self.provider == "openai":

            from langchain_openai import (
                OpenAIEmbeddings,
            )

            self._embeddings = (
                OpenAIEmbeddings(
                    model=self.model_name
                )
            )

        elif self.provider == "huggingface":

            # Original model load kept for reference and disabled to avoid repeated startup downloads.
            # from langchain_huggingface import (
            #     HuggingFaceEmbeddings,
            # )
            # self._embeddings = (
            #     HuggingFaceEmbeddings(
            #         model_name=self.model_name
            #     )
            # )
            try:
                from main import get_shared_embedding_model
                self._embeddings = get_shared_embedding_model()
            except Exception:
                self._embeddings = None

        elif self.provider == "google":

            from langchain_google_genai import (
                GoogleGenerativeAIEmbeddings,
            )

            self._embeddings = (
                GoogleGenerativeAIEmbeddings(
                    model=self.model_name
                )
            )

        else:

            raise ValueError(
                "Unsupported embedding provider: "
                f"{self.provider}"
            )

        LOGGER.info(
            "Initialized embedding provider=%s "
            "model=%s",
            self.provider,
            self.model_name,
        )

        return self._embeddings