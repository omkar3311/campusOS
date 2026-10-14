import textwrap
from pathlib import Path

from resume_agent.guardrails.guardrails import GuardrailViolation
from resume_agent.agent import ResumeAgent
from resume_agent.logging.logger import LOGGER

def main():

    print("=" * 60)
    print("Resume Agent v2")
    print("=" * 60)

    # resume_input = input(
    #     "\nEnter resume path(s)\n"
    #     "(For multiple resumes separate with commas)\n\n> "
    # ).strip()
    resume_input = str(Path(__file__).resolve().parents[2] / "omkar2.pdf")

    if not resume_input:
        print("No resume path provided.")
        return

    resume_paths = [
        path.strip()
        for path in resume_input.split(",")
        if path.strip()
    ]

    agent = ResumeAgent()

    try:
        loaded,docs = agent.load_resume(resume_paths)
        

    except Exception as e:
        print(f"\nFailed to load resume(s):\n{e}")
        return

    print("\nLoaded resumes:")

    for resume in loaded:
        print(f"  • {resume}")

    print("\nYou can now ask resume-related questions.")
    print("Type 'exit' to quit.\n")

    while True:

        question = input("\nYou > ").strip()

        if question.lower() in ("exit", "quit"):
            break

        if not question:
            continue

        job_description = None

        if any(
            word in question.lower()
            for word in (
                "jd",
                "job description",
                "eligibility",
                "match",
                "skill gap",
                "placement",
                "compare",
            )
        ):

            print("\nPaste Job Description.")
            print("Type END on a new line when finished.\n")

            lines = []

            while True:

                line = input()

                if line.strip() == "END":
                    break

                lines.append(line)

            job_description = "\n".join(lines)

        try:

            answer = agent.ask(
                question=question,
                job_description=job_description,
            )

            print("\nAssistant:\n")
            print(
                textwrap.fill(
                    answer,
                    width=100,
                )
            )

        except GuardrailViolation as e:

            print(
                f"\nRequest blocked:\n{e}"
            )

        except Exception as e:

            print(
                f"\nError:\n{e}"
            )


if __name__ == "__main__":
    main()
    
    
"""
uv run python -m resume_agent.runner

"""

