import os

from dotenv import load_dotenv

load_dotenv()


class Settings:
    """Centralized configuration and environment validation."""

    OPENAI_API_KEY: str | None = os.getenv("OPENAI_API_KEY")
    GEMINI_API_KEY: str | None = os.getenv("GEMINI_API_KEY")

    # Azure Specifics
    AZURE_OPENAI_API_KEY: str | None = os.getenv("AZURE_OPENAI_API_KEY")
    AZURE_OPENAI_ENDPOINT: str | None = os.getenv("AZURE_OPENAI_ENDPOINT")
    AZURE_OPENAI_API_VERSION: str | None = os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-01")
    AZURE_OPENAI_CHAT_DEPLOYMENT_NAME: str | None = os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT_NAME")

    DATABASE_URI: str = os.getenv("DATABASE_URI", "postgresql://admin:securepassword@localhost:5432/supply_chain_audit")

    LANGCHAIN_TRACING_V2: str | None = os.getenv("LANGCHAIN_TRACING_V2", "false")

    # We will dynamically set this during validation
    ACTIVE_LLM_PROVIDER: str = "unknown"

    @classmethod
    def validate_core_settings(cls) -> None:
        """Fails fast if critical infrastructure keys are missing and sets the active provider."""
        if not cls.OPENAI_API_KEY and not cls.GEMINI_API_KEY and not cls.AZURE_OPENAI_API_KEY:
            raise ValueError("[FATAL] You must provide credentials for OpenAI, Gemini, or Azure in the .env file.")

        # Determine which provider to use based on available keys
        if cls.OPENAI_API_KEY:
            cls.ACTIVE_LLM_PROVIDER = "openai"
        elif cls.GEMINI_API_KEY:
            cls.ACTIVE_LLM_PROVIDER = "gemini"
        elif cls.AZURE_OPENAI_API_KEY:
            if not cls.AZURE_OPENAI_ENDPOINT or not cls.AZURE_OPENAI_CHAT_DEPLOYMENT_NAME:
                raise ValueError("[FATAL] Azure OpenAI requires an ENDPOINT and a CHAT_DEPLOYMENT_NAME.")
            cls.ACTIVE_LLM_PROVIDER = "azure"


settings = Settings()
