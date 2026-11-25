"""Application configuration using Pydantic Settings.

Loads from environment variables and .env file with validation.
"""

from functools import lru_cache
from urllib.parse import urlparse

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── App ──────────────────────────────────────
    app_name: str = "ResearchScout"
    app_env: str = "development"
    debug: bool = True
    secret_key: str = "change-me-to-a-random-secret-key-at-least-32-chars"
    admin_api_key: str = ""
    api_host: str = "0.0.0.0"
    api_port: int = 8000

    # ── PostgreSQL ───────────────────────────────
    database_url: str = "sqlite+aiosqlite:///./researchscout.db"

    # ── Redis ────────────────────────────────────
    redis_url: str = "redis://localhost:6379/0"
    celery_broker_url: str = "redis://localhost:6379/1"
    celery_result_backend: str = "redis://localhost:6379/2"

    # ── Qdrant ───────────────────────────────────
    qdrant_url: str = "http://localhost:6333"

    # ── Neo4j ────────────────────────────────────
    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = "researchscout_neo4j"

    # ── MinIO ────────────────────────────────────
    minio_host: str = "localhost"
    minio_port: int = 9000
    minio_root_user: str = "minioadmin"
    minio_root_password: str = "minioadmin"
    minio_bucket: str = "researchscout"

    # ── LLM APIs ─────────────────────────────────
    openai_api_key: str = ""
    google_api_key: str = ""
    google_oauth_client_id: str = ""
    anthropic_api_key: str = ""

    # ── Embedding ────────────────────────────────
    embedding_model: str = "text-embedding-3-large"
    embedding_dimensions: int = 3072

    # ── Search APIs ──────────────────────────────
    google_cse_api_key: str = ""
    google_cse_cx: str = ""
    bing_search_api_key: str = ""
    tavily_api_key: str = ""
    serpapi_api_key: str = ""

    # ── Notifications ────────────────────────────
    sendgrid_api_key: str = ""
    sendgrid_from_email: str = "notifications@researchscout.io"
    telegram_bot_token: str = ""
    discord_webhook_url: str = ""

    # ── Auth ─────────────────────────────────────
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 30
    jwt_refresh_token_expire_days: int = 7

    # ── Crawling ─────────────────────────────────
    crawler_user_agent: str = "ResearchScoutBot/1.0 (+https://researchscout.io/bot)"
    crawler_default_rate_limit: float = 1.0
    crawler_max_concurrent: int = 10
    crawler_timeout_seconds: int = 30
    cors_origins: list[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]
    crawl_allow_private_networks: bool = False

    @model_validator(mode="after")
    def validate_production_settings(self):
        self.app_env = self.app_env.lower()
        if self.app_env.lower() == "production":
            if self.secret_key.startswith("change-me") or len(self.secret_key) < 32:
                raise ValueError(
                    "SECRET_KEY must be a unique random value of at least 32 "
                    "characters in production"
                )
            if len(self.admin_api_key) < 32:
                raise ValueError(
                    "ADMIN_API_KEY must be a unique random value of at least 32 "
                    "characters in production"
                )
            if not self.cors_origins or any(
                "localhost" in origin or "127.0.0.1" in origin for origin in self.cors_origins
            ):
                raise ValueError(
                    "CORS_ORIGINS must contain deployed frontend origins in production"
                )
            if urlparse(self.database_url).hostname in {None, "localhost", "127.0.0.1"}:
                raise ValueError("DATABASE_URL must point to the production database")
        return self

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"


@lru_cache
def get_settings() -> Settings:
    """Cached settings singleton."""
    return Settings()
