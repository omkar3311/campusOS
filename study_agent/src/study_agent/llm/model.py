from __future__ import annotations

import os
import logging

from langchain_groq import ChatGroq
from langchain_google_genai import ChatGoogleGenerativeAI


from study_agent.logger import LOGGER


class LLMModel:

    def __init__(self):

        LOGGER.info(
            "Initializing LLM fallback chain."
        )

        self.model = self._create_model()

        LOGGER.info(
            "LLM fallback chain initialized successfully."
        )

    def _create_model(self):

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

    def get_model(self):

        return self.model

    def invoke(
        self,
        messages
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