# Neon Database Guidelines

## Architecture & Conventions
1. **Primary Database Engine**: Neon Serverless PostgreSQL.
2. **Connection Handling**:
   - For FastAPI async endpoints: Use `postgresql+asyncpg://` with SSL enabled (`ssl=True` in `connect_args`).
   - Use the Neon `-pooler` endpoint for stateless application queries.
   - For local offline development when `DATABASE_URL` is unset, provide seamless fallback to SQLite (`sqlite+aiosqlite:///case_management.db`) so tests and development never fail.
3. **ORM & Migrations**:
   - Use SQLAlchemy 2.0 async declarative models (`AsyncAttrs`, `DeclarativeBase`).
   - All database sessions must be handled via `async with get_session() as session:`.
4. **Safety**:
   - Never commit database credentials or connection strings to git. Read from `.env`.
