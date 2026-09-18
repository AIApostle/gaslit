# Host Community Complaint and Case Management Platform

## Purpose

Build a secure, mobile-first platform that turns a community complaint into a traceable case with an owner, controlled lifecycle, SLA visibility, audit history, and understandable updates.

The application is the system of record. SwiftAgents is optional and may be embedded through its SDK as a public support/chat interface. It does not own case data, workflow state, access control, official notifications, or the audit trail.

## Product Boundaries

### Our application owns

- Complaint intake, case references, case records, staff accounts, and roles.
- The lifecycle: Reported, Under Investigation, Response Issued, Resolved, and Escalated.
- Configurable categories, priorities, SLA policies, and escalation rules.
- Investigation notes, evidence metadata, responses, resolutions, exports, and immutable audit events.
- Privacy-safe case-status lookup, notification delivery records, and retries.

### SwiftAgents SDK may provide

- An embedded AI assistant that explains how to submit a complaint, answers public process questions, and directs people to the complaint form.
- A tightly controlled, authenticated handoff to our status-lookup API, only after SDK/API capabilities and privacy safeguards are validated.

### SwiftAgents SDK must not provide

- The case database or authoritative case stage.
- Direct access to raw case histories, evidence, staff notes, or internal dashboards.
- The only route for acknowledgement or official stage-change notification.

## Key Decisions Before Build

1. Confirm the pilot organization, operating sites, complaint categories, severity definitions, staff roles, SLA targets, and escalation policy.
2. Select the MVP intake channels. Default to responsive web/PWA, then add SMS only if coverage, cost, and provider capability suit the pilot.
3. Choose a notification provider for SMS, email, and optional WhatsApp. It must expose delivery status and support idempotent sends.
4. Define status lookup as `reference + one-time code` or another approved verification factor. A reference number alone is not sufficient.
5. Obtain SwiftAgents SDK/API documentation and a sandbox. Test allowed data, authentication, embeds, webhooks, rate limits, and failure behavior.
6. Confirm legal requirements for retention, consent, evidence handling, data location, and sensitive community information.

Deliverable: a signed-off pilot configuration and integration decision record.

## Proposed Architecture

```text
Community web/PWA ----> FastAPI case API ----> PostgreSQL
       |                        |                    |
SwiftAgents SDK (optional)      |                    +--> audit/event records
       |                        |
       +--> approved public guidance          +--> job queue / worker
                                                      |
                                              SMS, email, WhatsApp provider

Staff dashboard ----> FastAPI case API ----> object storage for evidence/exports
```

## Technology Direction

- Backend: extend the existing FastAPI and Pydantic project in `backend/`.
- Database: PostgreSQL, with SQLAlchemy and Alembic migrations.
- Background work: Redis plus a worker framework for retries, SLA checks, notification delivery, and export generation.
- Frontend: React-based responsive PWA for public intake and internal staff UI.
- Files: S3-compatible object storage with type, size, and access restrictions.
- Deployment: Docker, staging and production environments, managed secrets, backups, metrics, and centralized error reporting.

## Delivery Phases

### Phase 1: Foundation and security

- Establish environments, Docker, CI, linting, tests, secret handling, and database migration conventions.
- Implement internal staff authentication, organizations/sites, RBAC, and authorization checks on every protected endpoint.
- Add structured logs, correlation IDs, health checks, and backup/restore procedures.

Exit criteria: a deployed staging API has authenticated health checks, database migrations, role-restricted test endpoints, and a passing CI pipeline.

### Phase 2: Core data model and workflow

Implement `Organization`, `Site`, `User`, `Role`, `SlaPolicy`, `Contact`, `Case`, `CaseAssignment`, `CaseEvent`, `InvestigationNote`, `Evidence`, `NotificationEvent`, `IntegrationEvent`, and `SlaRecord`.

Implement a workflow service that:

- Generates non-guessable case references.
- Enforces permitted stage transitions and records the actor/timestamp.
- Requires an assigned owner before investigation, a response before response issuance, and a resolution summary before closure.
- Computes SLA warning, breach, and escalation status from configuration.
- Writes the case update and an event/outbox record in one database transaction.

Exit criteria: API and database tests cover valid/invalid transitions, ownership, SLA calculations, audit completeness, and concurrent update handling.

### Phase 3: Community intake and status lookup

