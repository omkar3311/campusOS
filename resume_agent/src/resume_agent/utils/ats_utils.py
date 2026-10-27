import re

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


class ATSUtils:
    """
    Utility class for resume parsing, ATS scoring,
    skill matching, section handling, and feedback.
    """

    def __init__(self):
        self.section_map = {
            "objective": "objective",
            "summary": "objective",

            "experience": "experience",
            "work experience": "experience",
            "professional experience": "experience",
            "internships": "experience",

            "projects": "projects",
            "academic projects": "projects",

            "required skills": "skills",
            "preferred skills": "skills",
            "skills": "skills",
            "technical skills": "skills",

            "education": "education",
            "awards": "awards",
            "certifications": "certifications",
        }

    @staticmethod
    def clean_text(text):
        """
        Clean extracted resume/JD text.
        """
        cleaned_text = re.sub(r"[•▪◦–—*]", "", text)
        cleaned_text = re.sub(
            r"page \d+ of \d+",
            "",
            cleaned_text,
            flags=re.I
        )
        cleaned_text = re.sub(r"\s+", " ", cleaned_text).strip()

        return cleaned_text

    def section_maker(self, text, section_map=None):
        """
        Convert resume text into structured sections.
        """

        if section_map is None:
            section_map = self.section_map

        lines = text.splitlines()
        sections = {}
        current_section = None

        for line in lines:
            line_clean = line.strip().lower()

            if line_clean in section_map:
                current_section = section_map[line_clean]

                if current_section not in sections:
                    sections[current_section] = []

            elif current_section:
                sections[current_section].append(line.strip())

        return sections

    def section_clean(self, sections):
        """
        Clean all extracted resume sections.
        """

        for key, value in sections.items():
            sections[key] = self.clean_text(" ".join(value))

        return sections

    def resume_weight(self, sections):
        """
        Give more weight to important resume sections
        for semantic comparison.
        """

        skills = sections.get("skills", [])
        experience = sections.get("experience", [])
        projects = sections.get("projects", [])
        objective = sections.get("objective", [])
        education = sections.get("education", [])

        resume_text = "".join(
            (" ".join(skills) + " ") * 3
            + (" ".join(experience) + " ") * 2
            + (" ".join(projects) + " ") * 2
            + " ".join(objective)
            + " "
            + " ".join(education)
        )

        return resume_text

    def text_jd(self, sections):
        """
        Convert JD sections into a single text string.
        """

        text = ""

        for key, value in sections.items():
            text = text + value + " "

        return text

    @staticmethod
    def compute_similarity(resume, jd):
        """
        Calculate TF-IDF cosine similarity between
        resume and job description.
        """

        try:
            vectorizer = TfidfVectorizer()
            vectors = vectorizer.fit_transform([resume, jd])

            return cosine_similarity(
                vectors[0],
                vectors[1]
            )[0][0]

        except ValueError:
            return 0.0

    @staticmethod
    def normalize_skills(text):
        """
        Normalize text so skills can be compared consistently.
        """

        text = text.lower()

        text = re.sub(
            r"[()\[\]{}/]",
            " ",
            text
        )

        text = re.sub(
            r"[^a-z0-9+.#\- ]",
            " ",
            text
        )

        text = re.sub(
            r"\s+",
            " ",
            text
        ).strip()

        skills = set(
            skill.strip()
            for skill in text.split()
            if len(skill) > 2
        )

        return skills

    @staticmethod
    def has_email(text):
        return re.search(
            r"[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,}",
            text,
            re.I
        )

    @staticmethod
    def has_phone(text):
        return re.search(
            r"\b\d{10}\b",
            text
        )

    @staticmethod
    def has_experience(text):
        return (
            "experience" in text.lower()
            or "internship" in text.lower()
        )

    @staticmethod
    def graduation_year(text):
        years = re.findall(
            r"(20\d{2})",
            text
        )

        return max(map(int, years)) if years else None

    def count_projects(self, project_lines):
        """
        Estimate number of projects in the Projects section.
        """

        if not project_lines:
            return 0

        project_count = 0
        detected_titles = 0
        bullet_blocks = 0

        def looks_like_title(line):
            return (
                2 <= len(line.split()) <= 10
                and not line.endswith(".")
                and not line.lower().startswith(
                    (
                        "tech",
                        "tools",
                        "description",
                        "responsibilities",
                    )
                )
            )

        for line in project_lines:

            line = line.strip()

            if not line:
                continue

            if re.match(r"^\d+\.", line):
                detected_titles += 1
                continue

            if "|" in line or ":" in line:
                detected_titles += 1
                continue

            if looks_like_title(line):
                detected_titles += 1
                continue

            if re.match(r"^[•\-*]", line):
                bullet_blocks += 1

        if detected_titles > 0:
            project_count = detected_titles

        elif bullet_blocks >= 2:
            project_count = max(
                1,
                bullet_blocks // 2
            )

        else:
            project_count = 0

        return min(project_count, 5)

    def evaluate_resume_structure(self, sections):
        """
        Check whether essential resume sections exist.
        """

        feedback = []

        expected_sections = [
            "skills",
            "projects",
            "education",
            "experience",
            "objective",
        ]

        detected_sections = list(sections.keys())

        missing_sections = [
            section
            for section in expected_sections
            if section not in detected_sections
        ]

        if len(missing_sections) >= 3:

            feedback.append(
                "Resume structure is very weak. "
                "Missing multiple essential sections: "
                + ", ".join(missing_sections)
            )

        elif missing_sections:

            feedback.append(
                "Resume structure can be improved. "
                "Missing sections: "
                + ", ".join(missing_sections)
            )

        return (
            feedback,
            detected_sections,
            missing_sections,
        )


    def ats_score(self, resume_text, sections):
        """
        Calculate ATS score and return feedback.
        """

        feedback = []
        score = 0

        if not sections or len(sections.keys()) == 0:
            return (
                0,
                [
                    "No resume sections detected. "
                    "Please structure your resume with clear "
                    "headings like Skills, Projects, Education, "
                    "and Experience."
                ],
            )

        # Email
        if self.has_email(resume_text):
            score += 5
        else:
            feedback.append(
                "Add a professional email address."
            )

        # Phone
        if self.has_phone(resume_text):
            score += 5
        else:
            feedback.append(
                "Add a valid mobile number."
            )

        # Skills
        if sections.get("skills"):
            score += 20
        else:
            feedback.append(
                "Skills section is missing."
            )

        # Projects
        if sections.get("projects"):

            score += 15

            project_count = self.count_projects(
                sections["projects"]
            )

            if project_count >= 3:
                score += 10

            elif project_count == 2:
                score += 7

            elif project_count == 1:
                score += 4

            else:
                score += 5

        else:
            feedback.append(
                "Projects section not found."
            )

        # Graduation year
        if self.graduation_year(resume_text):
            score += 15
        else:
            feedback.append(
                "Mention your graduation year clearly."
            )

        # Experience
        if sections.get("experience"):

            score += 15

            if self.has_experience(resume_text):
                score += 8
            else:
                score += 5

        else:
            feedback.append(
                "No experience section found."
            )

        # Objective
        if sections.get("objective"):
            score += 5

        # Structure
        (
            structure_feedback,
            detected_sections,
            missing_sections,
        ) = self.evaluate_resume_structure(sections)

        feedback.extend(structure_feedback)

        return min(score, 100), feedback


    @staticmethod
    def ai_feedback(overall, skills, matched, missing):
        """
        Generate human-readable feedback based on
        skill matching.
        """

        if skills >= 0.75:

            verdict = "Strong Match"
            color = "green"
            tone = (
                "Your resume strongly aligns with this role."
            )

        elif skills >= 0.5:

            verdict = "Moderate Match"
            color = "orange"
            tone = (
                "You meet many requirements, "
                "but some skills are missing."
            )

        else:

            verdict = "Weak Match"
            color = "red"
            tone = (
                "Your resume currently lacks "
                "several key requirements."
            )

        feedback_text = ""

        feedback_text += f"\n{tone}\n"

        feedback_text += (
            "\n**Skill Analysis**\n"
        )

        feedback_text += (
            f"\n- Matched skills: {len(matched)}"
        )

        feedback_text += (
            f"\n- Missing skills: {len(missing)}\n"
        )

        if missing:

            feedback_text += (
                "\n**Recommended Skills to "
                "Improve or Highlight:**\n\n"
            )

            feedback_text += "\n".join(
                [
                    f"• {skill}  "
                    for skill in sorted(missing)
                ]
            )

        else:

            feedback_text += (
                "\n**Excellent** — "
                "no critical skills missing."
            )

        return (
            verdict,
            color,
            feedback_text,
        )