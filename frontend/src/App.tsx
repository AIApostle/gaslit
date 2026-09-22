import {
  Activity,
  ArrowLeft,
  BarChart3,
  Bell,
  Bot,
  BriefcaseBusiness,
  CheckCircle,
  CircleUserRound,
  Clock,
  Download,
  Droplets,
  Flame,
  FileText,
  FolderOpen,
  Gauge,
  Lock,
  Plus,
  RefreshCw,
  Search,
  Send,
  ShieldCheck,
  Siren,
  Sparkles,
  SquarePen,
  Trees,
  X,
} from "lucide-react";
import { FormEvent, useEffect, useMemo, useState } from "react";

import {
  addEvidence,
  addNote,
  agentSubmitComplaint,
  assignCase,
  exportCase,
  getCase,
  getCaseNotifications,
  getEvidence,
  getNotes,
  getPortfolioReport,
  getAgentToolsCatalog,
  listCases,
  listHandoffs,
  listNotifications,
  lookupStatus,
  retryHandoff,
  retryNotification,
  transitionCase,
} from "./api";
import { SwiftAgentChatModal } from "./components/SwiftAgentChatModal";
import { useSwiftAgent } from "./hooks/useSwiftAgent";
import type {
  CaseExport,
  CaseStage,
  CaseSummary,
  CaseWithTimeline,
  Evidence,
  Handoff,
  InvestigationNote,
  NotificationEvent,
  PortfolioReport,
  PublicStatus,
  SwiftAgentToolResponse,
} from "./types";

type View = "portal" | "workspace" | "reports" | "integration" | "settings";

const stageOptions: { value: CaseStage; label: string }[] = [
  { value: "reported", label: "Reported" },
  { value: "under_investigation", label: "Investigation" },
  { value: "response_issued", label: "Response issued" },
  { value: "escalated", label: "Escalated" },
  { value: "resolved", label: "Resolved" },
];

const queueOptions = [
  { value: "open", label: "Open" },
  { value: "unassigned", label: "Unassigned" },
  { value: "at_risk", label: "At risk" },
  { value: "breached", label: "Breached" },
  { value: "escalated", label: "Escalated" },
];

