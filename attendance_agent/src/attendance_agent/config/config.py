import os

from dotenv import load_dotenv


load_dotenv()


class Settings:
    """Application configuration."""

    SUPABASE_URL: str = os.getenv(
        "SUPABASE_URL",
        "",
    )

    SUPABASE_KEY: str = os.getenv(
        "SUPABASE_KEY",
        "",
    )

    # -----------------------------------------
    # Groq
    # -----------------------------------------

    GROQ_API_KEY: str = os.getenv(
        "GROQ_API_KEY",
        "",
    )

    GROQ_API_KEY0: str = os.getenv(
        "GROQ_API_KEY0",
        "",
    )

    GROQ_MODEL: str = os.getenv(
        "GROQ_MODEL",
        "qwen/qwen3.6-27b",
    )

    # -----------------------------------------
    # Gemini
    # -----------------------------------------

    GEMINI_API_KEY: str = os.getenv(
        "GEMINI_API_KEY",
        "",
    )

    GEMINI_MODEL: str = os.getenv(
        "GEMINI_MODEL",
        "gemini-2.5-flash",
    )

    # -----------------------------------------
    # Logging
    # -----------------------------------------

    LOG_LEVEL: str = os.getenv(
        "LOG_LEVEL",
        "INFO",
    )

    @classmethod
    def validate(cls) -> None:
        """
        Validate required environment variables.

        At least one LLM provider must be configured.
        """

        required_database = {
            "SUPABASE_URL": cls.SUPABASE_URL,
            "SUPABASE_KEY": cls.SUPABASE_KEY,
        }

        missing_database = [
            name
            for name, value
            in required_database.items()
            if not value
        ]

        if missing_database:
            raise RuntimeError(
                "Missing required environment variables: "
                + ", ".join(
                    missing_database
                )
            )

        llm_keys = [
            cls.GROQ_API_KEY,
            cls.GROQ_API_KEY0,
            cls.GEMINI_API_KEY,
        ]

        if not any(llm_keys):
            raise RuntimeError(
                "At least one LLM API key is required. "
                "Configure GROQ_API_KEY, GROQ_API_KEY0, "
                "or GEMINI_API_KEY."
            )


settings = Settings()