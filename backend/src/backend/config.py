from pathlib import Path
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(
            str(Path(__file__).resolve().parents[2] / ".env"),
            str(Path(__file__).resolve().parents[3] / ".env"),
            ".env",
        ),
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )

    database_path: str = Field(default="case_management.db", alias="DATABASE_PATH")
    database_url: str | None = Field(default=None, alias="DATABASE_URL")
    neon_api_key: str | None = Field(default=None, alias="NEON_API_KEY")

    # SwiftAgents Integration
    swiftagents_company_id: str | None = Field(default=None, alias="SWIFTAGENTS_COMPANY_ID")
    swiftagents_public_key: str | None = Field(default=None, alias="SWIFTAGENTS_PUBLIC_KEY")
    agent_key: str | None = Field(default=None, alias="SWIFTAGENTS_AGENT_KEY")
    swiftagents_webhook_url: str | None = Field(default=None, alias="SWIFTAGENTS_WEBHOOK_URL")

    # Staff API Secret
    staff_key: str | None = Field(default=None, alias="STAFF_API_KEY")

    @property
    def effective_database_url(self) -> str:
        if self.database_url:
            return self.database_url
        return f"sqlite+aiosqlite:///{self.database_path}"


settings = Settings()
