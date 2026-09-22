import json
import secrets
import urllib.error
import urllib.request
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from .config import settings
from .models import (
    AgentHandoff,
    Case,
    CaseEvent,
    Evidence,
    InvestigationNote,
    NotificationEvent,
)
from .schemas import (
    CaseAssignment,
    CaseDetail,
    CaseExport,
    CaseStage,
    CaseSummary,
    CaseTransition,
    CaseWithTimeline,
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
    PublicCaseStatus,
    SlaStatus,
    StatusLookup,
    SwiftAgentComplaintInput,
    SwiftAgentToolResponse,
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
    CaseStage.REPORTED: "Your complaint has been received and is being reviewed by community liaison officers.",
    CaseStage.UNDER_INVESTIGATION: "Your case is currently under active field investigation.",
    CaseStage.RESPONSE_ISSUED: "An official response has been issued for your grievance.",
    CaseStage.RESOLVED: "Your case has been formally resolved and documented.",
    CaseStage.ESCALATED: "Your case has been escalated for high-priority executive review.",
}


def now_dt() -> datetime:
    return datetime.now(UTC)


def now_iso() -> str:
    return now_dt().isoformat()


def parse_dt(value: str | datetime | None) -> datetime | None:
    if not value:
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=UTC)
    dt = datetime.fromisoformat(value)
    return dt if dt.tzinfo else dt.replace(tzinfo=UTC)


def generate_reference() -> str:
    return f"HCC-{datetime.now(UTC):%Y%m%d}-{secrets.token_hex(4).upper()}"


def generate_verification_code() -> str:
    return f"{secrets.randbelow(900000) + 100000}"


def sla_times(priority: str, created_at: datetime) -> tuple[str, str]:
    target = SLA_TARGETS.get(priority, SLA_TARGETS["normal"])
    warning = created_at + (target * 0.8)
    due = created_at + target
    return warning.isoformat(), due.isoformat()


def calculate_sla_status(case: Case) -> SlaStatus:
    if case.stage == CaseStage.RESOLVED.value:
        return SlaStatus.RESOLVED
    current = now_dt()
    due_at = parse_dt(case.sla_due_at)
    warning_at = parse_dt(case.sla_warning_at)
    if due_at and current >= due_at:
        return SlaStatus.BREACHED
    if warning_at and current >= warning_at:
        return SlaStatus.AT_RISK
    return SlaStatus.ON_TRACK


def calculate_age_hours(created_at: str | datetime) -> float:
    dt = parse_dt(created_at)
    if not dt:
        return 0.0
    return round(max(0.0, (now_dt() - dt).total_seconds() / 3600), 1)


def case_to_detail(case: Case) -> CaseDetail:
    created = parse_dt(case.created_at) or now_dt()
    updated = parse_dt(case.updated_at) or now_dt()
    return CaseDetail(
        id=case.id,
        reference=case.reference,
        category=case.category,
        location=case.location,
        stage=CaseStage(case.stage),
        priority=case.priority,
        assigned_officer=case.assigned_officer,
        created_at=created,
        updated_at=updated,
        age_hours=calculate_age_hours(created),
        sla_status=calculate_sla_status(case),
        sla_warning_at=parse_dt(case.sla_warning_at),
        sla_due_at=parse_dt(case.sla_due_at),
        complainant_name=case.complainant_name,
        contact_value=case.contact_value,
        preferred_channel=ContactChannel(case.preferred_channel),
        description=case.description,
        occurred_at=parse_dt(case.occurred_at),
        source_channel=case.source_channel,
        response_summary=case.response_summary,
        resolution_summary=case.resolution_summary,
        resolved_at=parse_dt(case.resolved_at),
        status_verification_code=case.status_verification_code,
    )


def case_to_summary(case: Case) -> CaseSummary:
    created = parse_dt(case.created_at) or now_dt()
    updated = parse_dt(case.updated_at) or now_dt()
    return CaseSummary(
        id=case.id,
        reference=case.reference,
        category=case.category,
        location=case.location,
        stage=CaseStage(case.stage),
        priority=case.priority,
        assigned_officer=case.assigned_officer,
        created_at=created,
        updated_at=updated,
        age_hours=calculate_age_hours(created),
        sla_status=calculate_sla_status(case),
        sla_warning_at=parse_dt(case.sla_warning_at),
        sla_due_at=parse_dt(case.sla_due_at),
    )


