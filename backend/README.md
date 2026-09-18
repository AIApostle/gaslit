# Host Community Case Management API

This is the backend for the complaint-to-resolution workflow. It owns the case
record, lifecycle, audit timeline, and staff operations. SwiftAgents is the
primary conversational integration, using the agent-safe endpoints below; it is
not the system of record.

## Run locally

```bash
uv run uvicorn backend.main:app --app-dir src --reload
```

The development database is `case_management.db` in the working directory.
Set `DATABASE_PATH` to use another location.

Open `http://127.0.0.1:8000/app/` for the local operations desk, or `http://127.0.0.1:8000/docs` for the interactive OpenAPI contract.

## MVP workflow now implemented

- Public intake creates a durable case with a unique reference, verification code,
  SLA warning/due timestamps, an audit event, a notification event, and a
  SwiftAgents/Zapier handoff event.
- Public status lookup uses `reference + verification_code` or the approved
  contact fallback and returns only the public stage message.
- Staff users can assign cases, move through the controlled lifecycle, escalate,
  record investigation notes, register evidence metadata, issue responses, and
  resolve with a required resolution summary.
- Manager reporting surfaces open, unassigned, escalated, at-risk, breached,
  resolved, stage, priority, and category counts.
- Case export returns a structured summary containing the case, timeline, notes,
  evidence metadata, and notification history.
- Integration and notification events are persisted and retryable without
  changing the authoritative case state.

Run the acceptance-focused tests with:

```bash
uv run pytest
```

## SwiftAgents integration contract

The operations desk uses the documented SwiftAgents browser widget. Set the
following values from the SwiftAgents dashboard before starting the API:

```bash
export SWIFTAGENTS_COMPANY_ID="your-company-uuid"
export SWIFTAGENTS_PUBLIC_KEY="swa_live_your_public_widget_key"
```

`SWIFTAGENTS_PUBLIC_KEY` is intentionally passed to the browser: SwiftAgents
documents it as a public, widget-scoped key. Do not put a dashboard or server
secret in this variable.

Configure the SwiftAgents SDK or agent tools to call:

- `POST /v1/agent/complaints` to create a case from a guided conversation.
- `POST /v1/public/status` to return a verified, minimal status update.

Set `SWIFTAGENTS_AGENT_KEY` and send it as `X-Agent-Key` in production. The API
records agent-created cases and stage-change handoffs in `agent_handoffs` so
delivery/retry behavior remains observable. Configure `SWIFTAGENTS_WEBHOOK_URL`
when the exact webhook contract is available; staff can deliver or retry pending
handoffs from the operations desk.

Set `STAFF_API_KEY` and send it as `X-Staff-Key` to protect staff endpoints in
non-development environments. Replace this temporary shared-key guard with the
chosen identity provider before production.
