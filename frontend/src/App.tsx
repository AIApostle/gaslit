import {
  Activity,
  BarChart3,
  Bell,
  BriefcaseBusiness,
  CheckCircle,
  CircleUserRound,
  Clock,
  Download,
  FileText,
  FolderOpen,
  Gauge,
  KeyRound,
  Plus,
  RefreshCw,
  Save,
  Search,
  Send,
  ShieldCheck,
  Siren,
  SquarePen
} from "lucide-react";
import { FormEvent, useEffect, useMemo, useState } from "react";

import {
  addEvidence,
  addNote,
  assignCase,
  createComplaint,
  exportCase,
  getCase,
  getCaseNotifications,
  getEvidence,
  getNotes,
  getPortfolioReport,
  listCases,
  listHandoffs,
  listNotifications,
  lookupStatus,
  retryHandoff,
  retryNotification,
  transitionCase
} from "./api";
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
  PublicStatus
} from "./types";

type View = "workspace" | "intake" | "status" | "reports" | "integration" | "settings";

const stageOptions: { value: CaseStage; label: string }[] = [
  { value: "reported", label: "Reported" },
  { value: "under_investigation", label: "Investigation" },
  { value: "response_issued", label: "Response issued" },
  { value: "escalated", label: "Escalated" },
  { value: "resolved", label: "Resolved" }
];

const queueOptions = [
  { value: "open", label: "Open" },
  { value: "unassigned", label: "Unassigned" },
  { value: "at_risk", label: "At risk" },
  { value: "breached", label: "Breached" },
  { value: "escalated", label: "Escalated" }
];