async def create_case(payload: ComplaintIntake, session: AsyncSession, actor: str = "community_member") -> CaseDetail:
    case_id = str(uuid.uuid4())
    ref = generate_reference()
    v_code = generate_verification_code()
    created_dt = now_dt()
    warning_at, due_at = sla_times(payload.priority, created_dt)

    case = Case(
        id=case_id,
        reference=ref,
        status_verification_code=v_code,
        complainant_name=payload.complainant_name,
        contact_value=payload.contact_value,
        preferred_channel=payload.preferred_channel.value,
        category=payload.category,
        description=payload.description,
        location=payload.location,
        occurred_at=payload.occurred_at.isoformat() if payload.occurred_at else None,
        source_channel=payload.source_channel,
        stage=CaseStage.REPORTED.value,
        priority=payload.priority,
        assigned_officer=None,
        sla_warning_at=warning_at,
        sla_due_at=due_at,
        created_at=created_dt.isoformat(),
        updated_at=created_dt.isoformat(),
    )
    session.add(case)

    # Initial event
    event = CaseEvent(
        id=str(uuid.uuid4()),
        case_id=case_id,
        event_type="complaint_logged",
        actor=actor,
        occurred_at=created_dt.isoformat(),
        metadata_json=json.dumps({
            "source": payload.source_channel,
            "category": payload.category,
            "priority": payload.priority,
            "channel": payload.preferred_channel.value,
        }),
    )
    session.add(event)

    # Acknowledgement Notification
    ack_msg = (
        f"Complaint received. Reference: {ref}. "
        f"Verification code: {v_code}. Status: {PUBLIC_STATUS_MESSAGES[CaseStage.REPORTED]}"
    )
    notification = NotificationEvent(
        id=str(uuid.uuid4()),
        case_id=case_id,
        event_type="complaint_acknowledged",
        channel=payload.preferred_channel.value,
        recipient=payload.contact_value,
        message=ack_msg,
        status="delivered" if payload.preferred_channel == ContactChannel.IN_BROWSER_CHAT else "pending",
        idempotency_key=f"{case_id}-ack",
        created_at=created_dt.isoformat(),
    )
    session.add(notification)

    # SwiftAgents Handoff / Webhook event
    handoff_payload = {
        "case_id": case_id,
        "reference": ref,
        "category": payload.category,
        "stage": CaseStage.REPORTED.value,
        "source": payload.source_channel,
        "verification_code": v_code,
    }
    handoff = AgentHandoff(
        id=str(uuid.uuid4()),
        case_id=case_id,
        event_type="case_created",
        payload_json=json.dumps(handoff_payload),
        status="pending",
        created_at=created_dt.isoformat(),
    )
    session.add(handoff)

    await session.commit()
    await session.refresh(case)
    return case_to_detail(case)


async def handle_agent_complaint(payload: SwiftAgentComplaintInput, session: AsyncSession) -> SwiftAgentToolResponse:
    intake = ComplaintIntake(
        complainant_name=payload.complainant_name,
        contact_value=payload.contact_value,
        preferred_channel=payload.preferred_channel,
        category=payload.category,
        description=payload.description,
        location=payload.location,
        occurred_at=payload.occurred_at,
        source_channel="swiftagents_chat",
        priority=payload.priority,
    )
    detail = await create_case(intake, session=session, actor="swiftagents_ai")
    msg = (
        f"Grievance recorded successfully!\n\n"
        f"• **Ticket ID**: `{detail.reference}`\n"
        f"• **Verification Code**: `{detail.status_verification_code}`\n"
        f"• **Stage**: {PUBLIC_STATUS_MESSAGES[CaseStage.REPORTED]}\n\n"
        f"Keep your verification code safe to check progress anytime."
    )
    return SwiftAgentToolResponse(
        ticket_id=detail.reference,
        status=detail.stage.value,
        verification_code=detail.status_verification_code or "",
        message=msg,
        badge={"label": "Ticket ID", "value": detail.reference},
    )


