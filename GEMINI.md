# Project Guidelines: Host Community Case Management Platform (Gaslit)

## Core Focus
* **Primary Intake Engine**: SwiftAgents in-browser AI conversational agent (`https://widget.swiftagents.org`).
* **Database**: Neon Serverless PostgreSQL with SQLAlchemy async ORM (with local dev fallback).
* **UI**: Preserve the established workspace layout, brand identity, and clean ergonomics while elevating design taste and adding SwiftAgents triggers and monitoring views.

## Architecture
* **Frontend**: React 19 + TypeScript + Vite (`frontend/`).
* **Backend**: FastAPI (`backend/`).
* **MCP & Tooling**: Neon MCP server configured in `.agents/mcp_config.json`.
