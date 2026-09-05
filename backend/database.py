"""
SIH26034 LMPC Compliance Engine — Database Setup

Async SQLAlchemy engine and session factory for SQLite (dev)
or PostgreSQL (prod). Uses aiosqlite for async SQLite support.
"""

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from backend.config import settings


from urllib.parse import parse_qs, urlencode, urlparse, urlunparse


def _get_engine_config():
    """Build normalized database URL and engine options for PostgreSQL or SQLite."""
    raw_url = str(settings.DATABASE_URL or "sqlite+aiosqlite:///./lmpc_audits.db").strip()

    # Automatically normalize PostgreSQL URLs from cloud providers (Neon, Supabase, Render, Railway)
    if raw_url.startswith("postgres://"):
        norm_url = raw_url.replace("postgres://", "postgresql+asyncpg://", 1)
    elif raw_url.startswith("postgresql://") and "+asyncpg" not in raw_url:
        norm_url = raw_url.replace("postgresql://", "postgresql+asyncpg://", 1)
    else:
        norm_url = raw_url

    is_sqlite = norm_url.startswith("sqlite")
    kwargs = {
        "echo": settings.DEBUG,
        "future": True,
    }

    if is_sqlite:
        kwargs["connect_args"] = {"check_same_thread": False}
    else:
        # Sanitize query parameters for asyncpg
        parsed = urlparse(norm_url)
        if parsed.query:
            qs = parse_qs(parsed.query)
            # Remove unsupported asyncpg parameters
            qs.pop("channel_binding", None)
            if "sslmode" in qs:
                sslmode_val = qs.pop("sslmode", ["require"])[0]
                if sslmode_val in ("require", "verify-ca", "verify-full", "prefer"):
                    qs["ssl"] = ["require"]
            clean_query = urlencode(qs, doseq=True)
            norm_url = urlunparse(parsed._replace(query=clean_query))

        # Production PostgreSQL connection pool
        kwargs["pool_size"] = 10
        kwargs["max_overflow"] = 20
        kwargs["pool_pre_ping"] = True
        kwargs["pool_recycle"] = 300

    return norm_url, kwargs


_db_url, _engine_kwargs = _get_engine_config()
engine = create_async_engine(_db_url, **_engine_kwargs)

async_session = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    """Base class for all ORM models."""
    pass


async def init_db() -> None:
    """Create all tables on startup and apply additive column migrations."""
    import backend.models  # noqa: F401
    from sqlalchemy import text
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        columns = [
            ("trust_score", "FLOAT"),
            ("expiry_status", "VARCHAR(30)"),
            ("is_expired", "BOOLEAN DEFAULT FALSE"),
            ("days_until_expiry", "INTEGER"),
            ("barcode_number", "VARCHAR(50)"),
            ("fssai_license_number", "VARCHAR(20)"),
        ]
        for col, col_type in columns:
            try:
                await conn.execute(text(f"ALTER TABLE audits ADD COLUMN IF NOT EXISTS {col} {col_type};"))
            except Exception:
                pass


async def get_db() -> AsyncSession:
    """FastAPI dependency — yields an async database session."""
    async with async_session() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