- Create a plain-language, mobile-first complaint form with category, description, location/community, occurrence date, contact details, preferred channel, and consent.
- Validate inputs, create the case durably, and show an immediate reference.
- Add clear network states, retry guidance, and saved form data where practical.
- Build status lookup using reference plus verification code. Return only approved public stage/status text, never internal notes or evidence.
- Add rate limits, abuse monitoring, and privacy-safe error messages to public endpoints.

Exit criteria: a community member can submit, receive a reference, verify identity, and view only the permitted status for their own case.

### Phase 4: Staff operations

- Build officer queues for new, assigned, unassigned, at-risk, breached, escalated, and recently resolved cases.
- Build a case detail screen with complaint data, ownership, SLA status, investigation notes, evidence, response, resolution, and chronological audit timeline.
- Support assignment/reassignment, categorization, priority updates, evidence metadata, stage transitions, escalation, and resolution.
- Build manager views for volume, stage bottlenecks, ageing, SLA health, category/location trends, and unassigned work.

Exit criteria: officers can take a case from Reported to Resolved without a spreadsheet, while managers can identify all at-risk and escalated work.

### Phase 5: Notifications and integration reliability

- Select and integrate the approved SMS/email/WhatsApp provider.
- Consume persisted outbox events in a worker; never block case updates on an external provider.
- Use idempotency keys, bounded exponential retries, delivery-state recording, staff-visible failures, and manual retry controls.
- Map lifecycle events to approved, minimal message templates.
- Implement scheduled SLA warning and breach checks.

Exit criteria: simulated provider outages leave cases intact, show a visible failure, and recover without duplicate messages.

### Phase 6: Optional SwiftAgents SDK integration

- Embed the SDK only after the sandbox validation gate passes.
- Restrict its knowledge to approved public guidance, FAQs, and complaint submission/status-lookup navigation.
- Keep it behind a feature flag and consent/privacy review.
- If authenticated status assistance is supported, proxy requests through our backend and return only data available on the status page.
- Add telemetry for handoffs, failures, and unsupported requests, with a clear human/support fallback.

Exit criteria: the assistant cannot access or disclose sensitive case data and the product remains usable if SwiftAgents is unavailable.

### Phase 7: Reports, hardening, and pilot

- Generate a structured case summary with facts, actions, responsible staff, communication history, response, and resolution.
- Finalize retention/archival, evidence access controls, export audit events, and administrator configuration.
- Run accessibility, mobile-device, security, load, backup/restore, and integration-failure tests.
- Pilot with limited sites, categories, and channels; measure time to first action, SLA performance, delivery success, and unresolved-case ageing.

Exit criteria: every PRD acceptance scenario passes in staging and the pilot team can operate the service with documented support procedures.

## Initial API Surface

| Area | Example endpoints |
| --- | --- |
| Public intake | `POST /public/complaints` |
| Public status | `POST /public/status/verify`, `GET /public/cases/{reference}` |
| Staff cases | `GET /cases`, `GET /cases/{id}`, `PATCH /cases/{id}` |
| Workflow | `POST /cases/{id}/assignments`, `POST /cases/{id}/transitions` |
| Case content | `POST /cases/{id}/notes`, `POST /cases/{id}/evidence` |
| Reports | `POST /cases/{id}/export`, `GET /reports/portfolio` |
| Operations | `GET /integration-events`, `POST /integration-events/{id}/retry` |

Document final request/response schemas, pagination, filters, authentication, and error contracts with OpenAPI and integration tests.

## MVP Acceptance Checklist

- A valid complaint produces a durable case and immediate unique reference.
- Authorized staff can assign, investigate, respond to, escalate, and resolve a case through controlled transitions.
- Each important action is attributable and visible in the case timeline.
- SLA warnings/breaches appear in officer and manager queues.
- A complainant can view only approved status for their own verified case.
- A notification failure is auditable, visible, retryable, and never loses the underlying case or creates duplicate notifications.
- Unauthorized users cannot retrieve another person's case information.
- A finalized case exports to a structured summary.
- The platform remains operational when SwiftAgents or a notification provider is unavailable.

## Recommended Build Order

Do not start optional SwiftAgents SDK work until Phases 1 through 3 work in staging. Build the case-management core first, then staff operations, then official communications. This keeps the pilot viable if AI-support integration is delayed or unsuitable.
