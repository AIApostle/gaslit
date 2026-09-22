from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any

from fastapi import Depends, FastAPI, Header, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession

from .config import settings
from .database import close_database, get_session, init_db_async
from .schemas import (
    CaseAssignment,
    CaseDetail,
    CaseExport,
    CaseStage,
    CaseSummary,
    CaseTransition,
    CaseWithTimeline,
    ComplaintIntake,
    EvidenceCreate,
    EvidenceView,
    HandoffView,
    InvestigationNoteCreate,
    InvestigationNoteView,
    NotificationView,
    PortfolioReport,
    PublicCaseStatus,
    StatusLookup,
    SwiftAgentComplaintInput,
    SwiftAgentToolResponse,
)
from .service import (
    add_evidence,
    add_note,
    assign_case,
    case_evidence,
    case_notes,
    case_notifications,
    case_timeline,
    create_case,
    deliver_handoff,
    deliver_notification,
    export_case,
    get_case_or_404,
    handle_agent_complaint,
    list_cases,
    list_handoffs,
    list_notifications,
    portfolio_report,
    public_status,
    transition_case,
)


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncGenerator[None, None]:
    await init_db_async()
    yield
    await close_database()


app = FastAPI(
    title="Host Community Grievance & Case Management API",
    version="0.2.0",
    lifespan=lifespan,
)

# CORS middleware for local frontend and SwiftAgents widget
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def require_agent(x_agent_key: str | None = Header(default=None)) -> None:
    if settings.agent_key and x_agent_key != settings.agent_key:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid agent credential")


def require_staff(x_staff_key: str | None = Header(default=None)) -> None:
    if settings.staff_key and x_staff_key != settings.staff_key:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid staff credential")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "case-management-api", "database": "neon-postgres-ready"}


@app.get("/v1/integrations/swiftagents/config")
def swiftagents_widget_config() -> dict[str, Any]:
    """Return only the browser-safe SwiftAgents widget configuration."""
    has_creds = bool(settings.swiftagents_company_id and settings.swiftagents_public_key)
    return {
        "enabled": has_creds,
        "company_id": settings.swiftagents_company_id or "demo-company-uuid",
        "public_key": settings.swiftagents_public_key or "swa_live_demo_key",
        "widget_url": "https://widget.swiftagents.org/dist/widget-ui.js",
        "api_base_url": "https://api.swiftagents.org",
        "mock_mode": not has_creds,
    }


@app.get("/", include_in_schema=False)
def home() -> dict[str, str]:
    return {"status": "online", "docs": "/docs", "service": "Host Community Case Management"}


# ---------------------------------------------------------------------------
# Public & SwiftAgent Intake Endpoints
# ---------------------------------------------------------------------------

@app.post("/v1/public/complaints", response_model=CaseDetail, status_code=status.HTTP_201_CREATED)
async def submit_complaint(
    payload: ComplaintIntake,
    session: AsyncSession = Depends(get_session),
) -> CaseDetail:
    return await create_case(payload, session=session, actor="community_member")


@app.post(
    "/v1/agent/complaints",
    response_model=SwiftAgentToolResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_agent)],
)
async def agent_submit_complaint(
    payload: SwiftAgentComplaintInput,
    session: AsyncSession = Depends(get_session),
) -> SwiftAgentToolResponse:
    """Primary tool endpoint called by SwiftAgents AI during conversational intake."""
    return await handle_agent_complaint(payload, session=session)


@app.post("/v1/public/status", response_model=PublicCaseStatus)
async def check_public_status(
    payload: StatusLookup,
    session: AsyncSession = Depends(get_session),
) -> PublicCaseStatus:
    """Privacy-safe status lookup used by both web visitors and SwiftAgents."""
    return await public_status(payload, session=session)


