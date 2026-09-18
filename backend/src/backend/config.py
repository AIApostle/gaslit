from dataclasses import dataclass
from os import getenv


@dataclass(frozen=True)
class Settings:
    database_path: str = getenv("DATABASE_PATH", "case_management.db")
    agent_key: str | None = getenv("SWIFTAGENTS_AGENT_KEY")
    staff_key: str | None = getenv("STAFF_API_KEY")
    swiftagents_webhook_url: str | None = getenv("SWIFTAGENTS_WEBHOOK_URL")
    swiftagents_company_id: str | None = getenv("SWIFTAGENTS_COMPANY_ID")
    swiftagents_public_key: str | None = getenv("SWIFTAGENTS_PUBLIC_KEY")


settings = Settings()