async def public_status(lookup: StatusLookup, session: AsyncSession) -> PublicCaseStatus:
    stmt = select(Case).where(Case.reference == lookup.reference.strip())
    result = await session.execute(stmt)
    case = result.scalar_one_or_none()

    if not case:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Case reference not found")

    code_match = (
        bool(lookup.verification_code)
        and lookup.verification_code.strip() == case.status_verification_code.strip()
    )
    contact_match = (
        bool(lookup.contact_value)
        and lookup.contact_value.strip().lower() == case.contact_value.strip().lower()
    )

    if not (code_match or contact_match):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Invalid verification code or contact details")

    stage_enum = CaseStage(case.stage)
    updated_dt = parse_dt(case.updated_at) or now_dt()
    return PublicCaseStatus(
        reference=case.reference,
        stage=stage_enum,
        status_message=PUBLIC_STATUS_MESSAGES.get(stage_enum, "Your case is actively being processed."),
        updated_at=updated_dt,
        sla_status=calculate_sla_status(case),
    )


async def list_cases(
    session: AsyncSession,
    stage: str | None = None,
    queue: str | None = None,
    query: str | None = None,
) -> list[CaseSummary]:
    stmt = select(Case).order_by(Case.created_at.desc())

    if stage:
        stmt = stmt.where(Case.stage == stage)

    if query:
        term = f"%{query.strip()}%"
        stmt = stmt.where(
            (Case.reference.ilike(term))
            | (Case.category.ilike(term))
            | (Case.location.ilike(term))
            | (Case.description.ilike(term))
        )

    result = await session.execute(stmt)
    cases = result.scalars().all()

    summaries = [case_to_summary(c) for c in cases]

    if queue == "open":
        return [s for s in summaries if s.stage != CaseStage.RESOLVED]
    if queue == "unassigned":
        return [s for s in summaries if not s.assigned_officer and s.stage != CaseStage.RESOLVED]
    if queue == "at_risk":
        return [s for s in summaries if s.sla_status == SlaStatus.AT_RISK and s.stage != CaseStage.RESOLVED]
    if queue == "breached":
        return [s for s in summaries if s.sla_status == SlaStatus.BREACHED and s.stage != CaseStage.RESOLVED]
    if queue == "escalated":
        return [s for s in summaries if s.stage == CaseStage.ESCALATED]

    return summaries


async def get_case_or_404(case_id: str, session: AsyncSession) -> CaseWithTimeline:
    stmt = (
        select(Case)
        .where(Case.id == case_id)
        .options(selectinload(Case.events))
    )
    result = await session.execute(stmt)
    case = result.scalar_one_or_none()

    if not case:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Case not found")

    events = [
        EventView(
            event_type=e.event_type,
            actor=e.actor,
            occurred_at=parse_dt(e.occurred_at) or now_dt(),
            metadata=e.metadata_dict,
        )
        for e in sorted(case.events, key=lambda x: x.occurred_at)
    ]
    return CaseWithTimeline(case=case_to_detail(case), events=events)


async def assign_case(case_id: str, payload: CaseAssignment, session: AsyncSession, actor: str = "staff") -> CaseDetail:
    stmt = select(Case).where(Case.id == case_id)
    result = await session.execute(stmt)
    case = result.scalar_one_or_none()

    if not case:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Case not found")

    case.assigned_officer = payload.assigned_officer
    case.updated_at = now_iso()

    event = CaseEvent(
        id=str(uuid.uuid4()),
        case_id=case_id,
        event_type="case_assigned",
        actor=actor,
        occurred_at=case.updated_at,
        metadata_json=json.dumps({"assigned_officer": payload.assigned_officer}),
    )
    session.add(event)

    notification = NotificationEvent(
        id=str(uuid.uuid4()),
        case_id=case_id,
        event_type="officer_assigned",
        channel=case.preferred_channel,
        recipient=case.contact_value,
        message=f"Case {case.reference} has been assigned to {payload.assigned_officer}.",
        status="delivered" if case.preferred_channel == ContactChannel.IN_BROWSER_CHAT.value else "pending",
        idempotency_key=f"{case_id}-assign-{int(datetime.now(UTC).timestamp())}",
        created_at=case.updated_at,
    )
    session.add(notification)

    await session.commit()
    await session.refresh(case)
    return case_to_detail(case)


