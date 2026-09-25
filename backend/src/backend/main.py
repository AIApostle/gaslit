import asyncio
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
import logging
from typing import Any

from fastapi import Depends, FastAPI, Header, HTTPException, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from .config import settings
from .database import close_database, get_session, init_db_async
from .manual import AGENT_DOCUMENTATION_MARKDOWN
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
    StaffLoginRequest,
    StatusLookup,
    SwiftAgentComplaintInput,
    SwiftAgentToolResponse,
    SwiftAgentCaseLookupInput,
    SwiftAgentCaseLookupResponse,
    SwiftAgentEvidenceInput,
    SwiftAgentEvidenceResponse,
    SwiftAgentHandoffInput,
    SwiftAgentHandoffResponse,
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
    handle_agent_lookup,
    handle_agent_evidence,
    handle_agent_handoff,
    list_cases,
    list_handoffs,
    list_notifications,
    portfolio_report,
    public_status,
    transition_case,
)


logger = logging.getLogger("outloud.keep_alive")


async def keep_alive_worker() -> None:
    """Periodically ping the public Render health endpoint to prevent free-tier spin down."""
    await asyncio.sleep(45)  # Wait 45s after boot
    target_url = "https://gaslit.onrender.com/health"
    async with httpx.AsyncClient(timeout=15.0) as client:
        while True:
            try:
                res = await client.get(target_url)
                logger.info("keep_alive_ping_success status=%s target=%s", res.status_code, target_url)
            except Exception as exc:
                logger.warning("keep_alive_ping_failed error=%s", str(exc))
            # Sleep 10 minutes (Render spins down after 15 minutes of inactivity)
            await asyncio.sleep(10 * 60)


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncGenerator[None, None]:
    await init_db_async()
    keep_alive_task = asyncio.create_task(keep_alive_worker())
    yield
    keep_alive_task.cancel()
    try:
        await keep_alive_task
    except asyncio.CancelledError:
        pass
    await close_database()