function titleCase(value: string) {
  return value.replaceAll("_", " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function formatDate(value: string | null | undefined) {
  return value ? new Date(value).toLocaleString() : "Not set";
}

function App() {
  const [view, setView] = useState<View>("workspace");
  const [toast, setToast] = useState<string | null>(null);

  return (
    <div className="app-shell">
      <header className="topbar">
        <button className="brand" type="button" onClick={() => setView("workspace")}>
          <span className="brand-mark">HC</span>
          <span>
            <strong>Community Case Desk</strong>
            <small>Complaint to resolution control room</small>
          </span>
        </button>
        <nav className="nav-tabs" aria-label="Primary navigation">
          <NavButton active={view === "workspace"} icon={<BriefcaseBusiness />} onClick={() => setView("workspace")}>
            Workspace
          </NavButton>
          <NavButton active={view === "intake"} icon={<Plus />} onClick={() => setView("intake")}>
            Intake
          </NavButton>
          <NavButton active={view === "status"} icon={<Search />} onClick={() => setView("status")}>
            Status
          </NavButton>
          <NavButton active={view === "reports"} icon={<BarChart3 />} onClick={() => setView("reports")}>
            Reports
          </NavButton>
          <NavButton active={view === "integration"} icon={<Bell />} onClick={() => setView("integration")}>
            Integration
          </NavButton>
          <NavButton active={view === "settings"} icon={<KeyRound />} onClick={() => setView("settings")}>
            Settings
          </NavButton>
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
        {view === "workspace" && <Workspace setToast={setToast} />}
        {view === "intake" && <Intake setToast={setToast} />}
        {view === "status" && <StatusLookup />}
        {view === "reports" && <Reports />}
        {view === "integration" && <IntegrationMonitor setToast={setToast} />}
        {view === "settings" && <Settings setToast={setToast} />}
      </main>
    </div>
  );
}

function NavButton({
  active,
  icon,
  children,
  onClick
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

function Workspace({ setToast }: { setToast: (message: string) => void }) {
  const [cases, setCases] = useState<CaseSummary[]>([]);
  const [stage, setStage] = useState<CaseStage | "">("");
  const [queue, setQueue] = useState("");
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
      setCases(await listCases({ stage, queue }));
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Could not load cases");
    } finally {
      setLoading(false);
    }
  }

  async function loadSelected(id: string) {
    setSelectedId(id);
    const [caseData, noteData, evidenceData, notificationData] = await Promise.all([
      getCase(id),
      getNotes(id),
      getEvidence(id),
      getCaseNotifications(id)
    ]);
    setSelected(caseData);
    setNotes(noteData);
    setEvidence(evidenceData);
    setNotifications(notificationData);
  }

  useEffect(() => {
    refreshCases();
  }, [stage, queue]);

  const metrics = useMemo(
    () => [
      ["Open", cases.filter((item) => item.stage !== "resolved").length, <FolderOpen />],
      ["Investigation", cases.filter((item) => item.stage === "under_investigation").length, <Activity />],
      ["Escalated", cases.filter((item) => item.stage === "escalated").length, <Siren />],
      ["At risk", cases.filter((item) => item.sla_status === "at_risk").length, <Clock />],
      ["Breached", cases.filter((item) => item.sla_status === "breached").length, <Gauge />],
      ["Resolved", cases.filter((item) => item.stage === "resolved").length, <ShieldCheck />]
    ],
    [cases]
  );

  return (
    <section className="view-stack">
      <PageHeader
        kicker="Operations"
        title="Case workspace"
        copy="A single accountable queue for intake, assignment, investigation, response, SLA pressure and resolution."
        action={<button className="button ghost" type="button" onClick={refreshCases}><RefreshCw />Refresh</button>}
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
            <h2>Queue</h2>
            <div className="filters">
              <select value={stage} onChange={(event) => setStage(event.target.value as CaseStage | "")}>
                <option value="">All stages</option>
                {stageOptions.map((option) => (
                  <option key={option.value} value={option.value}>{option.label}</option>
                ))}
              </select>
              <select value={queue} onChange={(event) => setQueue(event.target.value)}>
                <option value="">All queues</option>
                {queueOptions.map((option) => (
                  <option key={option.value} value={option.value}>{option.label}</option>
                ))}
              </select>
            </div>
          </div>
          {loading && <SkeletonRows />}
          {error && <EmptyState tone="danger" title="Queue unavailable" copy={error} />}
          {!loading && !error && (
            <ul className="case-list">
              {cases.length === 0 && <li><EmptyState title="No matching cases" copy="Change the queue filters or create a complaint." /></li>}
              {cases.map((item) => (
                <li key={item.id}>
                  <button
                    className={selectedId === item.id ? "case-row selected" : "case-row"}
                    type="button"
                    onClick={() => loadSelected(item.id)}
                  >
                    <span>
                      <strong>{item.reference}</strong>
                      <small>{item.category} in {item.location}</small>
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
  setToast
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
        <EmptyState title="Select a case" copy="Open a queue item to inspect the complaint, timeline, SLA state and next action." />
      </aside>
    );
  }

  const detail = selected.case;

  async function assign() {
    const officer = window.prompt("Officer name", detail.assigned_officer ?? "Current staff member");
    if (!officer) return;
    await assignCase(detail.id, officer);
    setToast("Case owner updated");
    await reload();
  }

  async function transition(stage: CaseStage) {
    const payload: { stage: CaseStage; response_summary?: string; resolution_summary?: string } = { stage };
    if (stage === "response_issued") {
      const response = window.prompt("Response summary");
      if (!response) return;
      payload.response_summary = response;
    }
    if (stage === "resolved") {
      const resolution = window.prompt("Resolution summary");
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
      description: fileDescription.trim() || null
    });
    setFileName("");
    setFileDescription("");
    setToast("Evidence metadata saved");
    await reload();
  }

  async function loadExport() {
    setCaseExport(await exportCase(detail.id));
  }

  return (
    <aside className="panel detail-panel">
      <div className="detail-hero">
        <div>
          <p className="eyebrow">{detail.reference}</p>
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
        <Fact label="Owner" value={detail.assigned_officer ?? "Unassigned"} />
        <Fact label="Priority" value={titleCase(detail.priority)} />
        <Fact label="SLA due" value={formatDate(detail.sla_due_at)} />
        <Fact label="Age" value={`${detail.age_hours} hours`} />
      </div>

      <div className="content-block">
        <h3>Complaint</h3>
        <p>{detail.description}</p>
      </div>
      {detail.response_summary && <ContentBlock title="Response" copy={detail.response_summary} />}
      {detail.resolution_summary && <ContentBlock title="Resolution" copy={detail.resolution_summary} />}

      <div className="action-grid">
        <button className="button ghost" type="button" onClick={assign}><CircleUserRound />Assign</button>
        <NextStageButton stage={detail.stage} onTransition={transition} />
        <button className="button warning" type="button" disabled={detail.stage === "resolved" || detail.stage === "escalated"} onClick={() => transition("escalated")}><Siren />Escalate</button>
        <button className="button ghost" type="button" onClick={loadExport}><Download />Export</button>
      </div>

      <form className="inline-form" onSubmit={saveNote}>
        <label htmlFor="note">Investigation note</label>
        <textarea id="note" value={note} onChange={(event) => setNote(event.target.value)} />
        <button className="button ghost" type="submit"><SquarePen />Save note</button>
      </form>

      <form className="inline-form" onSubmit={saveEvidence}>
        <label htmlFor="file-name">Evidence metadata</label>
        <input id="file-name" value={fileName} onChange={(event) => setFileName(event.target.value)} placeholder="File name or reference" />
        <input value={fileDescription} onChange={(event) => setFileDescription(event.target.value)} placeholder="Short description" />
        <button className="button ghost" type="submit"><FileText />Save evidence</button>
      </form>

      <RecordSection title="Timeline" records={selected.events.map((event) => ({
        id: `${event.event_type}-${event.occurred_at}`,
        title: titleCase(event.event_type),
        meta: `${event.actor} | ${formatDate(event.occurred_at)}`
      }))} />
      <RecordSection title="Notes" records={notes.map((item) => ({ id: item.id, title: item.note, meta: `${item.actor} | ${formatDate(item.created_at)}` }))} />
      <RecordSection title="Evidence" records={evidence.map((item) => ({ id: item.id, title: item.file_name, meta: `${item.evidence_type} | ${item.description ?? "No description"}` }))} />
      <RecordSection title="Notifications" records={notifications.map((item) => ({ id: item.id, title: titleCase(item.event_type), meta: `${item.channel} | ${titleCase(item.status)} | ${item.attempts} attempts` }))} />
      {caseExport && <pre className="export-box">{JSON.stringify(caseExport, null, 2)}</pre>}
    </aside>
  );
}

function NextStageButton({ stage, onTransition }: { stage: CaseStage; onTransition: (stage: CaseStage) => void }) {
  const next: Partial<Record<CaseStage, { label: string; stage: CaseStage }>> = {
    reported: { label: "Start investigation", stage: "under_investigation" },
    under_investigation: { label: "Issue response", stage: "response_issued" },
    response_issued: { label: "Resolve", stage: "resolved" },
    escalated: { label: "Resume investigation", stage: "under_investigation" }
  };
  const action = next[stage];
  return (
    <button className="button primary" type="button" disabled={!action} onClick={() => action && onTransition(action.stage)}>
      <Send />
      {action?.label ?? "Resolved"}
    </button>
  );
}

function Intake({ setToast }: { setToast: (message: string) => void }) {
  const [result, setResult] = useState<{ reference: string; code: string } | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    const form = Object.fromEntries(new FormData(event.currentTarget));
    const payload = {
      ...form,
      occurred_at: form.occurred_at ? String(form.occurred_at) : undefined
    } as Parameters<typeof createComplaint>[0];
    const created = await createComplaint(payload).catch((caught) => {
      setError(caught instanceof Error ? caught.message : "Could not create case");
      return null;
    });
    if (!created) return;
    setResult({ reference: created.reference, code: created.status_verification_code });
    setToast("Complaint recorded");
    event.currentTarget.reset();
  }

  return (
    <section className="view-stack">
      <PageHeader
        kicker="Public intake"
        title="Record a complaint"
        copy="Capture the complaint once, issue a reference immediately, and create the audit and notification trail."
      />
      <section className="panel form-panel">
        {error && <Notice tone="danger">{error}</Notice>}
        {result && <Notice>Reference {result.reference}. Verification code {result.code}.</Notice>}
        <form className="case-form" onSubmit={submit}>
          <Field label="Complainant name" name="complainant_name" required minLength={2} />
          <Field label="Contact detail" name="contact_value" required minLength={4} />
          <SelectField label="Preferred channel" name="preferred_channel" options={["sms", "email", "whatsapp", "phone"]} />
          <SelectField label="Priority" name="priority" options={["normal", "low", "high", "critical"]} />
          <Field label="Category" name="category" required minLength={2} />
          <Field label="Occurrence date" name="occurred_at" type="datetime-local" />
          <Field label="Location or community" name="location" required minLength={2} wide />
          <TextAreaField label="Complaint description" name="description" required minLength={10} wide />
          <SelectField label="Intake source" name="source_channel" options={["web", "staff", "phone", "community_meeting", "swiftagents"]} />
          <button className="button primary form-submit" type="submit"><Save />Create case</button>
        </form>
      </section>
    </section>
  );
}

function StatusLookup() {
  const [status, setStatus] = useState<PublicStatus | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setStatus(null);
    const form = Object.fromEntries(new FormData(event.currentTarget));
    const result = await lookupStatus({
      reference: String(form.reference),
      verification_code: form.verification_code ? String(form.verification_code) : undefined,
      contact_value: form.contact_value ? String(form.contact_value) : undefined
    }).catch((caught) => {
      setError(caught instanceof Error ? caught.message : "No verified case was found");
      return null;
    });
    if (result) setStatus(result);
  }

  return (
    <section className="view-stack">
      <PageHeader
        kicker="Public status"
        title="Verified case lookup"
        copy="Show only approved stage language after the person proves they know the reference and verification factor."
      />
      <div className="two-column">
        <section className="panel form-panel">
          {error && <Notice tone="danger">{error}</Notice>}
          <form className="case-form single" onSubmit={submit}>
            <Field label="Reference" name="reference" required />
            <Field label="Verification code" name="verification_code" />
            <Field label="Contact fallback" name="contact_value" />
            <button className="button primary form-submit" type="submit"><Search />Check status</button>
          </form>
        </section>
        <section className="panel result-panel">
          {!status && <EmptyState title="No lookup yet" copy="Enter a case reference and verification factor to view the public-safe status." />}
          {status && (
            <>
              <div className="case-topline">
                <strong>{status.reference}</strong>
                <Badge value={status.stage} />
              </div>
              <p className="status-message">{status.status_message}</p>
              <Badge value={status.sla_status} />
              <p className="muted">Updated {formatDate(status.updated_at)}</p>
            </>
          )}
        </section>
      </div>
    </section>
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
        ["Breached", report.breached_cases]
      ]
    : [];

  return (
    <section className="view-stack">
      <PageHeader
        kicker="Management"
        title="Portfolio report"
        copy="Identify open, ageing, unassigned, escalated and SLA-risk work without leaving the case system."
        action={<button className="button ghost" type="button" onClick={loadReport}><RefreshCw />Refresh</button>}
      />
      {error && <Notice tone="danger">{error}</Notice>}
      {!report && !error && <SkeletonRows />}
      {report && (
        <>
          <div className="metric-grid">
            {metrics.map(([label, value]) => (
              <div className="metric" key={String(label)}>
                <span><BarChart3 /></span>
                <strong>{value}</strong>
                <small>{label}</small>
              </div>
            ))}
          </div>
          <div className="three-column">
            <Breakdown title="By stage" data={report.by_stage} />
            <Breakdown title="By priority" data={report.by_priority} />
            <Breakdown title="By category" data={report.by_category} />
          </div>
        </>
      )}
    </section>
  );
}

function IntegrationMonitor({ setToast }: { setToast: (message: string) => void }) {
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
        title="Integration monitor"
        copy="Every external handoff is visible and retryable; case state remains authoritative in the backend."
        action={<button className="button ghost" type="button" onClick={load}><RefreshCw />Refresh</button>}
      />
      {error && <Notice tone="danger">{error}</Notice>}
      <div className="two-column">
        <EventPanel title="SwiftAgents handoffs" rows={handoffs} type="handoff" retry={retry} />
        <EventPanel title="Notification events" rows={notifications} type="notification" retry={retry} />
      </div>
    </section>
  );
}

function Settings({ setToast }: { setToast: (message: string) => void }) {
  const [staffKey, setStaffKey] = useState(localStorage.getItem("staffApiKey") ?? "");

  function save(event: FormEvent) {
    event.preventDefault();
    if (staffKey.trim()) localStorage.setItem("staffApiKey", staffKey.trim());
    else localStorage.removeItem("staffApiKey");
    setToast("Settings saved");
  }

  return (
    <section className="view-stack">
      <PageHeader
        kicker="Access"
        title="Frontend settings"
        copy="Store a staff API key locally when the backend is configured to require one."
      />
      <section className="panel form-panel">
        <form className="case-form single" onSubmit={save}>
          <label className="field">
            <span>Staff API key</span>
            <input value={staffKey} onChange={(event) => setStaffKey(event.target.value)} type="password" autoComplete="off" />
            <small>Sent as X-Staff-Key for protected staff endpoints.</small>
          </label>
          <button className="button primary form-submit" type="submit"><Save />Save settings</button>
        </form>
      </section>
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

function Field(props: {
  label: string;
  name: string;
  required?: boolean;
  minLength?: number;
  type?: string;
  wide?: boolean;
}) {
  return (
    <label className={props.wide ? "field wide" : "field"}>
      <span>{props.label}</span>
      <input name={props.name} required={props.required} minLength={props.minLength} type={props.type ?? "text"} />
    </label>
  );
}

function TextAreaField(props: { label: string; name: string; required?: boolean; minLength?: number; wide?: boolean }) {
  return (
    <label className={props.wide ? "field wide" : "field"}>
      <span>{props.label}</span>
      <textarea name={props.name} required={props.required} minLength={props.minLength} />
    </label>
  );
}

function SelectField({ label, name, options }: { label: string; name: string; options: string[] }) {
  return (
    <label className="field">
      <span>{label}</span>
      <select name={name}>
        {options.map((option) => (
          <option key={option} value={option}>{titleCase(option)}</option>
        ))}
      </select>
    </label>
  );
}

function Fact({ label, value }: { label: string; value: string }) {
  return (
    <div className="fact">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function Badge({ value }: { value: string }) {
  return <span className={`badge ${value}`}>{titleCase(value)}</span>;
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
      <h3>{title}</h3>
      {records.length === 0 && <p className="muted">No records yet.</p>}
      {records.map((record) => (
        <div className="record" key={record.id}>
          <strong>{record.title}</strong>
          <small>{record.meta}</small>
        </div>
      ))}
    </section>
  );
}

function EventPanel({
  title,
  rows,
  type,
  retry
}: {
  title: string;
  rows: Array<Handoff | NotificationEvent>;
  type: "handoff" | "notification";
  retry: (type: "handoff" | "notification", id: string) => Promise<void>;
}) {
  return (
    <section className="panel event-panel">
      <div className="panel-head"><h2>{title}</h2></div>
      {rows.length === 0 && <EmptyState title="No events" copy="Events will appear when cases are created or changed." />}
      {rows.map((row) => (
        <div className="event-row" key={row.id}>
          <div>
            <strong>{titleCase(row.event_type)}</strong>
            <small>{titleCase(row.status)} | {row.attempts} attempts</small>
            {row.error_message && <small className="danger-text">{row.error_message}</small>}
          </div>
          <button className="button ghost compact" type="button" onClick={() => retry(type, row.id)}>
            <RefreshCw />Retry
          </button>
        </div>
      ))}
    </section>
  );
}

function Breakdown({ title, data }: { title: string; data: Record<string, number> }) {
  const rows = Object.entries(data);
  return (
    <section className="panel breakdown">
      <div className="panel-head"><h2>{title}</h2></div>
      {rows.length === 0 && <EmptyState title="No data" copy="Create cases to populate this view." />}
      {rows.map(([key, value]) => (
        <div className="breakdown-row" key={key}>
          <span>{titleCase(key)}</span>
          <strong>{value}</strong>
        </div>
      ))}
    </section>
  );
}

function EmptyState({ title, copy, tone }: { title: string; copy: string; tone?: "danger" }) {
  return (
    <div className={tone === "danger" ? "empty-state danger" : "empty-state"}>
      <strong>{title}</strong>
      <p>{copy}</p>
    </div>
  );
}

function Notice({ children, tone }: { children: React.ReactNode; tone?: "danger" }) {
  return <div className={tone === "danger" ? "notice danger" : "notice"}>{children}</div>;
}

function SkeletonRows() {
  return (
    <div className="skeleton-stack" aria-label="Loading">
      <span />
      <span />
      <span />
    </div>
  );
}

export default App;
