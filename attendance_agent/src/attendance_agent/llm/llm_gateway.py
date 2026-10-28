import logging
import os

from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_google_genai import (
    ChatGoogleGenerativeAI,
)

from attendance_agent.config import settings


LOGGER = logging.getLogger(
    "attendance_agent.llm"
)


class LLMGateway:
    """
    Centralized LLM gateway for the attendance agent.

    Primary:
        Groq #1

    Fallback:
        Groq #2

    Final fallback:
        Gemini
    """

    def __init__(self):
        load_dotenv()

        self.model_name = os.getenv(
            "GROQ_MODEL",
            "openai/gpt-oss-20b"
        )

    def create_agent_llm(self):
        """
        Create the LLM used by the attendance agent.

        Fallback order:

            Groq #1
                ↓
            Groq #2
                ↓
            Gemini
        """

        try:

            groq1 = ChatGroq(
                model=self.model_name,
                temperature=0,
                api_key=os.getenv(
                    "GROQ_API_KEY"
                ),
            )

            groq2 = ChatGroq(
                model=self.model_name,
                temperature=0,
                api_key=os.getenv(
                    "GROQ_API_KEY0"
                ),
            )

            gemini = ChatGoogleGenerativeAI(
                model="gemini-2.5-flash",
                temperature=0,
                google_api_key=os.getenv(
                    "GEMINI_API_KEY"
                ),
            )

            llm = groq1.with_fallbacks(
                [
                    groq2,
                    gemini,
                ]
            )

            LOGGER.info(
                "Created attendance LLM gateway | "
                "primary=%s | fallback=Groq#2 | "
                "final_fallback=Gemini",
                self.model_name,
            )

            return llm

        except Exception as e:

            LOGGER.exception(
                "Error creating attendance "
                "LLM gateway: %s",
                e,
            )

            raise

    def create_judge(self):
        """
        Create a standalone judge LLM.

        Currently not used by the attendance agent,
        but kept here so the architecture matches
        the other agents and can be used later for
        response evaluation.
        """

        try:

            judge_llm = ChatGroq(
                model=self.model_name,
                temperature=0,
                api_key=os.getenv(
                    "GROQ_API_KEY"
                ),
            )

            LOGGER.info(
                "Created attendance judge model: %s",
                self.model_name,
            )

            return judge_llm

        except Exception as e:

            LOGGER.exception(
                "Error creating attendance "
                "judge model: %s",
                e,
            )

            raise