"""
$COPPER Database Connection

Async PostgreSQL connection using SQLAlchemy with asyncpg.
"""

import ssl
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import declarative_base
from sqlalchemy.pool import NullPool, AsyncAdaptedQueuePool

from app.config import get_settings

settings = get_settings()


def prepare_database_url(url: str) -> tuple[str, dict]:
    """
    Prepare database URL for asyncpg.

    Converts postgres:// to postgresql+asyncpg:// and handles SSL properly.
    asyncpg doesn't accept sslmode as a query param - needs ssl context.
    """
    # Convert to asyncpg driver
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql+asyncpg://", 1)
    elif url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+asyncpg://", 1)

    # Parse URL and remove sslmode from query params (asyncpg doesn't support it)
    parsed = urlparse(url)
    query_params = parse_qs(parsed.query)

    # Check if SSL is required
    ssl_mode = query_params.pop("sslmode", ["require"])[0]
    needs_ssl = ssl_mode in ("require", "verify-ca", "verify-full")

    # Rebuild URL without sslmode
    new_query = urlencode(query_params, doseq=True)
    clean_url = urlunparse((
        parsed.scheme,
        parsed.netloc,
        parsed.path,
        parsed.params,
        new_query,
        parsed.fragment
    ))

    # Build connect_args with proper SSL context for asyncpg
    connect_args = {
        "command_timeout": 30,  # 30 second query timeout
    }

    if needs_ssl:
        # Create SSL context for asyncpg
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
        connect_args["ssl"] = ssl_context

    return clean_url, connect_args


# Prepare database URL and connection args
database_url, connect_args = prepare_database_url(settings.database_url)

# Create async engine
# Use NullPool for serverless (Neon), connection pool otherwise
engine = create_async_engine(
    database_url,
    echo=settings.debug,
    poolclass=NullPool if settings.is_production else AsyncAdaptedQueuePool,
    pool_size=5 if not settings.is_production else None,
    max_overflow=10 if not settings.is_production else None,
    pool_pre_ping=True,  # Verify connections before use
    connect_args=connect_args
)

# Session factory
async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False
)

# Base class for models
Base = declarative_base()


async def get_db() -> AsyncSession:
    """
    Dependency that provides a database session.

    Usage:
        @app.get("/")
        async def route(db: AsyncSession = Depends(get_db)):
            ...
    """
    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db():
    """Initialize database connection (for startup)."""
    async with engine.begin() as conn:
        # Verify connection works using proper text() wrapper
        await conn.execute(text("SELECT 1"))


async def close_db():
    """Close database connections (for shutdown)."""
    await engine.dispose()
