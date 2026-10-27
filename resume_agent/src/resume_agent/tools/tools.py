import logging
from typing import Any

from langchain_core.tools import BaseTool, tool

from resume_agent.utils.ats_utils import ATSUtils
from resume_agent.utils.jd_utils import JDUtils
from resume_agent.loaders.loader import ResumeLoader
from resume_agent.memory.memory import Profile, SessionMemory
from resume_agent.retrieval.store import ResumeStore


LOGGER = logging.getLogger(__name__)


class Tools:

    def __init__(self):
        self.loader = ResumeLoader()
        self.profile_memory = self.loader.profile_memory
        self.session_memory = SessionMemory()
        self._store = ResumeStore(loader=self.loader)
        self.ats = ATSUtils()
        self.jd = JDUtils(
            ats_utils=self.ats,
            context_provider=self._context,
        )

    def _build_tools(self) -> list[BaseTool]:

        def load_resume_tool(self, paths: list[str]) -> list[str]:
            """
            Load resumes through ResumeLoader and
            index them into the vector store.
            """

            loaded , docs = self.loader.load_resume(paths)

            self._store._store_documents(docs)

            return loaded

        @tool("resume_search_tool")
        def resume_search_tool(
            query: str,
            filename: str = "",
        ) -> dict[str, Any]:
            """Retrieve resume chunks before answering any question about a resume."""
            return {
                "results": self._store._search(
                    query,
                    filename=filename or None,
                )
            }

        @tool("resume_review_tool")
        def resume_review_tool(
            question: str,
            filename: str = "",
        ) -> dict[str, Any]:
            """Retrieve grounded evidence for a concise professional resume review."""
            return {
                "evidence": self._context(
                    question,
                    filename=filename or None,
                )
            }

        @tool("ats_score_tool")
        def ats_score_tool(
            filename: str = "",
        ) -> dict[str, Any]:
            """Calculate ATS score, sections, and suggestions using ResumeIQ logic."""
            return self._ats_result(filename or None)

        @tool("jd_match_tool")
        def jd_match_tool(
            job_description: str,
            filename: str = "",
        ) -> dict[str, Any]:
            """Compare a retrieved resume with a job description using ResumeIQ scoring."""
            return self.jd._jd_result(
                job_description,
                filename or None,
            )

        @tool("placement_checker_tool")
        def placement_checker_tool(
            job_description: str,
            filename: str = "",
        ) -> dict[str, Any]:
            """Assess placement eligibility against a JD from retrieved resume evidence."""
            result = self.jd._jd_result(
                job_description,
                filename or None,
            )

            score = result["final_match"]

            result["eligibility"] = (
                "Eligible"
                if score >= 70
                else "Borderline"
                if score >= 40
                else "Not Eligible"
            )

            return result

        @tool("skill_gap_tool")
        def skill_gap_tool(
            job_description: str,
            filename: str = "",
        ) -> dict[str, Any]:
            """Identify JD skills absent from retrieved resume evidence and learning priority."""
            result = self.jd._jd_result(
                job_description,
                filename or None,
            )

            result["learning_priority"] = result["missing_skills"]

            return result

        @tool("interview_question_tool")
        def interview_question_tool(
            question: str,
            job_description: str = "",
            filename: str = "",
        ) -> dict[str, Any]:
            """Retrieve only the resume/JD evidence needed to create interview questions."""
            result: dict[str, Any] = {
                "resume_evidence": self._context(
                    question,
                    filename=filename or None,
                )
            }

            if job_description:
                result["jd_match"] = self.jd._jd_result(
                    job_description,
                    filename or None,
                )

            return result

        @tool("coding_practice_tool")
        def coding_practice_tool(
            question: str,
            filename: str = "",
        ) -> dict[str, Any]:
            """Retrieve skills and projects to ground coding-practice recommendations."""
            return {
                "resume_evidence": self._context(
                    question + " skills projects programming",
                    filename=filename or None,
                )
            }

        @tool("career_recommendation_tool")
        def career_recommendation_tool(
            question: str,
            filename: str = "",
        ) -> dict[str, Any]:
            """Retrieve skills, education, projects, and experience for career suggestions."""
            return {
                "resume_evidence": self._context(
                    question + " skills education projects experience",
                    filename=filename or None,
                )
            }

        @tool("resume_compare_tool")
        def resume_compare_tool(
            job_description: str = "",
        ) -> dict[str, Any]:
            """Rank loaded resumes using ResumeIQ JD ranking, or ATS score when no JD is given."""
            self._require_resumes()

            ranked = []

            for record in self.loader.records().values():
                result = (
                    self.jd._jd_result(
                        job_description,
                        record["filename"],
                    )
                    if job_description
                    else self._ats_result(
                        record["filename"]
                    )
                )

                ranked.append(
                    {
                        "filename": record["filename"],
                        "candidate_name": record["candidate_name"],
                        "score": result.get(
                            "final_match",
                            result.get("ats_score", 0),
                        ),
                    }
                )

            return {
                "ranking": sorted(
                    ranked,
                    key=lambda item: item["score"],
                    reverse=True,
                )
            }

        @tool("resume_summary_tool")
        def resume_summary_tool(
            filename: str = "",
        ) -> dict[str, Any]:
            """Retrieve resume facts needed for a professional summary; do not invent facts."""
            return {
                "resume_evidence": self._context(
                    "summary education experience projects skills certifications",
                    filename=filename or None,
                )
            }

        @tool("resume_section_tool")
        def resume_section_tool(
            section: str,
            filename: str = "",
        ) -> dict[str, Any]:
            """Retrieve a requested resume section, such as projects, education, or certifications."""
            return {
                "section": section,
                "resume_evidence": self._context(
                    section,
                    filename=filename or None,
                ),
            }

        # @tool("profile_memory_tool")
        # def profile_memory(candidate_name:str) -> str:
        #     """
        #     Retrieve the user's resume-derived profile.
        #     Use this when stable information about the candidate
        #     is needed.
        #     """
        #     profile = self.profile_memory.get_profile(candidate_name)

        #     if not profile:
        #         return "No profile memory is available."

        #     return profile

        # @tool("session_memory_tool")
        # def session_memory() -> str:
        #     """
        #     Retrieve summarized context from the current conversation.
        #     Use this when information from an earlier part of the
        #     current session is needed.
        #     """
        #     memory = self.session_memory.get_session_memory()

        #     if not memory:
        #         return "No previous session memory is available."

        #     return memory

        return [
            load_resume_tool,
            resume_search_tool,
            resume_review_tool,
            ats_score_tool,
            jd_match_tool,
            placement_checker_tool,
            skill_gap_tool,
            interview_question_tool,
            coding_practice_tool,
            career_recommendation_tool,
            resume_compare_tool,
            resume_summary_tool,
            resume_section_tool,
            # profile_memory,
            # session_memory,
        ]

    def _context(
        self,
        query: str,
        *,
        filename: str | None = None,
    ) -> str:
        results = self._store._search(
            query,
            filename=filename,
            k=12,
        )

        return "\n\n".join(
            item["content"]
            for item in results
        )

    def _ats_result(
        self,
        filename: str | None,
    ) -> dict[str, Any]:
        evidence = self._context(
            "contact email phone skills projects education experience objective summary",
            filename=filename,
        )

        sections = self.ats.section_maker(
            evidence,
            self.ats.section_map,
        )

        score, feedback = self.ats.ats_score(
            evidence,
            sections,
        )

        structure_feedback, detected, missing = (
            self.ats.evaluate_resume_structure(
                sections,
            )
        )

        return {
            "filename": filename,
            "ats_score": score,
            "detected_sections": detected,
            "missing_sections": missing,
            "suggestions": list(
                dict.fromkeys(
                    feedback + structure_feedback
                )
            ),
            "project_count": self.ats.count_projects(
                sections.get("projects", [])
            ),
            "evidence": evidence,
        }

    def _require_resumes(self) -> None:
        records = self.loader.records()

        if not records or self._store is None:
            LOGGER.error(
                "No resumes loaded. Please load at least one resume."
            )
            raise RuntimeError(
                "Load at least one resume before using this operation."
            )
            
    def update_session_memory(
        self,
        question: str,
        answer: str,
    ) -> str:

        return self.session_memory.set_session_memory(
            question,
            answer,
        )