async def transition_case(case_id: str, payload: CaseTransition, session: AsyncSession, actor: str = "staff") -> CaseDetail:
    stmt = select(Case).where(Case.id == case_id)
    result = await session.execute(stmt)
    case = result.scalar_one_or_none()

    if not case:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Case not found")

    current_stage = CaseStage(case.stage)
    target_stage = payload.stage

    if target_stage not in ALLOWED_TRANSITIONS[current_stage]:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            f"Invalid transition from {current_stage.value} to {target_stage.value}",
        )

    if target_stage == CaseStage.UNDER_INVESTIGATION and not case.assigned_officer:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Case must have an assigned officer before investigation")

    if target_stage == CaseStage.RESPONSE_ISSUED:
        summary = payload.response_summary or case.response_summary
        if not summary:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Response summary is required to issue response")
        case.response_summary = summary

    if target_stage == CaseStage.RESOLVED:
        summary = payload.resolution_summary or case.resolution_summary
        if not summary:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Resolution summary is required to resolve case")
        case.resolution_summary = summary
        case.resolved_at = now_iso()

    case.stage = target_stage.value
    case.updated_at = now_iso()

    event = CaseEvent(
        id=str(uuid.uuid4()),
        case_id=case_id,
        event_type="stage_changed",
        actor=actor,
        occurred_at=case.updated_at,
        metadata_json=json.dumps({
            "from_stage": current_stage.value,
            "to_stage": target_stage.value,
            "note": payload.note,
        }),
    )
    session.add(event)

    msg = f"Case {case.reference} updated to {target_stage.value.replace('_', ' ')}: {PUBLIC_STATUS_MESSAGES[target_stage]}"
    notification = NotificationEvent(
        id=str(uuid.uuid4()),
        case_id=case_id,
        event_type="stage_updated",
        channel=case.preferred_channel,
        recipient=case.contact_value,
        message=msg,
        status="delivered" if case.preferred_channel == ContactChannel.IN_BROWSER_CHAT.value else "pending",
        idempotency_key=f"{case_id}-{target_stage.value}-{int(datetime.now(UTC).timestamp())}",
        created_at=case.updated_at,
    )
    session.add(notification)

    handoff = AgentHandoff(
        id=str(uuid.uuid4()),
        case_id=case_id,
        event_type="stage_transition",
        payload_json=json.dumps({
            "case_id": case_id,
            "reference": case.reference,
            "from_stage": current_stage.value,
            "to_stage": target_stage.value,
        }),
        status="pending",
        created_at=case.updated_at,
    )
    session.add(handoff)

    await session.commit()
    await session.refresh(case)
    return case_to_detail(case)


async def add_note(case_id: str, payload: InvestigationNoteCreate, session: AsyncSession, actor: str = "staff") -> InvestigationNoteView:
    stmt = select(Case).where(Case.id == case_id)
    case = (await session.execute(stmt)).scalar_one_or_none()
    if not case:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Case not found")

    note_id = str(uuid.uuid4())
    created = now_iso()
    note = InvestigationNote(
        id=note_id,
        case_id=case_id,
        note=payload.note,
        actor=actor,
        created_at=created,
    )
    session.add(note)

    event = CaseEvent(
        id=str(uuid.uuid4()),
        case_id=case_id,
        event_type="note_added",
        actor=actor,
        occurred_at=created,
        metadata_json=json.dumps({"note_id": note_id}),
    )
    session.add(event)

    await session.commit()
    return InvestigationNoteView(
        id=note_id,
        case_id=case_id,
        note=payload.note,
        actor=actor,
        created_at=parse_dt(created) or now_dt(),
    )


async def case_notes(case_id: str, session: AsyncSession) -> list[InvestigationNoteView]:
    stmt = select(InvestigationNote).where(InvestigationNote.case_id == case_id).order_by(InvestigationNote.created_at.desc())
    result = await session.execute(stmt)
    notes = result.scalars().all()
    return [
        InvestigationNoteView(
            id=n.id,
            case_id=n.case_id,
            note=n.note,
            actor=n.actor,
            created_at=parse_dt(n.created_at) or now_dt(),
        )
        for n in notes
    ]


