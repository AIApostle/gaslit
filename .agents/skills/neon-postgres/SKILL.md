---
name: neon-postgres
description: Comprehensive guide and best practices for Neon Serverless Postgres in Python (FastAPI/SQLAlchemy) and Node.js. Covers connection pooling, asyncpg, branching, migrations, and MCP workflows.
---

# Neon Serverless Postgres Skill

This skill guides development with **Neon Serverless Postgres** for the Host Community Case Management Platform.

## 1. Connection Architecture & Best Practices

Neon separates compute and storage and provides two primary connection strings:
1. **Pooled Connection (`-pooler` host, port 5432 or 6543)**:
   * Uses built-in PgBouncer pooling.
   * Ideal for stateless web applications, serverless handlers, and FastAPI endpoints.
   * Format: `postgresql+asyncpg://[user]:[password]@[endpoint]-pooler.[region].aws.neon.tech/[dbname]?sslmode=require`
2. **Direct Connection (non-pooler host)**:
   * Direct connection to the Postgres compute node.
   * Required for schema migrations (Alembic) or operations using prepared statements that require session-level features.

## 2. Python / SQLAlchemy Async Configuration

Use `asyncpg` with SQLAlchemy:

```python
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase

class Base(DeclarativeBase):
    pass

def create_db_engine(database_url: str):
    # Ensure ssl is handled cleanly with asyncpg
    connect_args = {}
    if "neon.tech" in database_url:
        connect_args["ssl"] = True

    return create_async_engine(
        database_url,
        connect_args=connect_args,
        pool_size=10,
        max_overflow=20,
        pool_pre_ping=True,
    )
```

## 3. Database Branching Workflow

Neon allows instant copy-on-write database branches:
* **`main`**: Production data branch.
* **`staging` / `preview`**: Isolated dev/test branches created in seconds.
* Use the Neon MCP server tools:
  * `create_branch(project_id, branch_name)`: Spawn a test branch.
  * `execute_sql(project_id, branch_id, query)`: Run queries directly.
  * `list_projects()`: Discover available Neon projects.

## 4. Migrations & Schema Sync

* Use SQLAlchemy declarative models for the source of truth.
* For automated table initialization in development:
  ```python
  async def init_db(engine):
      async with engine.begin() as conn:
          await conn.run_sync(Base.metadata.create_all)
  ```
* For production migrations, use Alembic pointing to the non-pooled connection string.