@app.post("/v1/agent/webhook", status_code=status.HTTP_200_OK)
async def receive_swiftagents_webhook(
    payload: dict[str, Any],
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    """Receives event notifications from SwiftAgents (e.g. ticket created, escalated)."""
    return {"status": "received", "event": payload.get("event", "unknown")}


# ---------------------------------------------------------------------------
# Staff Operations Endpoints
# ---------------------------------------------------------------------------

@app.get("/v1/cases", response_model=list[CaseSummary], dependencies=[Depends(require_staff)])
async def get_cases(
    stage: str | None = None,
    queue: str | None = None,
    query: str | None = None,
    session: AsyncSession = Depends(get_session),
) -> list[CaseSummary]:
    return await list_cases(session=session, stage=stage, queue=queue, query=query)


@app.get("/v1/cases/{case_id}", response_model=CaseWithTimeline, dependencies=[Depends(require_staff)])
async def get_case(
    case_id: str,
    session: AsyncSession = Depends(get_session),
) -> CaseWithTimeline:
    return await get_case_or_404(case_id, session=session)


@app.post("/v1/cases/{case_id}/assignments", response_model=CaseDetail, dependencies=[Depends(require_staff)])
async def assign_case_officer(
    case_id: str,
    payload: CaseAssignment,
    session: AsyncSession = Depends(get_session),
) -> CaseDetail:
    return await assign_case(case_id, payload, session=session, actor="staff")


@app.post("/v1/cases/{case_id}/transitions", response_model=CaseDetail, dependencies=[Depends(require_staff)])
async def transition_case_stage(
    case_id: str,
    payload: CaseTransition,
    session: AsyncSession = Depends(get_session),
) -> CaseDetail:
    return await transition_case(case_id, payload, session=session, actor="staff")


@app.post("/v1/cases/{case_id}/notes", response_model=InvestigationNoteView, dependencies=[Depends(require_staff)])
async def create_note(
    case_id: str,
    payload: InvestigationNoteCreate,
    session: AsyncSession = Depends(get_session),
) -> InvestigationNoteView:
    return await add_note(case_id, payload, session=session, actor="staff")


@app.get("/v1/cases/{case_id}/notes", response_model=list[InvestigationNoteView], dependencies=[Depends(require_staff)])
async def get_notes(
    case_id: str,
    session: AsyncSession = Depends(get_session),
) -> list[InvestigationNoteView]:
    return await case_notes(case_id, session=session)


@app.post("/v1/cases/{case_id}/evidence", response_model=EvidenceView, dependencies=[Depends(require_staff)])
async def create_evidence(
    case_id: str,
    payload: EvidenceCreate,
    session: AsyncSession = Depends(get_session),
) -> EvidenceView:
    return await add_evidence(case_id, payload, session=session, actor="staff")


@app.get("/v1/cases/{case_id}/evidence", response_model=list[EvidenceView], dependencies=[Depends(require_staff)])
async def get_evidence(
    case_id: str,
    session: AsyncSession = Depends(get_session),
) -> list[EvidenceView]:
    return await case_evidence(case_id, session=session)


@app.get("/v1/cases/{case_id}/timeline", response_model=list[dict[str, Any]], dependencies=[Depends(require_staff)])
async def get_timeline(
    case_id: str,
    session: AsyncSession = Depends(get_session),
) -> list[dict[str, Any]]:
    events = await case_timeline(case_id, session=session)
    return [e.model_dump() for e in events]


@app.get("/v1/cases/{case_id}/notifications", response_model=list[NotificationView], dependencies=[Depends(require_staff)])
async def get_case_notifications(
    case_id: str,
    session: AsyncSession = Depends(get_session),
) -> list[NotificationView]:
    return await case_notifications(case_id, session=session)


@app.get("/v1/cases/{case_id}/export", response_model=CaseExport, dependencies=[Depends(require_staff)])
async def export_case_record(
    case_id: str,
    session: AsyncSession = Depends(get_session),
) -> CaseExport:
    return await export_case(case_id, session=session)


@app.get("/v1/reports/portfolio", response_model=PortfolioReport, dependencies=[Depends(require_staff)])
async def get_portfolio_report(
    session: AsyncSession = Depends(get_session),
) -> PortfolioReport:
    return await portfolio_report(session=session)


@app.get("/v1/agent/handoffs", response_model=list[HandoffView], dependencies=[Depends(require_staff)])
async def get_handoffs(
    session: AsyncSession = Depends(get_session),
) -> list[HandoffView]:
    return await list_handoffs(session=session)


@app.post("/v1/agent/handoffs/{handoff_id}/deliver", response_model=HandoffView, dependencies=[Depends(require_staff)])
async def retry_handoff(
    handoff_id: str,
    session: AsyncSession = Depends(get_session),
) -> HandoffView:
    return await deliver_handoff(handoff_id, session=session)


@app.get("/v1/notifications", response_model=list[NotificationView], dependencies=[Depends(require_staff)])
async def get_notifications(
    session: AsyncSession = Depends(get_session),
) -> list[NotificationView]:
    return await list_notifications(session=session)


@app.post("/v1/notifications/{notification_id}/deliver", response_model=NotificationView, dependencies=[Depends(require_staff)])
async def retry_notification(
    notification_id: str,
    session: AsyncSession = Depends(get_session),
) -> NotificationView:
    return await deliver_notification(notification_id, session=session)
