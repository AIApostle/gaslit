# Project Guidelines: Host Community Case Management Platform (Gaslit)

## Core Focus
* **Primary Intake Engine**: SwiftAgents in-browser AI conversational agent (`https://widget.swiftagents.org`).
* **Database**: SQLite with SQLAlchemy async ORM (`aiosqlite`) for zero-setup, local and lightweight server persistence.
* **UI**: Preserve the established workspace layout, brand identity, and clean ergonomics while elevating design taste and adding SwiftAgents triggers and monitoring views.

## Architecture
* **Frontend**: React 19 + TypeScript + Vite (`frontend/`).
* **Backend**: FastAPI (`backend/`).
## UI & Software Engineering Standards
* **No Literal Infrastructure/Vendor Names in UI**: Never expose literal database or infrastructure engine names (e.g., `SQLite`, `PostgreSQL`, `Neon`, `Redis`, `AWS`, `Render`) in user-facing or staff dashboard interfaces. Leaking low-level implementation details in UI is bad software engineering practice. Always use professional, domain-oriented terminology (e.g., "System of Record Online", "Audit Ledger Active", "Persistent Storage Connected", "Operational").
* **Mobile-First Responsiveness**: All public citizen pages and internal operations desk views must be fully responsive, supporting seamless navigation, off-canvas drawers, clean stacking, and minimum 44px touch targets on mobile viewports.

## Workflow & Version Control Rules
* **Mandatory Git Commits**: Always commit any changes made to the codebase immediately after verification so every feature, fix, or rule addition is cleanly tracked in git.
* **Public vs. Admin Separation**: The public portal is strictly citizen-facing (simple, conversational, zero-form, no admin links). The internal staff/admin desk must only be accessed via its dedicated special URL (`/admin` or `#/admin`).

