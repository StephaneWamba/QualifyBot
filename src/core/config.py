"""Application configuration."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings."""

    # Environment
    ENVIRONMENT: str = "development"
    DEBUG: bool = False

    # API
    API_V1_PREFIX: str = "/api/v1"
    CORS_ORIGINS: list[str] = ["*"]

    # Twilio
    TWILIO_ACCOUNT_SID: str = ""
    TWILIO_AUTH_TOKEN: str = ""
    TWILIO_PHONE_NUMBER: str = ""
    TWILIO_WEBHOOK_URL: str = ""

    # OpenAI
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4o-mini"

    # ElevenLabs
    ELEVENLABS_API_KEY: str = ""
    ELEVENLABS_VOICE_ID: str = "21m00Tcm4TlvDq8ikWAM"  # Default voice

    # Salesforce
    SALESFORCE_USERNAME: str = ""
    SALESFORCE_PASSWORD: str = ""
    SALESFORCE_SECURITY_TOKEN: str = ""
    SALESFORCE_DOMAIN: str = "login"  # or "test" for sandbox

    # Redis
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6383
    REDIS_DB: int = 0
    REDIS_PASSWORD: str | None = None
    REDIS_URL: str | None = None  # Railway provides this

    # PostgreSQL
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5436
    POSTGRES_USER: str = "qualifybot"
    POSTGRES_PASSWORD: str = "qualifybot"
    POSTGRES_DB: str = "qualifybot"
    DATABASE_URL: str | None = None  # Railway provides this

    # Sentry
    SENTRY_DSN: str | None = None
    SENTRY_ENVIRONMENT: str = "development"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    @property
    def database_url(self) -> str:
        """Get database URL."""
        # Railway provides DATABASE_URL directly
        if self.DATABASE_URL:
            # Ensure it uses asyncpg driver
            if self.DATABASE_URL.startswith("postgresql://"):
                return self.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)
            return self.DATABASE_URL
        
        # For Docker, use port 5432 (internal), for local use configured port
        import os
        # Check if we're in Docker (POSTGRES_HOST is 'postgres' or 'redis')
        postgres_host = os.getenv("POSTGRES_HOST", self.POSTGRES_HOST)
        if postgres_host in ("postgres", "localhost") and postgres_host == "postgres":
            # Inside Docker - use internal port 5432
            postgres_port = 5432
        else:
            # Local development - use configured port
            postgres_port = int(os.getenv("POSTGRES_PORT", self.POSTGRES_PORT))
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{postgres_host}:{postgres_port}/{self.POSTGRES_DB}"
        )

    @property
    def redis_url(self) -> str:
        """Get Redis URL."""
        # Railway provides REDIS_URL directly
        if self.REDIS_URL:
            return self.REDIS_URL
        
        import os
        # Check if we're in Docker (REDIS_HOST is 'redis')
        redis_host = os.getenv("REDIS_HOST", self.REDIS_HOST)
        if redis_host == "redis":
            # Inside Docker - use internal port 6379
            redis_port = 6379
        else:
            # Local development - use configured port
            redis_port = int(os.getenv("REDIS_PORT", self.REDIS_PORT))
        
        if self.REDIS_PASSWORD:
            return f"redis://:{self.REDIS_PASSWORD}@{redis_host}:{redis_port}/{self.REDIS_DB}"
        return f"redis://{redis_host}:{redis_port}/{self.REDIS_DB}"


settings = Settings()

