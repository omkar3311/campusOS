import logging

from dotenv import load_dotenv
from langchain_groq import ChatGroq
import os
from langchain_google_genai import ChatGoogleGenerativeAI


LOGGER = logging.getLogger(__name__)


class LLMGateway:

    def __init__(self):
        load_dotenv()
        self.model_name = "openai/gpt-oss-20b"

    def create_agent(self):
        
        try:
            groq1 = ChatGroq(
                model=self.model_name,
                temperature=0,
                api_key=os.getenv("GROQ_API_KEY"),
            )

            groq2 = ChatGroq(
                model=self.model_name,
                temperature=0,
                api_key=os.getenv("GROQ_API_KEY0"),
            )

            gemini = ChatGoogleGenerativeAI(
                model="gemini-2.5-flash",
                temperature=0,
                google_api_key=os.getenv("GEMINI_API_KEY"),
            )

            return groq1.with_fallbacks([
                groq2,
                gemini,
            ])
        except Exception as e:
            LOGGER.error(
                f"Error creating LLM model: {e}"
            )
            raise

    def create_judge(self) -> ChatGroq:
        try:
            judge_llm = ChatGroq(
                model=self.model_name,
                temperature=0,
            )

            LOGGER.info(
                f"Created judge model: {self.model_name}"
            )

            return judge_llm

        except Exception as e:
            LOGGER.error(
                f"Error creating judge model: {e}"
            )
            raise