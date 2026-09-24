from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field, field_validator


class CaseStage(StrEnum):
    REPORTED = "reported"
    UNDER_INVESTIGATION = "under_investigation"
    RESPONSE_ISSUED = "response_issued"
    RESOLVED = "resolved"
    ESCALATED = "escalated"


class ContactChannel(StrEnum):
    SMS = "sms"
    EMAIL = "email"
    WHATSAPP = "whatsapp"
    PHONE = "phone"
    IN_BROWSER_CHAT = "in_browser_chat"
    CHAT = "chat"


class SlaStatus(StrEnum):
    ON_TRACK = "on_track"
    AT_RISK = "at_risk"
    BREACHED = "breached"
    RESOLVED = "resolved"


class ComplaintIntake(BaseModel):
    complainant_name: str = Field(default="Community Member", min_length=1, max_length=160)
    contact_value: str = Field(default="in-app-session", min_length=1, max_length=160)
    preferred_channel: ContactChannel = ContactChannel.IN_BROWSER_CHAT
    category: str = Field(default="Environmental Grievance", min_length=2, max_length=100)
    description: str = Field(min_length=3, max_length=5000)
    location: str = Field(default="Host Community Sector", min_length=1, max_length=240)
    occurred_at: datetime | None = None
    source_channel: str = Field(default="web", max_length=40)
    priority: str = Field(default="normal", pattern="^(low|normal|high|critical)$")

    @field_validator("contact_value")
    @classmethod
    def normalize_contact(cls, value: str) -> str:
        return value.strip().lower()


class SwiftAgentComplaintInput(BaseModel):
    complainant_name: str = Field(default="Community Member", min_length=1, max_length=160)
    contact_value: str = Field(default="in-app-session", min_length=1, max_length=160)
    preferred_channel: ContactChannel = ContactChannel.IN_BROWSER_CHAT
    category: str = Field(default="Environmental Grievance", min_length=2, max_length=100)
    description: str = Field(min_length=3, max_length=5000)
    location: str = Field(default="Host Community Site", min_length=1, max_length=240)
    occurred_at: datetime | None = None
    priority: str = Field(default="normal", pattern="^(low|normal|high|critical)$")


class StaffLoginRequest(BaseModel):
    key: str = Field(min_length=1)


class SwiftAgentToolResponse(BaseModel):
    ticket_id: str
    status: str
    verification_code: str
    message: str
    badge: dict[str, str]


class SwiftAgentCaseLookupInput(BaseModel):
    reference: str = Field(min_length=3, max_length=60)
    verification_code: str | None = Field(default=None, max_length=40)


class SwiftAgentCaseLookupResponse(BaseModel):
    found: bool
    reference: str
    stage: str
    category: str
    location: str
    assigned_officer: str | None = None
    sla_status: str
    sla_due_at: datetime | None = None
    latest_update: str | None = None
    summary_markdown: str


class SwiftAgentEvidenceInput(BaseModel):
    reference: str = Field(min_length=3, max_length=60)
    file_name: str = Field(min_length=2, max_length=240)
    evidence_type: str = Field(default="photo", max_length=80)
    storage_uri: str | None = Field(default=None, max_length=500)
    description: str | None = Field(default=None, max_length=1000)


class SwiftAgentEvidenceResponse(BaseModel):
    success: bool
    evidence_id: str
    reference: str
    message: str


class SwiftAgentHandoffInput(BaseModel):
    reference: str | None = Field(default=None, max_length=60)
    citizen_name: str = Field(default="Community Member", max_length=160)
    contact_value: str = Field(default="in-app-session", max_length=160)
    reason: str = Field(min_length=3, max_length=2000)
    urgency: str = Field(default="high", pattern="^(normal|high|critical)$")


class SwiftAgentHandoffResponse(BaseModel):
    handoff_id: str
    status: str
    message: str


class CaseTransition(BaseModel):
    stage: CaseStage
    note: str | None = Field(default=None, max_length=2000)
    response_summary: str | None = Field(default=None, max_length=5000)
    resolution_summary: str | None = Field(default=None, max_length=5000)


class CaseAssignment(BaseModel):
    assigned_officer: str = Field(min_length=2, max_length=160)


class CaseSummary(BaseModel):
    id: str
    reference: str
    category: str
    location: str
    stage: CaseStage
    priority: str
    assigned_officer: str | None
    created_at: datetime
    updated_at: datetime
    age_hours: float = 0
    sla_status: SlaStatus = SlaStatus.ON_TRACK
    sla_warning_at: datetime | None = None
    sla_due_at: datetime | None = None


class CaseDetail(CaseSummary):
    complainant_name: str
    contact_value: str
    preferred_channel: ContactChannel
    description: str
    occurred_at: datetime | None
    source_channel: str
    response_summary: str | None
    resolution_summary: str | None
    resolved_at: datetime | None
    status_verification_code: str | None = None


class EventView(BaseModel):
    event_type: str
    actor: str
    occurred_at: datetime
    metadata: dict[str, Any]


class CaseWithTimeline(BaseModel):
    case: CaseDetail
    events: list[EventView]


class StatusLookup(BaseModel):
    reference: str = Field(min_length=6, max_length=40)
    verification_code: str | None = Field(default=None, min_length=3, max_length=20)
    contact_value: str | None = Field(default=None, min_length=4, max_length=160)

    @field_validator("contact_value")
    @classmethod
    def normalize_contact(cls, value: str | None) -> str | None:
        return value.strip().lower() if value else value


class PublicCaseStatus(BaseModel):
    reference: str
    stage: CaseStage
    status_message: str
    updated_at: datetime
    sla_status: SlaStatus


class InvestigationNoteCreate(BaseModel):
    note: str = Field(min_length=3, max_length=5000)


class InvestigationNoteView(BaseModel):
    id: str
    case_id: str
    note: str
    actor: str
    created_at: datetime


class EvidenceCreate(BaseModel):
    file_name: str = Field(min_length=2, max_length=240)
    evidence_type: str = Field(default="document", max_length=80)
    description: str | None = Field(default=None, max_length=1000)
    storage_uri: str | None = Field(default=None, max_length=500)


class EvidenceView(BaseModel):
    id: str
    case_id: str
    file_name: str
    evidence_type: str
    description: str | None
    storage_uri: str | None
    actor: str
    created_at: datetime


class NotificationView(BaseModel):
    id: str
    case_id: str
    event_type: str
    channel: ContactChannel
    recipient: str
    message: str
    status: str
    attempts: int
    created_at: datetime
    last_attempt_at: datetime | None
    error_message: str | None


class CaseExport(BaseModel):
    case: CaseDetail
    events: list[EventView]
    notes: list[InvestigationNoteView]
    evidence: list[EvidenceView]
    notifications: list[NotificationView]


class PortfolioReport(BaseModel):
    total_cases: int
    open_cases: int
    resolved_cases: int
    unassigned_cases: int
    escalated_cases: int
    at_risk_cases: int
    breached_cases: int
    by_stage: dict[str, int]
    by_priority: dict[str, int]
    by_category: dict[str, int]


class HandoffView(BaseModel):
    id: str
    case_id: str
    event_type: str
    status: str
    attempts: int
    created_at: datetime
    last_attempt_at: datetime | None
    error_message: str | None