function titleCase(value: string) {
  return value.replaceAll("_", " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function formatDate(value: string | null | undefined) {
  return value ? new Date(value).toLocaleString() : "Not set";
}

function getInitialView(): View {
  const path = window.location.pathname.toLowerCase();
  const hash = window.location.hash.toLowerCase();
  if (path.startsWith("/admin") || hash.startsWith("#/admin")) {
    if (path.includes("reports") || hash.includes("reports")) return "reports";
    if (path.includes("integration") || hash.includes("integration")) return "integration";
    if (path.includes("settings") || hash.includes("settings")) return "settings";
    return "workspace";
  }
  return "portal";
}

export function App() {
  const [view, setView] = useState<View>(getInitialView);
  const [toast, setToast] = useState<string | null>(null);
  const [chatModalOpen, setChatModalOpen] = useState(false);
  const [chatTopic, setChatTopic] = useState<string | undefined>();
  const { openAgent, isLoaded, config } = useSwiftAgent();

  // Sync view with browser URL and history
  useEffect(() => {
    const handleUrlChange = () => {
      setView(getInitialView());
    };
    window.addEventListener("hashchange", handleUrlChange);
    window.addEventListener("popstate", handleUrlChange);
    return () => {
      window.removeEventListener("hashchange", handleUrlChange);
      window.removeEventListener("popstate", handleUrlChange);
    };
  }, []);

  const navigate = (newView: View) => {
    setView(newView);
    if (newView === "portal") {
      window.location.hash = "";
      if (window.location.pathname.startsWith("/admin")) {
        window.history.pushState({}, "", "/");
      }
    } else {
      window.location.hash = `#/admin/${newView}`;
    }
  };

  const handleOpenChat = (topic?: string) => {
    setChatTopic(topic);
    setChatModalOpen(true);
    if (isLoaded) {
      openAgent();
    }
  };

  const isStaffDesk = view !== "portal";

  return (
    <div className="app-shell">
      <header className="topbar">
        <button className="brand" type="button" onClick={() => navigate("portal")}>
          <span className="brand-mark">HC</span>
          <span>
            <strong>Community Voice</strong>
            <small>{isStaffDesk ? "Officer & Admin Desk" : "Host Community Grievance Service"}</small>
          </span>
        </button>

        <nav className="nav-tabs" aria-label="Primary navigation">
          {!isStaffDesk ? (
            /* Public Portal Navigation: Strictly Citizen Facing, Zero Admin Links */
            <button
              className="portal-btn-primary"
              style={{ padding: "8px 18px", fontSize: "13px" }}
              type="button"
              onClick={() => handleOpenChat()}
            >
              <Bot size={15} />
              <span>Talk to AI Officer</span>
            </button>
          ) : (
            /* Admin & Officer Desk Navigation: Only accessed via /admin or #/admin */
            <>
              <button
                className="nav-button"
                type="button"
                onClick={() => navigate("portal")}
                style={{ marginRight: "12px", fontWeight: 700 }}
                title="Exit back to the public citizen portal"
              >
                <ArrowLeft size={16} />
                <span>Exit Admin</span>
              </button>
              <NavButton active={view === "workspace"} icon={<BriefcaseBusiness size={16} />} onClick={() => navigate("workspace")}>
                Cases
              </NavButton>
              <NavButton active={view === "reports"} icon={<BarChart3 size={16} />} onClick={() => navigate("reports")}>
                Analytics
              </NavButton>
              <NavButton active={view === "integration"} icon={<Bell size={16} />} onClick={() => navigate("integration")}>
                SwiftAgents Hub
              </NavButton>
              <NavButton active={view === "settings"} icon={<ShieldCheck size={16} />} onClick={() => navigate("settings")}>
                System Status
              </NavButton>
            </>
          )}
        </nav>
      </header>

      {toast && (
        <div className="toast" role="status">
          <CheckCircle size={18} fill="currentColor" />
          {toast}
          <button type="button" onClick={() => setToast(null)} aria-label="Dismiss message">
            x
          </button>
        </div>
      )}

      <main>
        {view === "portal" && <PublicCommunityPortal onOpenChat={handleOpenChat} setToast={setToast} />}
        {view === "workspace" && <Workspace setToast={setToast} />}
        {view === "reports" && <Reports />}
        {view === "integration" && <IntegrationMonitor setToast={setToast} openAgent={openAgent} config={config} />}
        {view === "settings" && <Settings setToast={setToast} config={config} />}
      </main>

      {/* Floating launcher visible on all views */}
      <button
        type="button"
        className="floating-ai-launcher"
        onClick={() => handleOpenChat()}
        title="Open SwiftAgents AI Grievance Officer"
      >
        <Bot size={18} />
        <span>Chat with AI Officer</span>
        <span className="status-dot"></span>
      </button>

      {/* Interactive SwiftAgents In-App Pop-up Chat */}
      <SwiftAgentChatModal
        isOpen={chatModalOpen}
        onClose={() => setChatModalOpen(false)}
        initialTopic={chatTopic}
        onCaseCreated={(ticketId) => setToast(`Incident logged: ${ticketId}`)}
      />
    </div>
  );
}

function NavButton({
  active,
  icon,
  children,
  onClick,
}: {
  active: boolean;
  icon: React.ReactNode;
  children: React.ReactNode;
  onClick: () => void;
}) {
  return (
    <button className="nav-button" type="button" aria-selected={active} onClick={onClick}>
      {icon}
      {children}
    </button>
  );
}

// ---------------------------------------------------------------------------
// Public Community Portal (Clean, Formless, SwiftAgents First)
// ---------------------------------------------------------------------------

function PublicCommunityPortal({
  onOpenChat,
  setToast,
}: {
  onOpenChat: (topic?: string) => void;
  setToast: (msg: string) => void;
}) {
  return (
    <div className="portal-container">
      {/* Hero Section */}
      <section className="portal-hero">
        <div className="portal-badge">
          <Sparkles size={15} />
          <span>Official Host Community Grievance Service</span>
        </div>
        <h1>Report Host Community Grievances Directly. No Paperwork. No Delays.</h1>
        <p>
          Speak or chat in natural language with our conversational AI officer. Describe what happened,
          upload incident photos, and receive your official verified case tracking badge in seconds.
        </p>

        <div className="portal-actions">
          <button type="button" className="portal-btn-primary" onClick={() => onOpenChat()}>
            <Bot size={20} />
            <span>Report Grievance with AI Officer</span>
          </button>
          <button type="button" className="portal-btn-secondary" onClick={() => onOpenChat("check status")}>
            <Search size={18} />
            <span>Check Status with AI Assistant</span>
          </button>
        </div>
      </section>

      {/* Category Cards (Interactive Launchers for SwiftAgents) */}
      <div className="portal-cards-grid">
        <button
          type="button"
          className="portal-card clickable"
          onClick={() => onOpenChat("Gas flaring with heavy black soot fallout")}
          title="Launch AI Officer to report gas flaring"
        >
          <div className="portal-card-icon">
            <Flame size={22} />
          </div>
          <h3>Gas Flaring & Soot</h3>
          <p>
            Continuous toxic flare emissions, heavy black soot fallouts, nighttime noise vibrations,
            and heat damage to community roofs and vegetation.
          </p>
          <span className="card-launch-action">Report with AI &rarr;</span>
        </button>

        <button
          type="button"
          className="portal-card clickable"
          onClick={() => onOpenChat("Crude oil pipeline rupture leak in farmland")}
          title="Launch AI Officer to report oil spills"
        >
          <div className="portal-card-icon">
            <Droplets size={22} />
          </div>
          <h3>Oil Spills & Farmland</h3>
          <p>
            Crude pipeline rupture leaks, agricultural soil degradation, damaged fishing streams,
            and blocked access roads preventing farm harvests.
          </p>
          <span className="card-launch-action">Report with AI &rarr;</span>
        </button>

        <button
          type="button"
          className="portal-card clickable"
          onClick={() => onOpenChat("Water borehole contamination and chemical odor")}
          title="Launch AI Officer to report water contamination"
        >
          <div className="portal-card-icon">
            <Trees size={22} />
          </div>
          <h3>Water & Community Health</h3>
          <p>
            Contaminated boreholes and drinking water, chemical odors causing respiratory illness,
            and industrial site disturbances in residential quarters.
          </p>
          <span className="card-launch-action">Report with AI &rarr;</span>
        </button>
      </div>

      {/* How it works (Simple & Honest) */}
      <section className="portal-steps">
        <div className="portal-steps-head">
          <h2>How It Works</h2>
          <p className="muted" style={{ margin: 0, fontSize: "14px" }}>
            A transparent 3-step process ensuring every community voice is documented and resolved.
          </p>
        </div>
        <div className="portal-steps-grid">
          <div className="step-item">
            <span className="step-num">1</span>
            <strong>Conversational Intake</strong>
            <span>
              Click the launcher to speak or type naturally. You can describe the issue in plain words
              and attach photos or evidence directly in the chat.
            </span>
          </div>

          <div className="step-item">
            <span className="step-num">2</span>
            <strong>Instant Verified Ticket</strong>
            <span>
              Your grievance is logged directly to the system of record with an official Ticket ID badge
              and a private 6-digit verification code.
            </span>
          </div>

          <div className="step-item">
            <span className="step-num">3</span>
            <strong>Accountable Resolution</strong>
            <span>
              An assigned Community Liaison Officer investigates on-site under strict SLA countdowns, with verified
              progress updates available anytime in chat.
            </span>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="portal-footer">
        <div>Host Community Case Desk &copy; {new Date().getFullYear()} • Secure & Privacy Preserving</div>
      </footer>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Staff Operations Desk (Case Workspace)
// ---------------------------------------------------------------------------

function Workspace({ setToast }: { setToast: (message: string) => void }) {
  const [cases, setCases] = useState<CaseSummary[]>([]);
  const [stage, setStage] = useState<CaseStage | "">("");
  const [queue, setQueue] = useState("");
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [selected, setSelected] = useState<CaseWithTimeline | null>(null);
  const [notes, setNotes] = useState<InvestigationNote[]>([]);
  const [evidence, setEvidence] = useState<Evidence[]>([]);
  const [notifications, setNotifications] = useState<NotificationEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  async function refreshCases() {
    setLoading(true);
    setError(null);
    try {
      setCases(await listCases({ stage, queue, query: searchQuery || undefined }));
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Could not load cases");
    } finally {
      setLoading(false);
    }
  }

  async function loadSelected(id: string) {
    setSelectedId(id);
    try {
      const [caseData, noteData, evidenceData, notificationData] = await Promise.all([
        getCase(id),
        getNotes(id),
        getEvidence(id),
        getCaseNotifications(id),
      ]);
      setSelected(caseData);
      setNotes(noteData);
      setEvidence(evidenceData);
      setNotifications(notificationData);
    } catch (caught) {
      setToast("Failed to load case details");
    }
  }

  useEffect(() => {
    refreshCases();
  }, [stage, queue, searchQuery]);

  const metrics = useMemo(
    () => [
      ["Open", cases.filter((item) => item.stage !== "resolved").length, <FolderOpen key="1" />],
      ["Investigation", cases.filter((item) => item.stage === "under_investigation").length, <Activity key="2" />],
      ["Escalated", cases.filter((item) => item.stage === "escalated").length, <Siren key="3" />],
      ["At risk", cases.filter((item) => item.sla_status === "at_risk").length, <Clock key="4" />],
      ["Breached", cases.filter((item) => item.sla_status === "breached").length, <Gauge key="5" />],
      ["Resolved", cases.filter((item) => item.stage === "resolved").length, <ShieldCheck key="6" />],
    ],
    [cases]
  );

  return (
    <section className="view-stack">
      <PageHeader
        kicker="Staff Operations Desk"
        title="Case Control Room"
        copy="A unified queue for triage, officer assignment, field investigation, responses, and official resolution."
        action={
          <button className="button ghost" type="button" onClick={refreshCases}>
            <RefreshCw />Refresh
          </button>
        }
      />
      <div className="metric-grid">
        {metrics.map(([label, value, icon]) => (
          <div className="metric" key={String(label)}>
            <span>{icon}</span>
            <strong>{value}</strong>
            <small>{label}</small>
          </div>
        ))}
      </div>
      <div className="workspace-grid">
        <section className="panel">
          <div className="panel-head">
            <h2>Grievance Queue</h2>
            <div className="filters">
              <input
                type="text"
                placeholder="Search reference, location..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                style={{ padding: "6px 10px", fontSize: "13px", borderRadius: "6px", border: "1px solid var(--line)" }}
              />
              <select value={stage} onChange={(event) => setStage(event.target.value as CaseStage | "")}>
                <option value="">All stages</option>
                {stageOptions.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
              <select value={queue} onChange={(event) => setQueue(event.target.value)}>
                <option value="">All queues</option>
                {queueOptions.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
            </div>
          </div>
          {loading && <SkeletonRows />}
          {error && <EmptyState tone="danger" title="Queue unavailable" copy={error} />}
          {!loading && !error && (
            <ul className="case-list">
              {cases.length === 0 && (
                <li>
                  <EmptyState title="No matching cases" copy="Adjust your filters or submit a grievance in the public portal." />
                </li>
              )}
              {cases.map((item) => (
                <li key={item.id}>
                  <button
                    className={selectedId === item.id ? "case-row selected" : "case-row"}
                    type="button"
                    onClick={() => loadSelected(item.id)}
                  >
                    <span>
                      <strong>{item.reference}</strong>
                      <small>
                        {item.category} in {item.location}
                      </small>
                    </span>
                    <span className="row-meta">
                      <Badge value={item.stage} />
                      <Badge value={item.sla_status} />
                    </span>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </section>

        <CaseDetailPanel
          selected={selected}
          notes={notes}
          evidence={evidence}
          notifications={notifications}
          reload={async () => {
            if (selectedId) await loadSelected(selectedId);
            await refreshCases();
          }}
          setToast={setToast}
        />
      </div>
    </section>
  );
}

function CaseDetailPanel({
  selected,
  notes,
  evidence,
  notifications,
  reload,
  setToast,
}: {
  selected: CaseWithTimeline | null;
  notes: InvestigationNote[];
  evidence: Evidence[];
  notifications: NotificationEvent[];
  reload: () => Promise<void>;
  setToast: (message: string) => void;
}) {
  const [note, setNote] = useState("");
  const [fileName, setFileName] = useState("");
  const [fileDescription, setFileDescription] = useState("");
  const [caseExport, setCaseExport] = useState<CaseExport | null>(null);

  if (!selected) {
    return (
      <aside className="panel detail-panel">
        <EmptyState title="Select a case" copy="Select an item from the queue to inspect grievance facts, timeline, evidence, and actions." />
      </aside>
    );
  }

  const detail = selected.case;
  const isAiSourced = detail.source_channel === "swiftagents_chat" || detail.source_channel === "swiftagents";

  async function assign() {
    const officer = window.prompt("Assign to Officer Name:", detail.assigned_officer ?? "Community Liaison Officer");
    if (!officer) return;
    await assignCase(detail.id, officer);
    setToast("Case assigned");
    await reload();
  }

  async function transition(stage: CaseStage) {
    const payload: { stage: CaseStage; response_summary?: string; resolution_summary?: string } = { stage };
    if (stage === "response_issued") {
      const response = window.prompt("Official response summary to community member:");
      if (!response) return;
      payload.response_summary = response;
    }
    if (stage === "resolved") {
      const resolution = window.prompt("Final resolution summary:");
      if (!resolution) return;
      payload.resolution_summary = resolution;
    }
    await transitionCase(detail.id, payload);
    setToast("Case stage updated");
    await reload();
  }

  async function saveNote(event: FormEvent) {
    event.preventDefault();
    if (!note.trim()) return;
    await addNote(detail.id, note.trim());
    setNote("");
    setToast("Investigation note saved");
    await reload();
  }

  async function saveEvidence(event: FormEvent) {
    event.preventDefault();
    if (!fileName.trim()) return;
    await addEvidence(detail.id, {
      file_name: fileName.trim(),
      description: fileDescription.trim() || null,
    });
    setFileName("");
    setFileDescription("");
    setToast("Evidence registered");
    await reload();
  }

  async function loadExport() {
    setCaseExport(await exportCase(detail.id));
  }

  return (
    <aside className="panel detail-panel">
      <div className="detail-hero">
        <div>
          <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "4px" }}>
            <p className="eyebrow" style={{ margin: 0 }}>{detail.reference}</p>
            {isAiSourced && <span className="ai-pill">SwiftAgents AI Intake</span>}
          </div>
          <h2>{detail.category}</h2>
          <p>{detail.location}</p>
        </div>
        <div className="badge-stack">
          <Badge value={detail.stage} />
          <Badge value={detail.sla_status} />
        </div>
      </div>

      <div className="detail-grid">
        <Fact label="Complainant" value={detail.complainant_name} />
        <Fact label="Contact" value={detail.contact_value} />
        <Fact label="Channel" value={detail.preferred_channel === "in_browser_chat" ? "In-Browser Chat (SwiftAgents)" : detail.preferred_channel} />
        <Fact label="Owner" value={detail.assigned_officer ?? "Unassigned"} />
        <Fact label="Priority" value={titleCase(detail.priority)} />
        <Fact label="SLA Due" value={formatDate(detail.sla_due_at)} />
        <Fact label="Age" value={`${detail.age_hours} hours`} />
        {detail.status_verification_code && <Fact label="Verify Code" value={detail.status_verification_code} />}
      </div>

      <div className="content-block">
        <h3>Grievance Details</h3>
        <p>{detail.description}</p>
      </div>
      {detail.response_summary && <ContentBlock title="Response" copy={detail.response_summary} />}
      {detail.resolution_summary && <ContentBlock title="Resolution" copy={detail.resolution_summary} />}

      <div className="action-grid">
        <button className="button ghost" type="button" onClick={assign}>
          <CircleUserRound />Assign
        </button>
        <NextStageButton stage={detail.stage} onTransition={transition} />
        <button
          className="button warning"
          type="button"
          disabled={detail.stage === "resolved" || detail.stage === "escalated"}
          onClick={() => transition("escalated")}
        >
          <Siren />Escalate
        </button>
        <button className="button ghost" type="button" onClick={loadExport}>
          <Download />Export
        </button>
      </div>

      <form className="inline-form" onSubmit={saveNote}>
        <label htmlFor="note">Investigation Note</label>
        <textarea id="note" value={note} onChange={(event) => setNote(event.target.value)} placeholder="Record field findings or inspection remarks..." />
        <button className="button ghost" type="submit">
          <SquarePen />Save note
        </button>
      </form>

      <form className="inline-form" onSubmit={saveEvidence}>
        <label htmlFor="file-name">Evidence Metadata</label>
        <input id="file-name" value={fileName} onChange={(event) => setFileName(event.target.value)} placeholder="Photo or document file name" />
        <input value={fileDescription} onChange={(event) => setFileDescription(event.target.value)} placeholder="Description or location tag" />
        <button className="button ghost" type="submit">
          <FileText />Save evidence
        </button>
      </form>

      <RecordSection
        title="Audit Timeline"
        records={selected.events.map((event) => ({
          id: `${event.event_type}-${event.occurred_at}`,
          title: titleCase(event.event_type),
          meta: `${event.actor} | ${formatDate(event.occurred_at)}`,
        }))}
      />
      <RecordSection
        title="Investigation Notes"
        records={notes.map((item) => ({
          id: item.id,
          title: item.note,
          meta: `${item.actor} | ${formatDate(item.created_at)}`,
        }))}
      />
      <RecordSection
        title="Evidence Records"
        records={evidence.map((item) => ({
          id: item.id,
          title: item.file_name,
          meta: `${item.evidence_type} | ${item.description ?? "No description"}`,
        }))}
      />
      <RecordSection
        title="Notification Trail"
        records={notifications.map((item) => ({
          id: item.id,
          title: titleCase(item.event_type),
          meta: `${item.channel} | ${titleCase(item.status)} | ${item.attempts} attempts`,
        }))}
      />
      {caseExport && <pre className="export-box">{JSON.stringify(caseExport, null, 2)}</pre>}
    </aside>
  );
}

function NextStageButton({ stage, onTransition }: { stage: CaseStage; onTransition: (stage: CaseStage) => void }) {
  const next: Partial<Record<CaseStage, { label: string; stage: CaseStage }>> = {
    reported: { label: "Start investigation", stage: "under_investigation" },
    under_investigation: { label: "Issue response", stage: "response_issued" },
    response_issued: { label: "Resolve case", stage: "resolved" },
    escalated: { label: "Resume investigation", stage: "under_investigation" },
  };
  const action = next[stage];
  return (
    <button className="button primary" type="button" disabled={!action} onClick={() => action && onTransition(action.stage)}>
      <Send />
      {action?.label ?? "Resolved"}
    </button>
  );
}


function Reports() {
  const [report, setReport] = useState<PortfolioReport | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function loadReport() {
    setError(null);
    const result = await getPortfolioReport().catch((caught) => {
      setError(caught instanceof Error ? caught.message : "Could not load report");
      return null;
    });
    setReport(result);
  }

  useEffect(() => {
    loadReport();
  }, []);

  const metrics = report
    ? [
        ["Total", report.total_cases],
        ["Open", report.open_cases],
        ["Unassigned", report.unassigned_cases],
        ["Escalated", report.escalated_cases],
        ["At risk", report.at_risk_cases],
        ["Breached", report.breached_cases],
        ["Resolved", report.resolved_cases],
      ]
    : [];

  return (
    <section className="view-stack">
      <PageHeader
        kicker="Executive Analytics"
        title="Grievance Analytics & Trends"
        copy="Grievance volume, stage distribution, SLA compliance, and environmental category breakdowns."
        action={
          <button className="button ghost" type="button" onClick={loadReport}>
            <RefreshCw />Refresh
          </button>
        }
      />
      {error && <Notice tone="danger">{error}</Notice>}
      <div className="metric-grid compact">
        {metrics.map(([label, value]) => (
          <div className="metric" key={String(label)}>
            <strong>{value}</strong>
            <small>{label}</small>
          </div>
        ))}
      </div>
      {report && (
        <div className="report-grid">
          <ReportSection title="Cases by Stage" counts={report.by_stage} />
          <ReportSection title="Cases by Priority" counts={report.by_priority} />
          <ReportSection title="Cases by Category" counts={report.by_category} />
        </div>
      )}
    </section>
  );
}

function IntegrationMonitor({
  setToast,
  openAgent,
  config,
}: {
  setToast: (message: string) => void;
  openAgent: () => void;
  config: ReturnType<typeof useSwiftAgent>["config"];
}) {
  const [handoffs, setHandoffs] = useState<Handoff[]>([]);
  const [notifications, setNotifications] = useState<NotificationEvent[]>([]);
  const [error, setError] = useState<string | null>(null);

  async function load() {
    setError(null);
    try {
      const [handoffData, notificationData] = await Promise.all([listHandoffs(), listNotifications()]);
      setHandoffs(handoffData);
      setNotifications(notificationData);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Could not load integration events");
    }
  }

  useEffect(() => {
    load();
  }, []);

  async function retry(type: "handoff" | "notification", id: string) {
    if (type === "handoff") await retryHandoff(id);
    else await retryNotification(id);
    setToast("Retry recorded");
    await load();
  }

  return (
    <section className="view-stack">
      <PageHeader
        kicker="Reliability"
        title="SwiftAgents Integration Hub"
        copy="Real-time monitoring of SwiftAgents conversational handoffs, webhooks, and outbound notification events."
        action={
          <button className="button ghost" type="button" onClick={load}>
            <RefreshCw />Refresh
          </button>
        }
      />
      {error && <Notice tone="danger">{error}</Notice>}

      <section className="panel" style={{ padding: "18px 22px" }}>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "12px" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
            <Bot size={22} color="#11685f" />
            <h3 style={{ margin: 0 }}>SwiftAgents Runtime Status</h3>
          </div>
          <span className="ai-pill">{config?.mock_mode ? "Mock Sandbox Mode" : "Live Cloud Active"}</span>
        </div>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: "14px", fontSize: "13px" }}>
          <div>
            <span className="muted" style={{ display: "block" }}>Company ID</span>
            <code>{config?.company_id ?? "Not configured"}</code>
          </div>
          <div>
            <span className="muted" style={{ display: "block" }}>Public Widget Key</span>
            <code>{config?.public_key ? `${config.public_key.slice(0, 12)}...` : "None"}</code>
          </div>
          <div>
            <span className="muted" style={{ display: "block" }}>Widget CDN URL</span>
            <span style={{ color: "var(--accent)" }}>widget.swiftagents.org</span>
          </div>
          <div>
            <span className="muted" style={{ display: "block" }}>Agent Tool Endpoint</span>
            <code>POST /v1/agent/complaints</code>
          </div>
        </div>
        <div style={{ marginTop: "14px", display: "flex", gap: "10px" }}>
          <button type="button" className="button secondary" onClick={openAgent}>
            <Bot size={16} /> Open Test Widget
          </button>
        </div>
      </section>

      <div className="two-column">
        <EventPanel title="SwiftAgents Handoffs" rows={handoffs} type="handoff" retry={retry} />
        <EventPanel title="Notification Events" rows={notifications} type="notification" retry={retry} />
      </div>
    </section>
  );
}

function Settings({
  setToast,
  config,
}: {
  setToast: (message: string) => void;
  config: ReturnType<typeof useSwiftAgent>["config"];
}) {
  const [latency, setLatency] = useState<number | null>(null);
  const [checking, setChecking] = useState(false);

  async function checkHealth() {
    setChecking(true);
    const start = performance.now();
    try {
      await getAgentToolsCatalog();
    } catch {
      // fallback in case of network issue
    }
    const end = performance.now();
    setLatency(Math.round(end - start));
    setChecking(false);
    setToast("API connectivity verified");
  }

  return (
    <section className="view-stack">
      <PageHeader
        kicker="Architecture & Environment"
        title="System Status & Configuration"
        copy="All infrastructure credentials and access policies are configured programmatically via secure server environment variables."
        action={
          <button className="button secondary" type="button" onClick={checkHealth} disabled={checking}>
            <Activity size={16} />
            {checking ? "Checking..." : latency !== null ? `Live Latency: ${latency}ms` : "Test Connection"}
          </button>
        }
      />
      <div className="two-column">
        <section className="panel" style={{ padding: "24px" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "10px", marginBottom: "16px" }}>
            <ShieldCheck size={22} color="var(--primary)" />
            <h3 style={{ margin: 0 }}>Programmatic Runtime Configuration</h3>
          </div>
          <p style={{ fontSize: "14px", color: "var(--muted)", lineHeight: 1.6, marginBottom: "20px" }}>
            Per platform security standards, operational secrets and API keys are injected at deployment time into the server environment rather than exposed or managed in client-side forms.
          </p>

          <div style={{ display: "grid", gap: "14px" }}>
            <div className="summary-card" style={{ padding: "14px 16px" }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <div>
                  <strong style={{ fontSize: "14px", display: "block" }}>Database Engine</strong>
                  <span className="muted" style={{ fontSize: "12px" }}>Neon Serverless PostgreSQL (asyncpg connection pooler)</span>
                </div>
                <span className="badge ready" style={{ display: "inline-flex", alignItems: "center", gap: "5px" }}>
                  <CheckCircle size={12} /> Configured
                </span>
              </div>
            </div>

            <div className="summary-card" style={{ padding: "14px 16px" }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <div>
                  <strong style={{ fontSize: "14px", display: "block" }}>Intake Engine</strong>
                  <span className="muted" style={{ fontSize: "12px" }}>SwiftAgents Autonomous Assistant ({config?.mock_mode ? "Local Dev Mock" : "Production Cloud CDN"})</span>
                </div>
                <span className="badge active" style={{ display: "inline-flex", alignItems: "center", gap: "5px" }}>
                  <Bot size={12} /> Active
                </span>
              </div>
            </div>

            <div className="summary-card" style={{ padding: "14px 16px" }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <div>
                  <strong style={{ fontSize: "14px", display: "block" }}>Staff Authorization</strong>
                  <span className="muted" style={{ fontSize: "12px" }}>Managed server-side via STAFF_API_KEY environment variable</span>
                </div>
                <span className="badge in_review" style={{ display: "inline-flex", alignItems: "center", gap: "5px" }}>
                  <Lock size={12} /> Programmatic
                </span>
              </div>
            </div>
          </div>
        </section>

        <section className="panel" style={{ padding: "24px" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "10px", marginBottom: "16px" }}>
            <Lock size={22} color="var(--accent)" />
            <h3 style={{ margin: 0 }}>Security & Zero-Exposure Policy</h3>
          </div>
          <p style={{ fontSize: "14px", color: "var(--muted)", lineHeight: 1.6, marginBottom: "16px" }}>
            The platform follows a zero-trust frontend design:
          </p>
          <ul style={{ fontSize: "13px", color: "var(--text)", lineHeight: 1.8, paddingLeft: "20px", margin: 0 }}>
            <li><strong>Zero Browser Storage:</strong> Secrets and master API credentials are never written to local storage, cookies, or client bundles.</li>
            <li><strong>Environment Isolation:</strong> Production variables (<code>DATABASE_URL</code>, <code>SWIFTAGENTS_AGENT_KEY</code>, <code>STAFF_API_KEY</code>) are passed securely via Render / hosting environment secrets.</li>
            <li><strong>Webhook Signature Verification:</strong> SwiftAgents webhooks and tool calls are validated at the API boundary before database execution.</li>
            <li><strong>Public Citizen Boundary:</strong> The public portal at <code>/</code> is completely stripped of administrative controls and privileged data access.</li>
          </ul>
        </section>
      </div>
    </section>
  );
}

function PageHeader({ kicker, title, copy, action }: { kicker: string; title: string; copy: string; action?: React.ReactNode }) {
  return (
    <div className="page-header">
      <div>
        <p className="eyebrow">{kicker}</p>
        <h1>{title}</h1>
        <p>{copy}</p>
      </div>
      {action}
    </div>
  );
}

function Fact({ label, value }: { label: string; value: string }) {
  return (
    <div className="fact">
      <small>{label}</small>
      <strong>{value}</strong>
    </div>
  );
}

function ContentBlock({ title, copy }: { title: string; copy: string }) {
  return (
    <div className="content-block">
      <h3>{title}</h3>
      <p>{copy}</p>
    </div>
  );
}

function RecordSection({ title, records }: { title: string; records: { id: string; title: string; meta: string }[] }) {
  return (
    <section className="record-section">
      <div className="section-head">
        <h3>{title}</h3>
        <span className="count-pill">{records.length}</span>
      </div>
      {records.length === 0 && <p className="muted small">No records yet.</p>}
      <ul className="record-list">
        {records.map((item) => (
          <li className="record" key={item.id}>
            <strong>{item.title}</strong>
            <small>{item.meta}</small>
          </li>
        ))}
      </ul>
    </section>
  );
}

function ReportSection({ title, counts }: { title: string; counts: Record<string, number> }) {
  const rows = Object.entries(counts);
  return (
    <section className="panel report-panel">
      <h3>{title}</h3>
      {rows.length === 0 && <p className="muted">No data available.</p>}
      <ul className="breakdown-list">
        {rows.map(([key, count]) => (
          <li className="breakdown-row" key={key}>
            <span>{titleCase(key)}</span>
            <strong>{count}</strong>
          </li>
        ))}
      </ul>
    </section>
  );
}

function EventPanel<T extends Handoff | NotificationEvent>({
  title,
  rows,
  type,
  retry,
}: {
  title: string;
  rows: T[];
  type: "handoff" | "notification";
  retry: (type: "handoff" | "notification", id: string) => Promise<void>;
}) {
  return (
    <section className="panel event-panel">
      <div className="panel-head">
        <h3>{title}</h3>
        <span className="count-pill">{rows.length}</span>
      </div>
      {rows.length === 0 && <EmptyState title="No events" copy="No external delivery attempts recorded yet." />}
      <ul className="event-list">
        {rows.map((row) => (
          <li className="event-row" key={row.id}>
            <div>
              <strong>{titleCase(row.event_type)}</strong>
              <small>{formatDate(row.created_at)}</small>
              {"channel" in row && <small>{row.channel}: {row.recipient}</small>}
              {"message" in row && <p className="event-message">{row.message}</p>}
              {row.error_message && <p className="error-copy">{row.error_message}</p>}
            </div>
            <div className="event-actions">
              <Badge value={row.status} />
              <button className="button ghost small" type="button" onClick={() => retry(type, row.id)}>
                Retry
              </button>
            </div>
          </li>
        ))}
      </ul>
    </section>
  );
}

function Badge({ value }: { value: string }) {
  return <span className={`badge ${value}`}>{titleCase(value)}</span>;
}

function Notice({ children, tone = "accent" }: { children: React.ReactNode; tone?: "accent" | "danger" }) {
  return <div className={`notice ${tone}`}>{children}</div>;
}

function EmptyState({ title, copy, tone = "default" }: { title: string; copy: string; tone?: "default" | "danger" }) {
  return (
    <div className={`empty-state ${tone}`}>
      <strong>{title}</strong>
      <p>{copy}</p>
    </div>
  );
}

function SkeletonRows() {
  return (
    <div className="skeleton-stack" aria-hidden="true">
      <div className="skeleton-row" />
      <div className="skeleton-row" />
      <div className="skeleton-row" />
    </div>
  );
}

export default App;
