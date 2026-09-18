import sqlite3
from contextlib import contextmanager
from pathlib import Path

from .config import settings


SCHEMA = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS cases (
    id TEXT PRIMARY KEY,
    reference TEXT NOT NULL UNIQUE,
    status_verification_code TEXT NOT NULL DEFAULT '',
    complainant_name TEXT NOT NULL,
    contact_value TEXT NOT NULL,
    preferred_channel TEXT NOT NULL,
    category TEXT NOT NULL,
    description TEXT NOT NULL,
    location TEXT NOT NULL,
    occurred_at TEXT,
    source_channel TEXT NOT NULL,
    stage TEXT NOT NULL,
    priority TEXT NOT NULL,
    assigned_officer TEXT,
    response_summary TEXT,
    resolution_summary TEXT,
    sla_warning_at TEXT,
    sla_due_at TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    resolved_at TEXT
);

CREATE TABLE IF NOT EXISTS case_events (
    id TEXT PRIMARY KEY,
    case_id TEXT NOT NULL REFERENCES cases(id),
    event_type TEXT NOT NULL,
    actor TEXT NOT NULL,
    occurred_at TEXT NOT NULL,
    metadata_json TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS agent_handoffs (
    id TEXT PRIMARY KEY,
    case_id TEXT NOT NULL REFERENCES cases(id),
    event_type TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    status TEXT NOT NULL,
    attempts INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    last_attempt_at TEXT,
    error_message TEXT
);

CREATE TABLE IF NOT EXISTS investigation_notes (
    id TEXT PRIMARY KEY,
    case_id TEXT NOT NULL REFERENCES cases(id),
    note TEXT NOT NULL,
    actor TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS evidence (
    id TEXT PRIMARY KEY,
    case_id TEXT NOT NULL REFERENCES cases(id),
    file_name TEXT NOT NULL,
    evidence_type TEXT NOT NULL,
    description TEXT,
    storage_uri TEXT,
    actor TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS notification_events (
    id TEXT PRIMARY KEY,
    case_id TEXT NOT NULL REFERENCES cases(id),
    event_type TEXT NOT NULL,
    channel TEXT NOT NULL,
    recipient TEXT NOT NULL,
    message TEXT NOT NULL,
    status TEXT NOT NULL,
    attempts INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    last_attempt_at TEXT,
    error_message TEXT,
    idempotency_key TEXT NOT NULL UNIQUE
);

CREATE INDEX IF NOT EXISTS idx_cases_stage ON cases(stage);
CREATE INDEX IF NOT EXISTS idx_cases_reference ON cases(reference);
CREATE INDEX IF NOT EXISTS idx_cases_sla_due_at ON cases(sla_due_at);
CREATE INDEX IF NOT EXISTS idx_case_events_case_id ON case_events(case_id, occurred_at);
CREATE INDEX IF NOT EXISTS idx_agent_handoffs_status ON agent_handoffs(status);
CREATE INDEX IF NOT EXISTS idx_investigation_notes_case_id ON investigation_notes(case_id, created_at);
CREATE INDEX IF NOT EXISTS idx_evidence_case_id ON evidence(case_id, created_at);
CREATE INDEX IF NOT EXISTS idx_notification_events_status ON notification_events(status);
"""


def database_file() -> Path:
    return Path(settings.database_path)


@contextmanager
def connection():
    db = sqlite3.connect(database_file())
    db.row_factory = sqlite3.Row
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def initialize_database() -> None:
    with connection() as db:
        db.executescript(SCHEMA)
        migrate_database(db)


def migrate_database(db: sqlite3.Connection) -> None:
    columns = {row["name"] for row in db.execute("PRAGMA table_info(cases)").fetchall()}
    migrations = {
        "status_verification_code": "ALTER TABLE cases ADD COLUMN status_verification_code TEXT NOT NULL DEFAULT ''",
        "response_summary": "ALTER TABLE cases ADD COLUMN response_summary TEXT",
        "sla_warning_at": "ALTER TABLE cases ADD COLUMN sla_warning_at TEXT",
        "sla_due_at": "ALTER TABLE cases ADD COLUMN sla_due_at TEXT",
    }
    for column, statement in migrations.items():
        if column not in columns:
            db.execute(statement)
