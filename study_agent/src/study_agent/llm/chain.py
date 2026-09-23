from langchain_core.output_parsers import (
    StrOutputParser
)

from langchain_core.prompts import (
    ChatPromptTemplate
)

from study_agent.guardrails import (
    Guardrails
)

from study_agent.logger import LOGGER

from study_agent.llm.model import (
    LLMModel
)

from study_agent.llm.prompts import (
    AcademicPrompt
)


class LLMChain:

    def __init__(
        self,
        guardrails: Guardrails
    ):

        LOGGER.info(
            "Initializing LLM chain."
        )

        self.guardrails = guardrails

        # =====================================
        # MODEL
        # =====================================

        llm_model = LLMModel()

        self.model = (
            llm_model.get_model()
        )

        # =====================================
        # PROMPT
        # =====================================

        academic_prompt = AcademicPrompt()

        self.prompt = (
            ChatPromptTemplate
            .from_template(
                academic_prompt.get_template()
            )
        )

        # =====================================
        # OUTPUT PARSER
        # =====================================

        self.output_parser = (
            StrOutputParser()
        )

        # =====================================
        # CHAIN
        # =====================================

        self.chain = (
            self.prompt
            | self.model
            | self.output_parser
        )

        LOGGER.info(
            "LLM chain initialized successfully."
        )

    def generate(
        self,
        question: str,
        context: str,
        session_memory: str | None = None,
    ):

        LOGGER.info(
            "Generating academic response."
        )

        safe_question = (
            self.guardrails
            .validate_question(
                question
            )
        )

        safe_context = (
            self.guardrails
            .validate_context(
                context
            )
        )

        session_memory = (
            session_memory
            or "No previous session memory."
        )

        try:

            response = self.chain.invoke(
                {
                    "question": safe_question,
                    "context": safe_context,
                    "session_memory": session_memory,
                }
            )

            answer = (
                self.guardrails
                .validate_output(
                    response
                )
            )

            LOGGER.info(
                "Academic response generated successfully."
            )

            return answer

        except Exception:

            LOGGER.exception(
                "LLM response generation failed."
            )

            raise