"""Centralised configuration loaded from environment variables / .env."""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Database
    database_url: str = "postgresql+asyncpg://postgres:postgres@postgres:5432/echobrief"

    # Kafka
    kafka_bootstrap_servers: str = "kafka:9092"
    kafka_topic_transcribe: str = "echobrief.transcribe"
    kafka_topic_structure: str = "echobrief.structure"
    kafka_consumer_group: str = "echobrief-workers"

    # LLM (OpenRouter, OpenAI-compatible)
    openrouter_api_key: str = ""
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    openrouter_model: str = "anthropic/claude-3.5-sonnet"

    # Where uploaded audio files are stored
    upload_dir: str = "/app/uploads"

    @property
    def asyncpg_dsn(self) -> str:
        """DATABASE_URL stripped of the SQLAlchemy driver suffix for raw asyncpg."""
        return self.database_url.replace("+asyncpg", "")

    @property
    def llm_enabled(self) -> bool:
        key = self.openrouter_api_key.strip()
        return bool(key) and key != "your_openrouter_api_key_here"


settings = Settings()
