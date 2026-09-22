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
  SwiftAgentConfig,
  SwiftAgentToolResponse,
  SwiftAgentLookupResponse,
  SwiftAgentEvidenceResponse,
  SwiftAgentHandoffResponse,
  SwiftAgentToolCatalog,
} from "./types";

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "";

export class ApiError extends Error {
  constructor(message: string, public status: number) {
    super(message);
  }
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const staffKey = localStorage.getItem("staffApiKey");
  const headers = new Headers(options.headers);
  headers.set("Content-Type", "application/json");
  if (staffKey) {
    headers.set("X-Staff-Key", staffKey);
  }

  const response = await fetch(`${API_BASE}${path}`, { ...options, headers });
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new ApiError(body.detail ?? "Request failed", response.status);
  }
  return response.json() as Promise<T>;
}

export type ComplaintInput = {
  complainant_name: string;
  contact_value: string;
  preferred_channel: string;
  category: string;
  description: string;
  location: string;
  occurred_at?: string;
  source_channel: string;
  priority: string;
};

export function createComplaint(payload: ComplaintInput) {
  return request<CaseSummary & { status_verification_code: string }>("/v1/public/complaints", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function lookupStatus(payload: {
  reference: string;
  verification_code?: string;
  contact_value?: string;
}) {
  return request<PublicStatus>("/v1/public/status", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function listCases(filters: { stage?: CaseStage | ""; queue?: string; query?: string }) {
  const params = new URLSearchParams();
  if (filters.stage) params.set("stage", filters.stage);
  if (filters.queue) params.set("queue", filters.queue);
  if (filters.query) params.set("query", filters.query);
  return request<CaseSummary[]>(`/v1/cases${params.toString() ? `?${params}` : ""}`);
}

export function getCase(id: string) {
  return request<CaseWithTimeline>(`/v1/cases/${id}`);
}

export function getNotes(id: string) {
  return request<InvestigationNote[]>(`/v1/cases/${id}/notes`);
}

export function getEvidence(id: string) {
  return request<Evidence[]>(`/v1/cases/${id}/evidence`);
}

export function getCaseNotifications(id: string) {
  return request<NotificationEvent[]>(`/v1/cases/${id}/notifications`);
}

export function assignCase(id: string, assignedOfficer: string) {
  return request(`/v1/cases/${id}/assignments`, {
    method: "POST",
    body: JSON.stringify({ assigned_officer: assignedOfficer }),
  });
}

export function transitionCase(
  id: string,
  payload: { stage: CaseStage; note?: string; response_summary?: string; resolution_summary?: string }
) {
  return request(`/v1/cases/${id}/transitions`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function addNote(id: string, note: string) {
  return request<InvestigationNote>(`/v1/cases/${id}/notes`, {
    method: "POST",
    body: JSON.stringify({ note }),
  });
}

export function addEvidence(id: string, payload: { file_name: string; description?: string | null }) {
  return request<Evidence>(`/v1/cases/${id}/evidence`, {
    method: "POST",
    body: JSON.stringify({ ...payload, evidence_type: "document" }),
  });
}

export function exportCase(id: string) {
  return request<CaseExport>(`/v1/cases/${id}/export`);
}

export function getPortfolioReport() {
  return request<PortfolioReport>("/v1/reports/portfolio");
}

export function listHandoffs() {
  return request<Handoff[]>("/v1/agent/handoffs");
}

export function retryHandoff(id: string) {
  return request<Handoff>(`/v1/agent/handoffs/${id}/deliver`, { method: "POST" });
}

export function listNotifications() {
  return request<NotificationEvent[]>("/v1/notifications");
}

export function retryNotification(id: string) {
  return request<NotificationEvent>(`/v1/notifications/${id}/deliver`, { method: "POST" });
}

export function getSwiftAgentConfig() {
  return request<SwiftAgentConfig>("/v1/integrations/swiftagents/config");
}

export function agentSubmitComplaint(payload: {
  complainant_name?: string;
  contact_value?: string;
  preferred_channel?: string;
  category?: string;
  description: string;
  location?: string;
  priority?: string;
}) {
  return request<SwiftAgentToolResponse>("/v1/agent/complaints", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function agentLookupCase(reference: string, verificationCode?: string) {
  return request<SwiftAgentLookupResponse>("/v1/agent/cases/lookup", {
    method: "POST",
    body: JSON.stringify({ reference, verification_code: verificationCode }),
  });
}

export function agentAttachEvidence(payload: {
  reference: string;
  file_name: string;
  evidence_type?: string;
  storage_uri?: string;
  description?: string;
}) {
  return request<SwiftAgentEvidenceResponse>("/v1/agent/evidence", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function agentRequestHandoff(payload: {
  reference?: string;
  citizen_name?: string;
  contact_value?: string;
  reason: string;
  urgency?: string;
}) {
  return request<SwiftAgentHandoffResponse>("/v1/agent/handoff", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function getAgentToolsCatalog() {
  return request<SwiftAgentToolCatalog>("/v1/agent/tools.json");
}
