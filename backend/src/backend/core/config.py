from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    app_name: str = "Host Community Case Management API"
    app_version: str = "0.1.0"
    debug: bool = False
    environment: str = "development"

    # Database
    database_url: str = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:5432/case_management",
        description="PostgreSQL async connection URL",
    )
    database_pool_size: int = 10
    database_max_overflow: int = 20
    database_pool_timeout: int = 30

    # Redis
    redis_url: str = Field(
        default="redis://localhost:6379/0",
        description="Redis connection URL for caching and job queue",
    )

    # Security
    secret_key: str = Field(
        default="change-me-in-production-use-a-strong-random-secret",
        description="Secret key for JWT signing",
    )
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7

    # CORS
    cors_origins: list[str] = Field(
        default=["http://localhost:3000", "http://localhost:5173"],
        description="Allowed CORS origins",
    )

    # SwiftAgents Integration
    swiftagents_agent_key: str | None = Field(default=None, description="SwiftAgents agent API key")
    swiftagents_webhook_url: str | None = Field(default=None, description="SwiftAgents webhook URL")
    swiftagents_company_id: str | None = Field(default=None, description="SwiftAgents company ID")
    swiftagents_public_key: str | None = Field(default=None, description="SwiftAgents public key")

    # Staff API Key (for simple API key auth)
    staff_api_key: str | None = Field(default=None, description="Staff API key for service-to-service auth")

    # Notification Provider (placeholder)
    notification_provider: str = Field(default="mock", description="Notification provider: mock, twilio, sendgrid, etc.")
    notification_api_key: str | None = None
    notification_from_number: str | None = None
    notification_from_email: str | None = None

    # File Storage
    storage_provider: str = Field(default="local", description="Storage provider: local, s3, minio")
    storage_bucket: str = Field(default="case-evidence")
    storage_region: str = Field(default="us-east-1")
    storage_access_key: str | None = None
    storage_secret_key: str | None = None
    storage_endpoint_url: str | None = None

    # Logging
    log_level: str = Field(default="INFO", description="Logging level")
    log_format: str = Field(default="json", description="Log format: json or console")

    # Rate Limiting
    rate_limit_requests: int = Field(default=100, description="Requests per window")
    rate_limit_window_seconds: int = Field(default=60, description="Rate limit window in seconds")

    # Pagination
    default_page_size: int = 20
    max_page_size: int = 100


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()