async def add_evidence(case_id: str, payload: EvidenceCreate, session: AsyncSession, actor: str = "staff") -> EvidenceView:
    stmt = select(Case).where(Case.id == case_id)
    case = (await session.execute(stmt)).scalar_one_or_none()
    if not case:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Case not found")

    evidence_id = str(uuid.uuid4())
    created = now_iso()
    ev = Evidence(
        id=evidence_id,
        case_id=case_id,
        file_name=payload.file_name,
        evidence_type=payload.evidence_type,
        description=payload.description,
        storage_uri=payload.storage_uri or f"evidence://{evidence_id}/{payload.file_name}",
        actor=actor,
        created_at=created,
    )
    session.add(ev)

    event = CaseEvent(
        id=str(uuid.uuid4()),
        case_id=case_id,
        event_type="evidence_registered",
        actor=actor,
        occurred_at=created,
        metadata_json=json.dumps({"file_name": payload.file_name, "evidence_type": payload.evidence_type}),
    )
    session.add(event)

    await session.commit()
    return EvidenceView(
        id=evidence_id,
        case_id=case_id,
        file_name=ev.file_name,
        evidence_type=ev.evidence_type,
        description=ev.description,
        storage_uri=ev.storage_uri,
        actor=ev.actor,
        created_at=parse_dt(created) or now_dt(),
    )


async def case_evidence(case_id: str, session: AsyncSession) -> list[EvidenceView]:
    stmt = select(Evidence).where(Evidence.case_id == case_id).order_by(Evidence.created_at.desc())
    result = await session.execute(stmt)
    return [
        EvidenceView(
            id=e.id,
            case_id=e.case_id,
            file_name=e.file_name,
            evidence_type=e.evidence_type,
            description=e.description,
            storage_uri=e.storage_uri,
            actor=e.actor,
            created_at=parse_dt(e.created_at) or now_dt(),
        )
        for e in result.scalars().all()
    ]


async def case_timeline(case_id: str, session: AsyncSession) -> list[EventView]:
    stmt = select(CaseEvent).where(CaseEvent.case_id == case_id).order_by(CaseEvent.occurred_at.asc())
    result = await session.execute(stmt)
    return [
        EventView(
            event_type=e.event_type,
            actor=e.actor,
            occurred_at=parse_dt(e.occurred_at) or now_dt(),
            metadata=e.metadata_dict,
        )
        for e in result.scalars().all()
    ]


async def case_notifications(case_id: str, session: AsyncSession) -> list[NotificationView]:
    stmt = select(NotificationEvent).where(NotificationEvent.case_id == case_id).order_by(NotificationEvent.created_at.desc())
    result = await session.execute(stmt)
    return [
        NotificationView(
            id=n.id,
            case_id=n.case_id,
            event_type=n.event_type,
            channel=ContactChannel(n.channel),
            recipient=n.recipient,
            message=n.message,
            status=n.status,
            attempts=n.attempts,
            created_at=parse_dt(n.created_at) or now_dt(),
            last_attempt_at=parse_dt(n.last_attempt_at),
            error_message=n.error_message,
        )
        for n in result.scalars().all()
    ]


async def export_case(case_id: str, session: AsyncSession) -> CaseExport:
    case_detail = (await get_case_or_404(case_id, session)).case
    events = await case_timeline(case_id, session)
    notes = await case_notes(case_id, session)
    evidence = await case_evidence(case_id, session)
    notifications = await case_notifications(case_id, session)

    return CaseExport(
        case=case_detail,
        events=events,
        notes=notes,
        evidence=evidence,
        notifications=notifications,
    )


async def portfolio_report(session: AsyncSession) -> PortfolioReport:
    stmt = select(Case)
    result = await session.execute(stmt)
    cases = result.scalars().all()

    total = len(cases)
    by_stage: dict[str, int] = {}
    by_priority: dict[str, int] = {}
    by_category: dict[str, int] = {}

    open_cases = 0
    resolved_cases = 0
    unassigned = 0
    escalated = 0
    at_risk = 0
    breached = 0

    for c in cases:
        by_stage[c.stage] = by_stage.get(c.stage, 0) + 1
        by_priority[c.priority] = by_priority.get(c.priority, 0) + 1
        by_category[c.category] = by_category.get(c.category, 0) + 1

        if c.stage == CaseStage.RESOLVED.value:
            resolved_cases += 1
        else:
            open_cases += 1
            if not c.assigned_officer:
                unassigned += 1
            if c.stage == CaseStage.ESCALATED.value:
                escalated += 1

            sla = calculate_sla_status(c)
            if sla == SlaStatus.AT_RISK:
                at_risk += 1
            elif sla == SlaStatus.BREACHED:
                breached += 1

    return PortfolioReport(
        total_cases=total,
        open_cases=open_cases,
        resolved_cases=resolved_cases,
        unassigned_cases=unassigned,
        escalated_cases=escalated,
        at_risk_cases=at_risk,
        breached_cases=breached,
        by_stage=by_stage,
        by_priority=by_priority,
        by_category=by_category,
    )