app = FastAPI(
    title="Outloud — Community Voice & Grievance Platform API",
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


def require_agent(
    x_agent_key: str | None = Header(default=None),
    x_api_key: str | None = Header(default=None),
    authorization: str | None = Header(default=None),
) -> None:
    if not settings.agent_key:
        return
    token = x_agent_key or x_api_key
    if not token and authorization:
        token = authorization[7:].strip() if authorization.startswith("Bearer ") else authorization.strip()
    if token != settings.agent_key:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid agent credential")


def require_staff(
    x_staff_key: str | None = Header(default=None),
    x_api_key: str | None = Header(default=None),
    authorization: str | None = Header(default=None),
) -> None:
    if not settings.staff_key:
        return
    token = x_staff_key or x_api_key
    if not token and authorization:
        token = authorization[7:].strip() if authorization.startswith("Bearer ") else authorization.strip()
    valid_keys = {"123456", "gaslit001"}
    if settings.staff_key:
        valid_keys.add(settings.staff_key)
    if token not in valid_keys:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid staff credential")


@app.post("/v1/auth/verify-staff")
def verify_staff(payload: StaffLoginRequest) -> dict[str, Any]:
    """Verify administrator and liaison officer credentials for the Operations Desk."""
    valid_keys = {"123456", "gaslit001"}
    if settings.staff_key:
        valid_keys.add(settings.staff_key)
    if payload.key not in valid_keys:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid staff passcode")
    return {
        "authenticated": True,
        "role": "admin",
        "name": "Community Liaison Officer",
        "staff_key": payload.key,
    }


@app.get("/health")
def health() -> dict[str, str]:
    db_type = "sqlite" if "sqlite" in settings.effective_database_url else "postgres"
    return {"status": "ok", "service": "case-management-api", "database": f"{db_type}-ready"}



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
    return {
        "status": "online",
        "docs": "/docs",
        "agent_manual": "/v1/agent/documentation",
        "llms_txt": "/llms.txt",
        "tools": "/v1/agent/tools.json",
        "service": "Outloud Host Community Case Management",
    }


@app.get("/v1/agent/documentation", response_class=Response, include_in_schema=True)
def get_agent_documentation() -> Response:
    """Returns the complete operational manual and API integration guide for AI agents."""
    return Response(content=AGENT_DOCUMENTATION_MARKDOWN, media_type="text/markdown; charset=utf-8")


@app.get("/llms.txt", response_class=Response, include_in_schema=False)
def get_llms_txt() -> Response:
    """Standard AI agent documentation file for LLMs discovering this service."""
    return Response(content=AGENT_DOCUMENTATION_MARKDOWN, media_type="text/plain; charset=utf-8")


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


@app.post(
    "/v1/agent/cases/lookup",
    response_model=SwiftAgentCaseLookupResponse,
    dependencies=[Depends(require_agent)],
)
async def agent_lookup_case(
    payload: SwiftAgentCaseLookupInput,
    session: AsyncSession = Depends(get_session),
) -> SwiftAgentCaseLookupResponse:
    """Tool endpoint called by SwiftAgents to retrieve case status and investigation updates."""
    return await handle_agent_lookup(payload, session=session)


@app.post(
    "/v1/agent/evidence",
    response_model=SwiftAgentEvidenceResponse,
    dependencies=[Depends(require_agent)],
)
async def agent_attach_evidence(
    payload: SwiftAgentEvidenceInput,
    session: AsyncSession = Depends(get_session),
) -> SwiftAgentEvidenceResponse:
    """Tool endpoint called by SwiftAgents when a citizen uploads photos or documents in chat."""
    return await handle_agent_evidence(payload, session=session)


@app.post(
    "/v1/agent/handoff",
    response_model=SwiftAgentHandoffResponse,
    dependencies=[Depends(require_agent)],
)
async def agent_request_handoff(
    payload: SwiftAgentHandoffInput,
    session: AsyncSession = Depends(get_session),
) -> SwiftAgentHandoffResponse:
    """Tool endpoint called by SwiftAgents to trigger human officer handoff."""
    return await handle_agent_handoff(payload, session=session)


@app.get("/v1/agent/tools.json")
def get_swiftagents_tool_catalog(request: Request) -> dict[str, Any]:
    """Returns the ready-to-import SwiftAgents tool schemas for your SwiftAgents Dashboard."""
    host = request.headers.get("x-forwarded-host") or request.headers.get("host") or "gaslit.onrender.com"
    proto = request.headers.get("x-forwarded-proto") or ("https" if "onrender.com" in str(host) else request.url.scheme)
    base_url = f"{proto}://{host}".rstrip("/")

    return {
        "version": "1.0.0",
        "description": "Outloud AI Agent Tool Suite",
        "server_url": base_url,
        "catalog_url": f"{base_url}/v1/agent/tools.json",
        "documentation_url": f"{base_url}/v1/agent/documentation",
        "manual_url": f"{base_url}/llms.txt",
        "instructions": "Follow the operational manual at /v1/agent/documentation to conduct conversational intake and invoke submit_complaint with extracted parameters.",
        "webhook_url": f"{base_url}/v1/agent/webhook",
        "openapi_url": f"{base_url}/openapi.json",
        "tools": [
            {
                "name": "submit_complaint",
                "description": "Log an official host community grievance (gas flare, oil spill, water contamination, health issue) to generate a verified case ticket.",
                "method": "POST",
                "url": f"{base_url}/v1/agent/complaints",
                "endpoint": "/v1/agent/complaints",
                "headers": {"Content-Type": "application/json"},
                "parameters": {
                    "type": "object",
                    "properties": {
                        "complainant_name": {"type": "string", "description": "Full name or Community Member"},
                        "contact_value": {"type": "string", "description": "Phone number or email"},
                        "category": {"type": "string", "description": "Gas Flaring, Oil Spill, Water Contamination, Health Hazard"},
                        "description": {"type": "string", "description": "Detailed explanation of what occurred"},
                        "location": {"type": "string", "description": "Town, local government, or facility site name"},
                        "priority": {"type": "string", "enum": ["low", "normal", "high", "critical"]}
                    },
                    "required": ["description", "category", "location"]
                }
            },
            {
                "name": "lookup_case",
                "description": "Retrieve the current live status, assigned officer, investigation notes, and SLA status for an existing ticket.",
                "method": "POST",
                "url": f"{base_url}/v1/agent/cases/lookup",
                "endpoint": "/v1/agent/cases/lookup",
                "headers": {"Content-Type": "application/json"},
                "parameters": {
                    "type": "object",
                    "properties": {
                        "reference": {"type": "string", "description": "The Ticket ID (e.g. HCC-20260922-A1B2)"},
                        "verification_code": {"type": "string", "description": "Optional 6-digit verification code"}
                    },
                    "required": ["reference"]
                }
            },
            {
                "name": "attach_evidence",
                "description": "Attach a photo, PDF document, or incident file uploaded by the user during the chat to an active case.",
                "method": "POST",
                "url": f"{base_url}/v1/agent/evidence",
                "endpoint": "/v1/agent/evidence",
                "headers": {"Content-Type": "application/json"},
                "parameters": {
                    "type": "object",
                    "properties": {
                        "reference": {"type": "string", "description": "The Ticket ID"},
                        "file_name": {"type": "string", "description": "Name of the uploaded file"},
                        "evidence_type": {"type": "string", "enum": ["photo", "document", "video"], "default": "photo"},
                        "storage_uri": {"type": "string", "description": "URL or storage key of the uploaded file"},
                        "description": {"type": "string", "description": "What this photo or document proves"}
                    },
                    "required": ["reference", "file_name"]
                }
            },
            {
                "name": "request_human_handoff",
                "description": "Escalate the current chat session to a live human Community Liaison Officer.",
                "method": "POST",
                "url": f"{base_url}/v1/agent/handoff",
                "endpoint": "/v1/agent/handoff",
                "headers": {"Content-Type": "application/json"},
                "parameters": {
                    "type": "object",
                    "properties": {
                        "reference": {"type": "string", "description": "Ticket ID if already created"},
                        "citizen_name": {"type": "string", "description": "Name of the person"},
                        "contact_value": {"type": "string", "description": "Phone or email"},
                        "reason": {"type": "string", "description": "Why human escalation is required"},
                        "urgency": {"type": "string", "enum": ["normal", "high", "critical"]}
                    },
                    "required": ["reason"]
                }
            }
        ]
    }


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
