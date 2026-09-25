import asyncio
from collections.abc import AsyncGenerator
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from sqlalchemy import event
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from .config import settings
from .models import Base

_engine: AsyncEngine | None = None
_session_maker: async_sessionmaker[AsyncSession] | None = None


def sanitize_database_url(url: str) -> tuple[str, dict]:
    """Sanitize database connection URLs and configure driver connection arguments."""
    connect_args: dict = {}

    if url.startswith("sqlite"):
        if url.startswith("sqlite:///") and not url.startswith("sqlite+aiosqlite:///"):
            url = url.replace("sqlite:///", "sqlite+aiosqlite:///")
        connect_args["check_same_thread"] = False
        connect_args["timeout"] = 30
        return url, connect_args

    if url.startswith("postgres://"):
        url = "postgresql+asyncpg://" + url[len("postgres://"):]
    elif url.startswith("postgresql://"):
        url = "postgresql+asyncpg://" + url[len("postgresql://"):]

    if "postgresql" in url:
        parsed = urlsplit(url)
        query_params = dict(parse_qsl(parsed.query))
        query_params.pop("sslmode", None)
        query_params.pop("ssl", None)
        new_query = urlencode(query_params)
        clean_url = urlunsplit((parsed.scheme, parsed.netloc, parsed.path, new_query, parsed.fragment))
        return clean_url, connect_args

    return url, connect_args


def get_engine() -> AsyncEngine:
    global _engine
    if _engine is None:
        raw_url = settings.effective_database_url
        clean_url, connect_args = sanitize_database_url(raw_url)

        _engine = create_async_engine(
            clean_url,
            connect_args=connect_args,
            pool_pre_ping=True,
            echo=False,
        )

        if "sqlite" in clean_url:
            @event.listens_for(_engine.sync_engine, "connect")
            def set_sqlite_pragma(dbapi_connection, connection_record):
                cursor = dbapi_connection.cursor()
                cursor.execute("PRAGMA foreign_keys=ON")
                cursor.execute("PRAGMA journal_mode=WAL")
                cursor.execute("PRAGMA busy_timeout=5000")
                cursor.close()

    return _engine


def get_session_maker() -> async_sessionmaker[AsyncSession]:
    global _session_maker
    if _session_maker is None:
        _session_maker = async_sessionmaker(
            bind=get_engine(),
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False,
        )
    return _session_maker


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    maker = get_session_maker()
    async with maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db_async() -> None:
    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


def initialize_database() -> None:
    """Synchronous bridge to initialize tables at app startup or in tests."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop and loop.is_running():
        asyncio.create_task(init_db_async())
    else:
        asyncio.run(init_db_async())


async def close_database() -> None:
    global _engine, _session_maker
    if _engine is not None:
        await _engine.dispose()
        _engine = None
        _session_maker = None