async def list_handoffs(session: AsyncSession) -> list[HandoffView]:
    stmt = select(AgentHandoff).order_by(AgentHandoff.created_at.desc())
    result = await session.execute(stmt)
    return [
        HandoffView(
            id=h.id,
            case_id=h.case_id,
            event_type=h.event_type,
            status=h.status,
            attempts=h.attempts,
            created_at=parse_dt(h.created_at) or now_dt(),
            last_attempt_at=parse_dt(h.last_attempt_at),
            error_message=h.error_message,
        )
        for h in result.scalars().all()
    ]


async def deliver_handoff(handoff_id: str, session: AsyncSession) -> HandoffView:
    stmt = select(AgentHandoff).where(AgentHandoff.id == handoff_id)
    result = await session.execute(stmt)
    h = result.scalar_one_or_none()
    if not h:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Handoff event not found")

    h.attempts += 1
    h.last_attempt_at = now_iso()

    if settings.swiftagents_webhook_url:
        try:
            req = urllib.request.Request(
                settings.swiftagents_webhook_url,
                data=h.payload_json.encode("utf-8"),
                headers={"Content-Type": "application/json", "X-Agent-Key": settings.agent_key or ""},
            )
            with urllib.request.urlopen(req, timeout=5) as resp:
                if resp.status < 300:
                    h.status = "delivered"
                    h.error_message = None
                else:
                    h.status = "failed"
                    h.error_message = f"HTTP {resp.status}"
        except Exception as ex:
            h.status = "failed"
            h.error_message = str(ex)
    else:
        h.status = "awaiting_configuration"
        h.error_message = "SWIFTAGENTS_WEBHOOK_URL not configured"

    await session.commit()
    await session.refresh(h)
    return HandoffView(
        id=h.id,
        case_id=h.case_id,
        event_type=h.event_type,
        status=h.status,
        attempts=h.attempts,
        created_at=parse_dt(h.created_at) or now_dt(),
        last_attempt_at=parse_dt(h.last_attempt_at),
        error_message=h.error_message,
    )


async def list_notifications(session: AsyncSession) -> list[NotificationView]:
    stmt = select(NotificationEvent).order_by(NotificationEvent.created_at.desc())
    result = await session.execute(stmt)
    return [
        NotificationView(
            id=n.id,
            case_id=n.case_id,
            event_type=n.event_type,
            channel=ContactChannel(n.channel),
            recipient=n.recipient,
            message=n.message,
            status=n.status,
            attempts=n.attempts,
            created_at=parse_dt(n.created_at) or now_dt(),
            last_attempt_at=parse_dt(n.last_attempt_at),
            error_message=n.error_message,
        )
        for n in result.scalars().all()
    ]


async def deliver_notification(notification_id: str, session: AsyncSession) -> NotificationView:
    stmt = select(NotificationEvent).where(NotificationEvent.id == notification_id)
    result = await session.execute(stmt)
    n = result.scalar_one_or_none()
    if not n:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Notification event not found")

    n.attempts += 1
    n.last_attempt_at = now_iso()
    n.status = "awaiting_configuration"
    n.error_message = "Notification provider not configured"

    await session.commit()
    await session.refresh(n)
    return NotificationView(
        id=n.id,
        case_id=n.case_id,
        event_type=n.event_type,
        channel=ContactChannel(n.channel),
        recipient=n.recipient,
        message=n.message,
        status=n.status,
        attempts=n.attempts,
        created_at=parse_dt(n.created_at) or now_dt(),
        last_attempt_at=parse_dt(n.last_attempt_at),
        error_message=n.error_message,
    )
