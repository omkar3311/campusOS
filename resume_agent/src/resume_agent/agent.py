import logging
from typing import Any

from langchain.agents import create_agent

from resume_agent.guardrails.guardrails import Guardrails
from resume_agent.llm_gateway import LLMGateway
from resume_agent.response import AgentLogger
from resume_agent.tools.tools import Tools
from resume_agent.prompts.prompts import get_prompt
from langchain.agents.middleware import (
    ToolRetryMiddleware,
    ToolCallLimitMiddleware,
)


LOGGER = logging.getLogger(__name__)


class ResumeAgent:

    modes = {
        "1": "Resume Review Agent",
        "2": "Placement Eligibility Checker",
        "3": "Skill Gap Analyzer",
        "4": "Interview Preparation Agent",
        "5": "Coding Practice Recommender",
        "6": "Career Recommendation Agent",
    }

    def __init__(
        self,
        guardrails: Guardrails | None = None,
    ) -> None:
        self.guardrails = guardrails or Guardrails()
        self.tools_manager = Tools()
        self.llm = LLMGateway()
        self.response = AgentLogger()
        self._agents: dict[str, Any] = {}
        self.tools = self.tools_manager._build_tools()

    def ask(
        self,
        question: str,
        job_description: str | None = None,
        mode: str | None = None,
    ) -> str:

        self.tools_manager._require_resumes()

        question = self.guardrails.check_question(question)

        if job_description:
            job_description = self.guardrails.check_job_description(
                job_description
            )

        mode_name = self._mode_name(
            mode or self._infer_mode(question)
        )

        agent = (
            self._agents.get(mode_name)
            or self._create_agent(mode_name)
        )

        self._agents[mode_name] = agent

        jd_context = ""

        if job_description:
            jd_context = (
                "\n\nJob description supplied by the user:\n"
                f"{job_description}"
            )

        resume_context = self.tools_manager.loader._resume_catalog()

        response = agent.invoke(
            {
                "messages": [
                    {
                        "role": "system",
                        "content": resume_context,
                    },
                    {
                        "role": "user",
                        "content": question + jd_context,
                    },
                   
                ]
            },
            #  config={
            #     "recursion_limit": 5,
            #     },
        )

        answer = ""

        for message in reversed(
            response.get("messages", [])
        ):
            content = getattr(message, "content", "")

            if isinstance(content, str) and content.strip():
                answer = content.strip()
                break

        if not answer:
            answer = (
                "I could not produce a response "
                "from the resume evidence."
            )

        self.tools_manager.update_session_memory(
            question,
            answer,
        )

        LOGGER.info("Session memory updated.")

        self.response.debug_agent_response(response)

        return self.guardrails.check_output(answer)

    def load_resume(
        self,
        paths: list[str],
    ):
        loaded, docs = self.tools_manager.loader.load_resume(paths)

        self.tools_manager._store._store_documents(docs)

        return loaded, docs
    
    def _create_agent(self, mode: str) -> Any:

        model = self.llm.create_agent()

        prompt = get_prompt(mode)

        return create_agent(
            model,
            tools=self.tools,
            system_prompt=prompt,
            middleware=[
            # Retry a failed tool call
            ToolRetryMiddleware(
                max_retries=2,
            ),
            ToolCallLimitMiddleware(
                tool_name="profile_memory_tool",
                run_limit=1,
                exit_behavior="end",
            ),
            # Maximum 2 tool calls in one agent run
            ToolCallLimitMiddleware(
                run_limit=2,
                exit_behavior="end",
            ),
        ],
        )

    def _infer_mode(self, question: str) -> str:

        text = question.lower()

        if any(
            word in text
            for word in (
                "eligible",
                "eligibility",
                "placement",
            )
        ):
            return "2"

        if any(
            word in text
            for word in (
                "missing skill",
                "skill gap",
            )
        ):
            return "3"

        if "interview" in text:
            return "4"

        if any(
            word in text
            for word in (
                "coding practice",
                "dsa",
                "leetcode",
            )
        ):
            return "5"

        if any(
            word in text
            for word in (
                "career",
                "role suits",
                "suitable role",
            )
        ):
            return "6"

        return "1"

    def _mode_name(self, mode: str) -> str:

        if mode in self.modes:
            return self.modes[mode]

        if mode in self.modes.values():
            return mode

        raise ValueError(
            f"Unknown mode {mode!r}. "
            "Use 1-6 or a value from ResumeAgent.modes."
        )