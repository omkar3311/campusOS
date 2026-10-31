from __future__ import annotations

import logging
import os
from dotenv import load_dotenv
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
        load_dotenv()

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

        configured_models: list[BaseChatModel] = []

        if groq1_key:
            configured_models.append(
                ChatGroq(
                    model="openai/gpt-oss-20b",
                    temperature=0,
                    api_key=groq1_key,
                )
            )

        if groq2_key:
            configured_models.append(
                ChatGroq(
                    model="openai/gpt-oss-20b",
                    temperature=0,
                    api_key=groq2_key,
                )
            )

        if gemini_key:
            configured_models.append(
                ChatGoogleGenerativeAI(
                    model="gemini-2.5-flash",
                    temperature=0,
                    google_api_key=gemini_key,
                )
            )

        if not configured_models:
            raise RuntimeError(
                "No LLM API keys are configured. Set GROQ_API_KEY, GROQ_API_KEY0, "
                "or GEMINI_API_KEY in your environment before starting the helpdesk agent."
            )

        primary_model = configured_models[0]
        fallback_models = configured_models[1:]

        LOGGER.info(
            "Configured LLM fallback order: %s.",
            " -> ".join(
                [
                    "Groq-1" if groq1_key else "",
                    "Groq-2" if groq2_key else "",
                    "Gemini" if gemini_key else "",
                ]
            ).strip(" -> "),
        )

        if not fallback_models:
            return primary_model

        return primary_model.with_fallbacks(
            fallback_models
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

            try:
                from langchain_huggingface import (
                    HuggingFaceEmbeddings,
                )

                self._embeddings = HuggingFaceEmbeddings(
                    model_name=self.model_name
                )
            except Exception:
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