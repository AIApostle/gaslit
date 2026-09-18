export type CaseStage =
  | "reported"
  | "under_investigation"
  | "response_issued"
  | "resolved"
  | "escalated";

export type ContactChannel = "sms" | "email" | "whatsapp" | "phone";

export type SlaStatus = "on_track" | "at_risk" | "breached" | "resolved";

export type CaseSummary = {
  id: string;
  reference: string;
  category: string;
  location: string;
  stage: CaseStage;
  priority: "low" | "normal" | "high" | "critical";
  assigned_officer: string | null;
  created_at: string;
  updated_at: string;
  age_hours: number;
  sla_status: SlaStatus;
  sla_warning_at: string | null;
  sla_due_at: string | null;
};

export type CaseDetail = CaseSummary & {
  complainant_name: string;
  contact_value: string;
  preferred_channel: ContactChannel;
  description: string;
  occurred_at: string | null;
  source_channel: string;
  response_summary: string | null;
  resolution_summary: string | null;
  resolved_at: string | null;
  status_verification_code: string | null;
};

export type CaseEvent = {
  event_type: string;
  actor: string;
  occurred_at: string;
  metadata: Record<string, unknown>;
};

export type CaseWithTimeline = {
  case: CaseDetail;
  events: CaseEvent[];
};

export type InvestigationNote = {
  id: string;
  case_id: string;
  note: string;
  actor: string;
  created_at: string;
};

export type Evidence = {
  id: string;
  case_id: string;
  file_name: string;
  evidence_type: string;
  description: string | null;
  storage_uri: string | null;
  actor: string;
  created_at: string;
};

export type NotificationEvent = {
  id: string;
  case_id: string;
  event_type: string;
  channel: ContactChannel;
  recipient: string;
  message: string;
  status: string;
  attempts: number;
  created_at: string;
  last_attempt_at: string | null;
  error_message: string | null;
};

export type Handoff = {
  id: string;
  case_id: string;
  event_type: string;
  status: string;
  attempts: number;
  created_at: string;
  last_attempt_at: string | null;
  error_message: string | null;
};

export type PublicStatus = {
  reference: string;
  stage: CaseStage;
  status_message: string;
  updated_at: string;
  sla_status: SlaStatus;
};

export type PortfolioReport = {
  total_cases: number;
  open_cases: number;
  resolved_cases: number;
  unassigned_cases: number;
  escalated_cases: number;
  at_risk_cases: number;
  breached_cases: number;
  by_stage: Record<string, number>;
  by_priority: Record<string, number>;
  by_category: Record<string, number>;
};

export type CaseExport = {
  case: CaseDetail;
  events: CaseEvent[];
  notes: InvestigationNote[];
  evidence: Evidence[];
  notifications: NotificationEvent[];
};
