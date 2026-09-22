# Project Guidelines: Host Community Case Management Platform (Gaslit)

## Core Focus
* **Primary Intake Engine**: SwiftAgents in-browser AI conversational agent (`https://widget.swiftagents.org`).
* **Database**: Neon Serverless PostgreSQL with SQLAlchemy async ORM (with local dev fallback).
* **UI**: Preserve the established workspace layout, brand identity, and clean ergonomics while elevating design taste and adding SwiftAgents triggers and monitoring views.

## Architecture
* **Frontend**: React 19 + TypeScript + Vite (`frontend/`).
* **Backend**: FastAPI (`backend/`).
## Workflow & Version Control Rules
* **Mandatory Git Commits**: Always commit any changes made to the codebase immediately after verification so every feature, fix, or rule addition is cleanly tracked in git.
* **Public vs. Admin Separation**: The public portal is strictly citizen-facing (simple, conversational, zero-form, no admin links). The internal staff/admin desk must only be accessed via its dedicated special URL (`/admin` or `#/admin`).
