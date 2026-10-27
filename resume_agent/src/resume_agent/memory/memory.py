from dotenv import load_dotenv
from langchain_groq import ChatGroq
import logging


LOGGER = logging.getLogger(__name__)


class Profile:

    def __init__(self):
        self.profile = None

    def make_profile(
        self,
        candidate_name: str,
        resume_context: str,
    ) -> str:
        self.profile = {
            "candidate_name": candidate_name,
            "profile": resume_context.strip(),
        }

        LOGGER.info(
            f"Profile created for {candidate_name}"
        )

        return self.profile["profile"]

    def get_profile(
        self,
        candidate_name: str,
    ) -> str | None:

        LOGGER.info(
            f"Retrieving profile for {candidate_name}"
        )

        if (
            self.profile
            and self.profile.get("candidate_name")
            == candidate_name
        ):
            return self.profile["profile"]

        return None


class SessionSummarizer:

    SYSTEM_PROMPT = """
You are the session memory summarizer for the CampusOS ResumeIQ Agent.

Your job is to maintain a short, accurate story of the current conversation so a future LLM can understand what happened earlier without seeing the full chat.

You receive:
1. Previous session memory, if available.
2. Latest user message.
3. Latest assistant response.

Update the previous memory with the new information.

IMPORTANT:
- Preserve explicit facts stated by the user.
- Always preserve names of people and relationships.
- Preserve user preferences, decisions, plans, important requests, and unresolved questions.
- If the user says "My friend is Om", remember that the user's friend is named Om.
- Do not remove an important fact just because it was mentioned only once.
- Connect related facts so the memory reads naturally as a short story.
- Keep the chronology/context clear when useful.
- Do not invent or assume information.

Do NOT store:
- greetings or filler
- repeated information
- full resume content
- full job descriptions
- tool calls or tool execution details
- unnecessary explanations
- information already available from profile/resume memory unless it is important to the conversation

The memory should be concise but complete enough for a future LLM to understand the conversation.

Example:

User: "My friend name is Om. He wants to know about me."

Memory:
"The user has a friend named Om. The user wants to share information about their background with Om."

Later:

User: "Give me a short introduction for him."

Updated memory:
"The user has a friend named Om and wants to share a short introduction about their background with him. The user previously requested help preparing this introduction."

Return ONLY the updated session memory. Do not add explanations or headings.
"""

    def __init__(self):
        load_dotenv()

        self.client = ChatGroq(
            model="openai/gpt-oss-20b",
            temperature=0.2,
        )

    def summarize(
        self,
        previous_summary: str | None,
        user_message: str,
        assistant_response: str,
    ) -> str:

        previous_summary = (
            previous_summary
            or "No previous session summary."
        )

        prompt = f"""
Previous session summary:
{previous_summary}

Latest user message:
{user_message}

Latest assistant response:
{assistant_response}
"""

        try:
            response = self.client.invoke(
                [
                    {
                        "role": "system",
                        "content": self.SYSTEM_PROMPT,
                    },
                    {
                        "role": "user",
                        "content": prompt,
                    },
                ]
            )

            LOGGER.info(
                "Session memory summarized successfully."
            )

            return response.content.strip()

        except Exception as e:
            LOGGER.error(
                f"Error summarizing session memory: {e}"
            )
            raise


class SessionMemory:

    def __init__(self):
        self.session_memory: str | None = None
        self.summarizer = SessionSummarizer()

    def set_session_memory(
        self,
        user_message: str,
        assistant_response: str,
    ) -> str:

        self.session_memory = (
            self.summarizer.summarize(
                previous_summary=self.session_memory,
                user_message=user_message,
                assistant_response=assistant_response,
            )
        )

        return self.session_memory

    def get_session_memory(self) -> str | None:

        LOGGER.info(
            "Retrieved session memory."
        )

        return self.session_memory