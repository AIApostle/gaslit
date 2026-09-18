from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, Header, HTTPException, status
from fastapi.staticfiles import StaticFiles

from .config import settings
from .database import initialize_database
from .schemas import (
    CaseAssignment,
    CaseStage,
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
    CaseTransition,
    CaseDetail,
    CaseSummary,
    CaseExport,
)
from .service import (
    PUBLIC_STATUS_MESSAGES,
    add_evidence,
    add_note,
    assign_case,
    case_evidence,
    case_notes,
    case_notifications,
    case_timeline,
    create_case,
    deliver_notification,
    export_case,
    get_case_or_404,
    list_cases,
    list_handoffs,
    list_notifications,
    deliver_handoff,
    portfolio_report,
    public_status,
    transition_case,
)


@asynccontextmanager
async def lifespan(_: FastAPI):
    initialize_database()
    yield


app = FastAPI(title="Host Community Case Management API", version="0.1.0", lifespan=lifespan)
STATIC_DIR = Path(__file__).resolve().parent / "static"
app.mount("/app", StaticFiles(directory=STATIC_DIR, html=True), name="app")


def require_agent(x_agent_key: str | None = Header(default=None)) -> None:
    if settings.agent_key and x_agent_key != settings.agent_key:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid agent credential")


def require_staff(x_staff_key: str | None = Header(default=None)) -> None:
    if settings.staff_key and x_staff_key != settings.staff_key:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid staff credential")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "case-management-api"}


@app.get("/v1/integrations/swiftagents/config")
def swiftagents_widget_config() -> dict[str, str | bool | None]:
    """Return only the browser-safe SwiftAgents widget configuration."""
    enabled = bool(settings.swiftagents_company_id and settings.swiftagents_public_key)
    return {
        "enabled": enabled,
        "company_id": settings.swiftagents_company_id if enabled else None,
        "public_key": settings.swiftagents_public_key if enabled else None,
        "widget_url": "https://widget.swiftagents.org/dist/widget-ui.js",
        "api_base_url": "https://api.swiftagents.org",
    }


@app.get("/", include_in_schema=False)
def home() -> dict[str, str]:
    return {"app": "/app/", "docs": "/docs"}


@app.post("/v1/public/complaints", response_model=CaseDetail, status_code=status.HTTP_201_CREATED)
def submit_complaint(payload: ComplaintIntake) -> CaseDetail:
    return create_case(payload, actor="community_member")


@app.post("/v1/agent/complaints", response_model=CaseDetail, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_agent)])
def submit_agent_complaint(payload: ComplaintIntake) -> CaseDetail:
    payload.source_channel = "swiftagents"
    return create_case(payload, actor="swiftagents")


@app.post("/v1/public/status", response_model=PublicCaseStatus)
def lookup_public_status(payload: StatusLookup) -> PublicCaseStatus:
    case = public_status(payload.reference, payload.verification_code, payload.contact_value)
    return PublicCaseStatus(
        reference=case.reference,
        stage=case.stage,
        status_message=PUBLIC_STATUS_MESSAGES[case.stage],
        updated_at=case.updated_at,
        sla_status=case.sla_status,
    )


@app.get("/v1/cases", response_model=list[CaseSummary], dependencies=[Depends(require_staff)])
def get_cases(stage: CaseStage | None = None, queue: str | None = None) -> list[CaseSummary]:
    return list_cases(stage, queue)


@app.get("/v1/cases/{case_id}", response_model=CaseWithTimeline, dependencies=[Depends(require_staff)])
def get_case(case_id: str) -> CaseWithTimeline:
    case = get_case_or_404(case_id)
    return CaseWithTimeline(case=CaseDetail(**dict(case)), events=case_timeline(case_id))


@app.post("/v1/cases/{case_id}/assignments", response_model=CaseDetail, dependencies=[Depends(require_staff)])
def assign(case_id: str, payload: CaseAssignment) -> CaseDetail:
    return assign_case(case_id, payload, actor="staff")


@app.post("/v1/cases/{case_id}/transitions", response_model=CaseDetail, dependencies=[Depends(require_staff)])
def transition(case_id: str, payload: CaseTransition) -> CaseDetail:
    return transition_case(case_id, payload, actor="staff")


@app.post("/v1/cases/{case_id}/notes", response_model=InvestigationNoteView, dependencies=[Depends(require_staff)])
def create_note(case_id: str, payload: InvestigationNoteCreate) -> InvestigationNoteView:
    return add_note(case_id, payload, actor="staff")


@app.get("/v1/cases/{case_id}/notes", response_model=list[InvestigationNoteView], dependencies=[Depends(require_staff)])
def get_notes(case_id: str) -> list[InvestigationNoteView]:
    return case_notes(case_id)


@app.post("/v1/cases/{case_id}/evidence", response_model=EvidenceView, dependencies=[Depends(require_staff)])
def create_evidence(case_id: str, payload: EvidenceCreate) -> EvidenceView:
    return add_evidence(case_id, payload, actor="staff")


@app.get("/v1/cases/{case_id}/evidence", response_model=list[EvidenceView], dependencies=[Depends(require_staff)])
def get_evidence(case_id: str) -> list[EvidenceView]:
    return case_evidence(case_id)


@app.get("/v1/cases/{case_id}/notifications", response_model=list[NotificationView], dependencies=[Depends(require_staff)])
def get_case_notifications(case_id: str) -> list[NotificationView]:
    return case_notifications(case_id)


@app.get("/v1/cases/{case_id}/export", response_model=CaseExport, dependencies=[Depends(require_staff)])
def get_case_export(case_id: str) -> CaseExport:
    return export_case(case_id)


@app.get("/v1/reports/portfolio", response_model=PortfolioReport, dependencies=[Depends(require_staff)])
def get_portfolio_report() -> PortfolioReport:
    return portfolio_report()


@app.get("/v1/agent/handoffs", response_model=list[HandoffView], dependencies=[Depends(require_staff)])
def get_agent_handoffs() -> list[HandoffView]:
    return list_handoffs()


@app.post("/v1/agent/handoffs/{handoff_id}/deliver", response_model=HandoffView, dependencies=[Depends(require_staff)])
def deliver_agent_handoff(handoff_id: str) -> HandoffView:
    return deliver_handoff(handoff_id)


@app.get("/v1/notifications", response_model=list[NotificationView], dependencies=[Depends(require_staff)])
def get_notifications() -> list[NotificationView]:
    return list_notifications()


@app.post("/v1/notifications/{notification_id}/deliver", response_model=NotificationView, dependencies=[Depends(require_staff)])
def retry_notification(notification_id: str) -> NotificationView:
    return deliver_notification(notification_id)
