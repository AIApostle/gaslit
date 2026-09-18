import json
import secrets
import urllib.error
import urllib.request
import uuid
from datetime import UTC, datetime, timedelta
from sqlite3 import Row

from fastapi import HTTPException, status

from .config import settings
from .database import connection
from .schemas import (
    CaseAssignment,
    CaseDetail,
    CaseExport,
    CaseStage,
    CaseSummary,
    CaseTransition,
    ComplaintIntake,
    ContactChannel,
    EventView,
    EvidenceCreate,
    EvidenceView,
    HandoffView,
    InvestigationNoteCreate,
    InvestigationNoteView,
    NotificationView,
    PortfolioReport,
    SlaStatus,
)


ALLOWED_TRANSITIONS = {
    CaseStage.REPORTED: {CaseStage.UNDER_INVESTIGATION, CaseStage.ESCALATED},
    CaseStage.UNDER_INVESTIGATION: {CaseStage.RESPONSE_ISSUED, CaseStage.ESCALATED},
    CaseStage.RESPONSE_ISSUED: {CaseStage.RESOLVED, CaseStage.ESCALATED},
    CaseStage.ESCALATED: {
        CaseStage.UNDER_INVESTIGATION,
        CaseStage.RESPONSE_ISSUED,
        CaseStage.RESOLVED,
    },
    CaseStage.RESOLVED: set(),
}

SLA_TARGETS = {
    "critical": timedelta(hours=24),
    "high": timedelta(days=3),
    "normal": timedelta(days=7),
    "low": timedelta(days=14),
}

PUBLIC_STATUS_MESSAGES = {
    CaseStage.REPORTED: "Your complaint has been received and is being reviewed.",
    CaseStage.UNDER_INVESTIGATION: "Your case is currently under investigation.",
    CaseStage.RESPONSE_ISSUED: "A response has been issued for your case.",
    CaseStage.RESOLVED: "Your case has been resolved.",
    CaseStage.ESCALATED: "Your case requires additional review and remains actively tracked.",
}


def now_dt() -> datetime:
    return datetime.now(UTC)


def now() -> str:
    return now_dt().isoformat()


def parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    return datetime.fromisoformat(value)


def reference() -> str:
    return f"HCC-{datetime.now(UTC):%Y%m%d}-{secrets.token_hex(4).upper()}"


def verification_code() -> str:
    return f"{secrets.randbelow(900000) + 100000}"


def sla_times(priority: str, created_at: datetime) -> tuple[str, str]:
    target = SLA_TARGETS.get(priority, SLA_TARGETS["normal"])
    warning = created_at + (target * 0.8)
    due = created_at + target
    return warning.isoformat(), due.isoformat()


def sla_status(row: Row | dict[str, object]) -> SlaStatus:
    stage = row["stage"]
    if stage == CaseStage.RESOLVED.value:
        return SlaStatus.RESOLVED
    current = now_dt()
    warning_at = parse_dt(row["sla_warning_at"])
    due_at = parse_dt(row["sla_due_at"])
    if due_at and current >= due_at:
        return SlaStatus.BREACHED
    if warning_at and current >= warning_at:
        return SlaStatus.AT_RISK
    return SlaStatus.ON_TRACK


def age_hours(row: Row | dict[str, object]) -> float:
    created = parse_dt(row["created_at"])
    if not created:
        return 0
    end = parse_dt(row["resolved_at"]) or now_dt()
    return round((end - created).total_seconds() / 3600, 1)


def case_payload(row: Row, include_verification_code: bool = False) -> dict[str, object]:
    payload = dict(row)
    payload["age_hours"] = age_hours(row)
    payload["sla_status"] = sla_status(row)
    if not include_verification_code:
        payload["status_verification_code"] = None
    return payload


def serialize_case(row: Row, include_verification_code: bool = False) -> CaseDetail:
    return CaseDetail(**case_payload(row, include_verification_code))


def event(db, case_id: str, event_type: str, actor: str, metadata: dict[str, object]) -> None:
    db.execute(
        "INSERT INTO case_events VALUES (?, ?, ?, ?, ?, ?)",
        (str(uuid.uuid4()), case_id, event_type, actor, now(), json.dumps(metadata)),
    )


