import asyncio
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from .config import settings
from .models import Base

_engine: AsyncEngine | None = None
_session_maker: async_sessionmaker[AsyncSession] | None = None


def sanitize_database_url(url: str) -> tuple[str, dict]:
    """
    Sanitize database connection URLs for asyncpg:
    1. Normalizes postgres/postgresql prefixes to postgresql+asyncpg://
    2. Strips 'sslmode' query parameter (asyncpg does not accept sslmode and raises TypeError)
    3. Injects connect_args['ssl'] = True for Neon and SSL-enabled connections
    """
    connect_args: dict = {}

    if url.startswith("postgres://"):
        url = "postgresql+asyncpg://" + url[len("postgres://"):]
    elif url.startswith("postgresql://"):
        url = "postgresql+asyncpg://" + url[len("postgresql://"):]

    if "postgresql" in url:
        parsed = urlsplit(url)
        query_params = dict(parse_qsl(parsed.query))

        sslmode = query_params.pop("sslmode", None)
        ssl_param = query_params.pop("ssl", None)

        if "neon.tech" in url or sslmode in ("require", "verify-ca", "verify-full") or ssl_param:
            connect_args["ssl"] = True

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
    global _engine, _session_maker
    engine = get_engine()
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    except Exception as exc:
        # If external database (e.g. Neon) is unreachable or DNS lookup fails,
        # fail over to local SQLite so Render / FastAPI starts up cleanly without crashing
        if "sqlite" not in str(engine.url):
            import logging
            logging.getLogger("uvicorn.error").warning(
                "Primary database connection failed on startup (%s: %s). Falling back to local SQLite to keep server operational.",
                type(exc).__name__,
                exc,
            )
            fallback_url = f"sqlite+aiosqlite:///{settings.database_path}"
            _engine = create_async_engine(fallback_url, pool_pre_ping=True, echo=False)
            _session_maker = async_sessionmaker(
                bind=_engine,
                class_=AsyncSession,
                expire_on_commit=False,
                autoflush=False,
            )
            async with _engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
        else:
            raise


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
