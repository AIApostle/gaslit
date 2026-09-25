from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


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
    model_config = ConfigDict(extra="ignore")

    complainant_name: str = Field(default="Community Member", min_length=1, max_length=160)
    contact_value: str = Field(default="in-app-session", min_length=1, max_length=160)
    preferred_channel: ContactChannel = ContactChannel.IN_BROWSER_CHAT
    category: str = Field(default="Environmental Grievance", min_length=2, max_length=100)
    description: str = Field(default="Community grievance report", min_length=1, max_length=5000)
    location: str = Field(default="Host Community Sector", min_length=1, max_length=240)
    occurred_at: datetime | None = None
    source_channel: str = Field(default="web", max_length=40)
    priority: str = Field(default="normal")

    @field_validator("contact_value")
    @classmethod
    def normalize_contact(cls, value: str) -> str:
        return value.strip().lower()

    @model_validator(mode="before")
    @classmethod
    def normalize_intake(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        d = dict(data)
        raw_pri = str(d.get("priority", "normal")).strip().lower()
        pri_map = {
            "medium": "normal",
            "med": "normal",
            "moderate": "normal",
            "urgent": "critical",
            "emergency": "critical",
            "severe": "critical",
            "critical": "critical",
            "high": "high",
            "low": "low",
            "normal": "normal",
        }
        d["priority"] = pri_map.get(raw_pri, "normal")
        raw_occ = d.get("occurred_at")
        if isinstance(raw_occ, str):
            try:
                d["occurred_at"] = datetime.fromisoformat(raw_occ.replace("Z", "+00:00"))
            except Exception:
                d["occurred_at"] = None
        return d


class SwiftAgentComplaintInput(BaseModel):
    model_config = ConfigDict(extra="ignore")

    complainant_name: str = Field(default="Community Member", min_length=1, max_length=160)
    contact_value: str = Field(default="in-app-session", min_length=1, max_length=160)
    preferred_channel: ContactChannel = ContactChannel.IN_BROWSER_CHAT
    category: str = Field(default="Environmental Grievance", min_length=2, max_length=100)
    description: str = Field(default="Community grievance report", min_length=1, max_length=5000)
    location: str = Field(default="Host Community Site", min_length=1, max_length=240)
    occurred_at: datetime | None = None
    priority: str = Field(default="normal")

    @model_validator(mode="before")
    @classmethod
    def normalize_input(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data

        d = dict(data)

        # 1. Resolve name
        if not d.get("complainant_name") or d.get("complainant_name") == "Community Member":
            for alias in ("name", "citizen_name", "user_name", "full_name", "complainant"):
                if d.get(alias):
                    d["complainant_name"] = str(d[alias]).strip()
                    break

        # 2. Resolve contact (email / phone)
        if not d.get("contact_value") or d.get("contact_value") == "in-app-session":
            for alias in ("email", "phone", "phone_number", "contact", "contact_info", "contact_number"):
                if d.get(alias):
                    d["contact_value"] = str(d[alias]).strip().lower()
                    if "@" in str(d[alias]):
                        d["preferred_channel"] = ContactChannel.EMAIL
                    elif any(c.isdigit() for c in str(d[alias])):
                        d["preferred_channel"] = ContactChannel.SMS
                    break

        # 3. Resolve category
        if not d.get("category"):
            for alias in ("incident", "incident_type", "issue_type", "grievance_type"):
                if d.get(alias):
                    d["category"] = str(d[alias]).strip()
                    break
        if not d.get("category"):
            d["category"] = "Environmental Grievance"

        # 4. Resolve description
        desc = (
            d.get("description")
            or d.get("details")
            or d.get("issue")
            or d.get("report")
            or d.get("category")
            or "Community grievance report"
        )
        d["description"] = str(desc).strip()

        # 5. Resolve location
        loc = (
            d.get("location")
            or d.get("community")
            or d.get("site")
            or d.get("area")
            or d.get("address")
            or "Host Community Site"
        )
        d["location"] = str(loc).strip()

        # 6. Resolve priority
        raw_pri = str(d.get("priority", "normal")).strip().lower()
        pri_map = {
            "medium": "normal",
            "med": "normal",
            "moderate": "normal",
            "urgent": "critical",
            "emergency": "critical",
            "severe": "critical",
            "critical": "critical",
            "high": "high",
            "low": "low",
            "normal": "normal",
        }
        d["priority"] = pri_map.get(raw_pri, "normal")

        # 7. Robust occurred_at handling (never crash on natural language dates/times!)
        raw_occurred = d.get("occurred_at") or d.get("time") or d.get("date") or d.get("incident_time")
        if raw_occurred:
            if isinstance(raw_occurred, datetime):
                d["occurred_at"] = raw_occurred
            elif isinstance(raw_occurred, str):
                try:
                    d["occurred_at"] = datetime.fromisoformat(raw_occurred.replace("Z", "+00:00"))
                except Exception:
                    # Append natural language timestamp to description safely
                    d["occurred_at"] = None
                    d["description"] = f"{d['description']}\n\n[Incident timing noted: {raw_occurred}]"
            else:
                d["occurred_at"] = None
        else:
            d["occurred_at"] = None

        return d


class StaffLoginRequest(BaseModel):
    key: str = Field(min_length=1)


class SwiftAgentToolResponse(BaseModel):
    ticket_id: str
    reference: str = ""
    case_reference: str = ""
    status: str
    verification_code: str
    verification_pin: str = ""
    message: str
    badge: dict[str, str]
    success: bool = True

    @model_validator(mode="before")
    @classmethod
    def populate_aliases(cls, data: Any) -> Any:
        if isinstance(data, dict):
            t_id = data.get("ticket_id") or data.get("reference") or ""
            data["ticket_id"] = t_id
            data["reference"] = t_id
            data["case_reference"] = t_id
            v_code = data.get("verification_code") or data.get("verification_pin") or ""
            data["verification_code"] = v_code
            data["verification_pin"] = v_code
            data["success"] = True
            if "badge" not in data and t_id:
                data["badge"] = {"label": "Ticket ID", "value": t_id}
        return data


class SwiftAgentCaseLookupInput(BaseModel):
    model_config = ConfigDict(extra="ignore")
    reference: str = Field(min_length=1, max_length=60)
    verification_code: str | None = Field(default=None, max_length=40)

    @model_validator(mode="before")
    @classmethod
    def normalize_lookup(cls, data: Any) -> Any:
        if isinstance(data, dict):
            d = dict(data)
            ref = d.get("reference") or d.get("ticket_id") or d.get("case_id") or d.get("ticket") or ""
            d["reference"] = str(ref).strip()
            v_code = d.get("verification_code") or d.get("verification_pin") or d.get("pin") or d.get("code")
            d["verification_code"] = str(v_code).strip() if v_code else None
            return d
        return data


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
    model_config = ConfigDict(extra="ignore")
    reference: str = Field(min_length=1, max_length=60)
    file_name: str = Field(default="evidence_file", min_length=1, max_length=240)
    evidence_type: str = Field(default="photo", max_length=80)
    storage_uri: str | None = Field(default=None, max_length=500)
    description: str | None = Field(default=None, max_length=1000)

    @model_validator(mode="before")
    @classmethod
    def normalize_evidence(cls, data: Any) -> Any:
        if isinstance(data, dict):
            d = dict(data)
            ref = d.get("reference") or d.get("ticket_id") or d.get("case_id") or ""
            d["reference"] = str(ref).strip()
            fn = d.get("file_name") or d.get("filename") or d.get("name") or "incident_evidence"
            d["file_name"] = str(fn).strip()
            return d
        return data


class SwiftAgentEvidenceResponse(BaseModel):
    success: bool
    evidence_id: str
    reference: str
    message: str


class SwiftAgentHandoffInput(BaseModel):
    model_config = ConfigDict(extra="ignore")
    reference: str | None = Field(default=None, max_length=60)
    citizen_name: str = Field(default="Community Member", max_length=160)
    contact_value: str = Field(default="in-app-session", max_length=160)
    reason: str = Field(default="Community member requested human officer assistance", min_length=1, max_length=2000)
    urgency: str = Field(default="high")

    @model_validator(mode="before")
    @classmethod
    def normalize_handoff(cls, data: Any) -> Any:
        if isinstance(data, dict):
            d = dict(data)
            if not d.get("citizen_name") or d.get("citizen_name") == "Community Member":
                for alias in ("name", "complainant_name", "user_name"):
                    if d.get(alias):
                        d["citizen_name"] = str(d[alias]).strip()
                        break
            if not d.get("contact_value") or d.get("contact_value") == "in-app-session":
                for alias in ("email", "phone", "contact"):
                    if d.get(alias):
                        d["contact_value"] = str(d[alias]).strip().lower()
                        break
            if not d.get("reason"):
                d["reason"] = d.get("message") or d.get("details") or "Community member requested human officer assistance"
            raw_urg = str(d.get("urgency", "high")).strip().lower()
            d["urgency"] = raw_urg if raw_urg in ("normal", "high", "critical") else "high"
            return d
        return data


class SwiftAgentHandoffResponse(BaseModel):
    handoff_id: str
    status: str
    reference: str | None = None
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
