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

    # SwiftAgents Integration
    swiftagents_company_id: str = Field(default="e465b6dd-7f97-4fcd-bed2-737555796064", alias="SWIFTAGENTS_COMPANY_ID")
    swiftagents_public_key: str = Field(
        default="swa_live_0c61a7623c4e53abe3e87d542ad82ba86092e6f6018c4ab426f0f358385d1679",
        alias="SWIFTAGENTS_PUBLIC_KEY",
    )
    agent_key: str | None = Field(default=None, alias="SWIFTAGENTS_AGENT_KEY")
    swiftagents_webhook_url: str | None = Field(default=None, alias="SWIFTAGENTS_WEBHOOK_URL")

    # Staff API Secret
    staff_key: str | None = Field(default="123456", alias="STAFF_API_KEY")

    @property
    def effective_database_url(self) -> str:
        if self.database_url:
            # If explicit sqlite url provided, normalize driver
            if self.database_url.startswith("sqlite"):
                if self.database_url.startswith("sqlite:///") and not self.database_url.startswith("sqlite+aiosqlite:///"):
                    return self.database_url.replace("sqlite:///", "sqlite+aiosqlite:///")
                return self.database_url
            # If leftover Neon/Postgres connection string, fallback to SQLite
            if "neon" in self.database_url.lower() or "postgres" in self.database_url.lower():
                return f"sqlite+aiosqlite:///{self.database_path}"
            return self.database_url
        return f"sqlite+aiosqlite:///{self.database_path}"


settings = Settings()