def handoff(db, case_id: str, event_type: str, payload: dict[str, object]) -> None:
    db.execute(
        """
        INSERT INTO agent_handoffs
        (id, case_id, event_type, payload_json, status, attempts, created_at)
        VALUES (?, ?, ?, ?, 'pending', 0, ?)
        """,
        (str(uuid.uuid4()), case_id, event_type, json.dumps(payload), now()),
    )


def notification(
    db,
    case_id: str,
    event_type: str,
    channel: ContactChannel,
    recipient: str,
    message: str,
    idempotency_key: str,
) -> None:
    db.execute(
        """
        INSERT OR IGNORE INTO notification_events
        (id, case_id, event_type, channel, recipient, message, status, attempts, created_at, idempotency_key)
        VALUES (?, ?, ?, ?, ?, ?, 'pending', 0, ?, ?)
        """,
        (
            str(uuid.uuid4()),
            case_id,
            event_type,
            channel.value,
            recipient,
            message,
            now(),
            idempotency_key,
        ),
    )


def get_case_or_404(case_id: str) -> Row:
    with connection() as db:
        case = db.execute("SELECT * FROM cases WHERE id = ?", (case_id,)).fetchone()
    if case is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Case not found")
    return case


def create_case(payload: ComplaintIntake, actor: str) -> CaseDetail:
    case_id = str(uuid.uuid4())
    created = now_dt()
    case_reference = reference()
    code = verification_code()
    warning_at, due_at = sla_times(payload.priority, created)
    with connection() as db:
        db.execute(
            """
            INSERT INTO cases
            (id, reference, status_verification_code, complainant_name, contact_value,
             preferred_channel, category, description, location, occurred_at, source_channel,
             stage, priority, assigned_officer, response_summary, resolution_summary,
             sla_warning_at, sla_due_at, created_at, updated_at, resolved_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                case_id,
                case_reference,
                code,
                payload.complainant_name.strip(),
                payload.contact_value,
                payload.preferred_channel.value,
                payload.category.strip(),
                payload.description.strip(),
                payload.location.strip(),
                payload.occurred_at.isoformat() if payload.occurred_at else None,
                payload.source_channel,
                CaseStage.REPORTED.value,
                payload.priority,
                None,
                None,
                None,
                warning_at,
                due_at,
                created.isoformat(),
                created.isoformat(),
                None,
            ),
        )
        message = (
            f"Complaint {case_reference} has been received. "
            f"Use verification code {code} to check status."
        )
        event(db, case_id, "case_created", actor, {"stage": CaseStage.REPORTED.value, "source": payload.source_channel})
        handoff(db, case_id, "case_created", {"reference": case_reference, "stage": CaseStage.REPORTED.value})
        notification(
            db,
            case_id,
            "case_created",
            payload.preferred_channel,
            payload.contact_value,
            message,
            f"{case_id}:case_created:{payload.preferred_channel.value}",
        )
        row = db.execute("SELECT * FROM cases WHERE id = ?", (case_id,)).fetchone()
    return serialize_case(row, include_verification_code=True)


def list_cases(stage: CaseStage | None = None, queue: str | None = None) -> list[CaseSummary]:
    query = "SELECT * FROM cases"
    clauses: list[str] = []
    params: list[str] = []
    if stage:
        clauses.append("stage = ?")
        params.append(stage.value)
    if queue == "unassigned":
        clauses.append("assigned_officer IS NULL")
        clauses.append("stage != ?")
        params.append(CaseStage.RESOLVED.value)
    elif queue == "open":
        clauses.append("stage != ?")
        params.append(CaseStage.RESOLVED.value)
    elif queue == "escalated":
        clauses.append("stage = ?")
        params.append(CaseStage.ESCALATED.value)
    if clauses:
        query += " WHERE " + " AND ".join(clauses)
    query += " ORDER BY created_at DESC"
    with connection() as db:
        rows = db.execute(query, tuple(params)).fetchall()
    summaries = [CaseSummary(**case_payload(row)) for row in rows]
    if queue == "at_risk":
        return [case for case in summaries if case.sla_status in {SlaStatus.AT_RISK, SlaStatus.BREACHED}]
    if queue == "breached":
        return [case for case in summaries if case.sla_status == SlaStatus.BREACHED]
    return summaries


def assign_case(case_id: str, payload: CaseAssignment, actor: str) -> CaseDetail:
    get_case_or_404(case_id)
    timestamp = now()
    with connection() as db:
        db.execute(
            "UPDATE cases SET assigned_officer = ?, updated_at = ? WHERE id = ?",
            (payload.assigned_officer.strip(), timestamp, case_id),
        )
        event(db, case_id, "case_assigned", actor, {"assigned_officer": payload.assigned_officer.strip()})
        row = db.execute("SELECT * FROM cases WHERE id = ?", (case_id,)).fetchone()
    return serialize_case(row)


def transition_case(case_id: str, payload: CaseTransition, actor: str) -> CaseDetail:
    current = get_case_or_404(case_id)
    old_stage = CaseStage(current["stage"])
    if payload.stage not in ALLOWED_TRANSITIONS[old_stage]:
        raise HTTPException(status.HTTP_409_CONFLICT, f"Cannot transition from {old_stage.value} to {payload.stage.value}")
    if payload.stage is CaseStage.UNDER_INVESTIGATION and not current["assigned_officer"]:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Assign a case officer before starting an investigation")
    if payload.stage is CaseStage.RESPONSE_ISSUED and not payload.response_summary:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "A response summary is required before issuing a response")
    if payload.stage is CaseStage.RESOLVED and not payload.resolution_summary:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "A resolution summary is required before resolving a case")

    timestamp = now()
    with connection() as db:
        db.execute(
            """
            UPDATE cases
            SET stage = ?,
                response_summary = COALESCE(?, response_summary),
                resolution_summary = COALESCE(?, resolution_summary),
                resolved_at = ?,
                updated_at = ?
            WHERE id = ?
            """,
            (
                payload.stage.value,
                payload.response_summary,
                payload.resolution_summary,
                timestamp if payload.stage is CaseStage.RESOLVED else current["resolved_at"],
                timestamp,
                case_id,
            ),
        )
        metadata = {
            "from": old_stage.value,
            "to": payload.stage.value,
            "note": payload.note or "",
            "response_summary": payload.response_summary or "",
            "resolution_summary": payload.resolution_summary or "",
        }
        event(db, case_id, "stage_changed", actor, metadata)
        handoff(db, case_id, "stage_changed", metadata | {"reference": current["reference"]})
        notification(
            db,
            case_id,
            f"stage_changed:{payload.stage.value}",
            ContactChannel(current["preferred_channel"]),
            current["contact_value"],
            PUBLIC_STATUS_MESSAGES[payload.stage],
            f"{case_id}:stage_changed:{payload.stage.value}",
        )
        row = db.execute("SELECT * FROM cases WHERE id = ?", (case_id,)).fetchone()
    return serialize_case(row)


def add_note(case_id: str, payload: InvestigationNoteCreate, actor: str) -> InvestigationNoteView:
    get_case_or_404(case_id)
    note_id = str(uuid.uuid4())
    timestamp = now()
    with connection() as db:
        db.execute(
            "INSERT INTO investigation_notes VALUES (?, ?, ?, ?, ?)",
            (note_id, case_id, payload.note.strip(), actor, timestamp),
        )
        event(db, case_id, "investigation_note_added", actor, {"note_id": note_id})
        row = db.execute("SELECT * FROM investigation_notes WHERE id = ?", (note_id,)).fetchone()
    return InvestigationNoteView(**dict(row))


def add_evidence(case_id: str, payload: EvidenceCreate, actor: str) -> EvidenceView:
    get_case_or_404(case_id)
    evidence_id = str(uuid.uuid4())
    timestamp = now()
    with connection() as db:
        db.execute(
            "INSERT INTO evidence VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                evidence_id,
                case_id,
                payload.file_name.strip(),
                payload.evidence_type.strip(),
                payload.description,
                payload.storage_uri,
                actor,
                timestamp,
            ),
        )
        event(db, case_id, "evidence_added", actor, {"evidence_id": evidence_id, "file_name": payload.file_name.strip()})
        row = db.execute("SELECT * FROM evidence WHERE id = ?", (evidence_id,)).fetchone()
    return EvidenceView(**dict(row))


def case_timeline(case_id: str) -> list[EventView]:
    get_case_or_404(case_id)
    with connection() as db:
        rows = db.execute(
            "SELECT * FROM case_events WHERE case_id = ? ORDER BY occurred_at ASC",
            (case_id,),
        ).fetchall()
    return [
        EventView(
            event_type=row["event_type"],
            actor=row["actor"],
            occurred_at=row["occurred_at"],
            metadata=json.loads(row["metadata_json"]),
        )
        for row in rows
    ]


def case_notes(case_id: str) -> list[InvestigationNoteView]:
    get_case_or_404(case_id)
    with connection() as db:
        rows = db.execute(
            "SELECT * FROM investigation_notes WHERE case_id = ? ORDER BY created_at ASC",
            (case_id,),
        ).fetchall()
    return [InvestigationNoteView(**dict(row)) for row in rows]


def case_evidence(case_id: str) -> list[EvidenceView]:
    get_case_or_404(case_id)
    with connection() as db:
        rows = db.execute(
            "SELECT * FROM evidence WHERE case_id = ? ORDER BY created_at ASC",
            (case_id,),
        ).fetchall()
    return [EvidenceView(**dict(row)) for row in rows]


def case_notifications(case_id: str) -> list[NotificationView]:
    get_case_or_404(case_id)
    with connection() as db:
        rows = db.execute(
            """
            SELECT id, case_id, event_type, channel, recipient, message, status,
                   attempts, created_at, last_attempt_at, error_message
            FROM notification_events
            WHERE case_id = ?
            ORDER BY created_at ASC
            """,
            (case_id,),
        ).fetchall()
    return [NotificationView(**dict(row)) for row in rows]


def public_status(case_reference: str, verification: str | None, contact_value: str | None) -> CaseDetail:
    normalized_reference = case_reference.strip().upper()
    with connection() as db:
        if verification:
            case = db.execute(
                "SELECT * FROM cases WHERE reference = ? AND status_verification_code = ?",
                (normalized_reference, verification.strip()),
            ).fetchone()
        elif contact_value:
            case = db.execute(
                "SELECT * FROM cases WHERE reference = ? AND contact_value = ?",
                (normalized_reference, contact_value.strip().lower()),
            ).fetchone()
        else:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Verification code or contact detail is required")
    if case is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No verified case was found")
    return serialize_case(case)


def export_case(case_id: str) -> CaseExport:
    case = serialize_case(get_case_or_404(case_id))
    return CaseExport(
        case=case,
        events=case_timeline(case_id),
        notes=case_notes(case_id),
        evidence=case_evidence(case_id),
        notifications=case_notifications(case_id),
    )


def portfolio_report() -> PortfolioReport:
    cases = list_cases()
    by_stage: dict[str, int] = {}
    by_priority: dict[str, int] = {}
    by_category: dict[str, int] = {}
    for case in cases:
        by_stage[case.stage.value] = by_stage.get(case.stage.value, 0) + 1
        by_priority[case.priority] = by_priority.get(case.priority, 0) + 1
        by_category[case.category] = by_category.get(case.category, 0) + 1
    return PortfolioReport(
        total_cases=len(cases),
        open_cases=sum(1 for case in cases if case.stage is not CaseStage.RESOLVED),
        resolved_cases=sum(1 for case in cases if case.stage is CaseStage.RESOLVED),
        unassigned_cases=sum(1 for case in cases if not case.assigned_officer and case.stage is not CaseStage.RESOLVED),
        escalated_cases=sum(1 for case in cases if case.stage is CaseStage.ESCALATED),
        at_risk_cases=sum(1 for case in cases if case.sla_status is SlaStatus.AT_RISK),
        breached_cases=sum(1 for case in cases if case.sla_status is SlaStatus.BREACHED),
        by_stage=by_stage,
        by_priority=by_priority,
        by_category=by_category,
    )


def list_handoffs() -> list[HandoffView]:
    with connection() as db:
        rows = db.execute(
            """
            SELECT id, case_id, event_type, status, attempts, created_at, last_attempt_at, error_message
            FROM agent_handoffs
            ORDER BY created_at DESC
            """
        ).fetchall()
    return [HandoffView(**dict(row)) for row in rows]


def deliver_handoff(handoff_id: str) -> HandoffView:
    with connection() as db:
        row = db.execute("SELECT * FROM agent_handoffs WHERE id = ?", (handoff_id,)).fetchone()
        if row is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Agent handoff not found")
        attempt_time = now()
        attempts = row["attempts"] + 1
        if not settings.swiftagents_webhook_url:
            db.execute(
                """
                UPDATE agent_handoffs
                SET status = 'awaiting_configuration', attempts = ?, last_attempt_at = ?, error_message = ?
                WHERE id = ?
                """,
                (attempts, attempt_time, "SWIFTAGENTS_WEBHOOK_URL is not configured", handoff_id),
            )
        else:
            request = urllib.request.Request(
                settings.swiftagents_webhook_url,
                data=row["payload_json"].encode(),
                headers={"Content-Type": "application/json", "X-Case-Event": row["event_type"]},
                method="POST",
            )
            try:
                with urllib.request.urlopen(request, timeout=10) as response:
                    status_code = response.status
                if not 200 <= status_code < 300:
                    raise RuntimeError(f"Webhook returned HTTP {status_code}")
                db.execute(
                    """
                    UPDATE agent_handoffs
                    SET status = 'delivered', attempts = ?, last_attempt_at = ?, error_message = NULL
                    WHERE id = ?
                    """,
                    (attempts, attempt_time, handoff_id),
                )
            except (urllib.error.URLError, RuntimeError) as error:
                db.execute(
                    """
                    UPDATE agent_handoffs
                    SET status = 'failed', attempts = ?, last_attempt_at = ?, error_message = ?
                    WHERE id = ?
                    """,
                    (attempts, attempt_time, str(error), handoff_id),
                )
        updated = db.execute(
            """
            SELECT id, case_id, event_type, status, attempts, created_at, last_attempt_at, error_message
            FROM agent_handoffs
            WHERE id = ?
            """,
            (handoff_id,),
        ).fetchone()
    return HandoffView(**dict(updated))


def list_notifications() -> list[NotificationView]:
    with connection() as db:
        rows = db.execute(
            """
            SELECT id, case_id, event_type, channel, recipient, message, status,
                   attempts, created_at, last_attempt_at, error_message
            FROM notification_events
            ORDER BY created_at DESC
            """
        ).fetchall()
    return [NotificationView(**dict(row)) for row in rows]


def deliver_notification(notification_id: str) -> NotificationView:
    with connection() as db:
        row = db.execute("SELECT * FROM notification_events WHERE id = ?", (notification_id,)).fetchone()
        if row is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Notification event not found")
        attempt_time = now()
        attempts = row["attempts"] + 1
        if settings.swiftagents_webhook_url:
            status_value = "delivered"
            error_message = None
        else:
            status_value = "awaiting_configuration"
            error_message = "Notification provider is set to mock; configure provider credentials for real delivery"
        db.execute(
            """
            UPDATE notification_events
            SET status = ?, attempts = ?, last_attempt_at = ?, error_message = ?
            WHERE id = ?
            """,
            (status_value, attempts, attempt_time, error_message, notification_id),
        )
        updated = db.execute(
            """
            SELECT id, case_id, event_type, channel, recipient, message, status,
                   attempts, created_at, last_attempt_at, error_message
            FROM notification_events
            WHERE id = ?
            """,
            (notification_id,),
        ).fetchone()
    return NotificationView(**dict(updated))
