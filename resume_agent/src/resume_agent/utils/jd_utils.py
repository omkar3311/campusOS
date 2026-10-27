import logging
from typing import Any, Callable

from resume_agent.utils.ats_utils import ATSUtils


LOGGER = logging.getLogger(__name__)


class JDUtils:

    def __init__(
        self,
        ats_utils: ATSUtils | None = None,
        context_provider: Callable[..., str] | None = None,
    ):
        self.ats = ats_utils or ATSUtils()
        self._context = context_provider

    def _jd_result(
        self,
        job_description: str,
        filename: str | None,
    ) -> dict[str, Any]:

        if not job_description.strip():
            raise ValueError(
                "A non-empty job description is required."
            )

        if self._context is None:
            raise RuntimeError(
                "A context provider is required."
            )

        resume_text = self._context(
            "skills experience projects education objective",
            filename=filename,
        )

        resume_sections = self.ats.section_maker(
            resume_text,
            self.ats.section_map,
        )

        resume_sections = self.ats.section_clean(
            resume_sections,
        )

        jd_sections = self.ats.section_maker(
            job_description,
            self.ats.section_map,
        )

        jd_sections = self.ats.section_clean(
            jd_sections,
        )

        weighted_sections = {
            key: [value]
            if isinstance(value, str)
            else value
            for key, value in resume_sections.items()
        }

        weighted = self.ats.resume_weight(
            weighted_sections,
        )

        jd_text = (
            self.ats.text_jd(jd_sections)
            or job_description
        )

        overall = self.ats.compute_similarity(
            weighted or resume_text,
            jd_text,
        )

        resume_skills = self.ats.normalize_skills(
            resume_sections.get("skills", ""),
        )

        jd_skills = self.ats.normalize_skills(
            jd_sections.get("skills", "")
            or job_description,
        )

        matched = resume_skills & jd_skills
        missing = jd_skills - resume_skills

        skills = (
            self.ats.compute_similarity(
                resume_sections.get("skills", ""),
                jd_sections.get("skills", "")
                or job_description,
            )
            if resume_skills
            else 0.0
        )

        final = (
            0.6 * skills
            + 0.4 * overall
        )

        verdict, _, feedback = self.ats.ai_feedback(
            overall,
            skills,
            matched,
            missing,
        )

        return {
            "filename": filename,
            "overall_match": round(
                overall * 100,
                2,
            ),
            "skills_match": round(
                skills * 100,
                2,
            ),
            "final_match": round(
                final * 100,
                2,
            ),
            "matched_skills": sorted(matched),
            "missing_skills": sorted(missing),
            "verdict": verdict,
            "feedback": feedback,
            "evidence": resume_text,
        }