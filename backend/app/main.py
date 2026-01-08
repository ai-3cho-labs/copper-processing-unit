"""
$COPPER Backend API

FastAPI application entry point.
"""

import logging
import re
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request


class SensitiveDataFilter(logging.Filter):
    """Filter to mask sensitive data in log messages."""

    # Pattern matches Base58 private keys (64 bytes = ~88 chars)
    PRIVATE_KEY_PATTERN = re.compile(r'[1-9A-HJ-NP-Za-km-z]{60,90}')
    # Pattern matches common secret-like values
    SECRET_PATTERNS = [
        re.compile(r'(private[_-]?key["\s:=]+)[^\s"\']+', re.IGNORECASE),
        re.compile(r'(secret["\s:=]+)[^\s"\']+', re.IGNORECASE),
    ]

    def filter(self, record: logging.LogRecord) -> bool:
        """Mask sensitive data in log messages."""
        if record.msg:
            msg = str(record.msg)
            # Mask long Base58-like strings that could be private keys
            msg = self.PRIVATE_KEY_PATTERN.sub('[REDACTED_KEY]', msg)
            # Mask explicit secret patterns
            for pattern in self.SECRET_PATTERNS:
                msg = pattern.sub(r'\1[REDACTED]', msg)
            record.msg = msg
        return True


from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.config import get_settings
from app.database import init_db, close_db
from app.utils.http_client import close_http_client
from app.utils.rate_limiter import limiter, validate_rate_limiter_config
from app.websocket import socket_app, setup_redis_adapter

# Configure logging with sensitive data filter
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
# Add sensitive data filter to root logger
for handler in logging.root.handlers:
    handler.addFilter(SensitiveDataFilter())
logger = logging.getLogger("copper")
logger.addFilter(SensitiveDataFilter())

settings = get_settings()

# Initialize Sentry for error tracking (if configured)
if settings.sentry_dsn:
    try:
        import sentry_sdk
        from sentry_sdk.integrations.fastapi import FastApiIntegration
        from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
        from sentry_sdk.integrations.celery import CeleryIntegration
        from sentry_sdk.integrations.logging import LoggingIntegration

        sentry_sdk.init(
            dsn=settings.sentry_dsn,
            environment=settings.environment,
            traces_sample_rate=0.1 if settings.is_production else 1.0,
            profiles_sample_rate=0.1 if settings.is_production else 1.0,
            integrations=[
                FastApiIntegration(transaction_style="endpoint"),
                SqlalchemyIntegration(),
                CeleryIntegration(),
                LoggingIntegration(
                    level=logging.INFO,
                    event_level=logging.ERROR
                ),
            ],
            send_default_pii=False,
            attach_stacktrace=True,
        )
        logger.info("Sentry initialized successfully")
    except ImportError:
        logger.warning("Sentry SDK not installed, error tracking disabled")
    except Exception as e:
        logger.error(f"Failed to initialize Sentry: {e}")
else:
    logger.info("Sentry DSN not configured, error tracking disabled")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    # Startup
    logger.info("$COPPER Backend initializing...")

    # Validate configuration
    if settings.is_production:
        if not validate_rate_limiter_config():
            logger.warning("Rate limiter configuration issues detected")
        if not settings.sentry_dsn:
            logger.warning("Sentry DSN not configured for production")
        if not settings.helius_api_key:
            logger.error("CRITICAL: Helius API key not configured")
        if not settings.copper_token_mint:
            logger.error("CRITICAL: Token mint not configured")

        # Validate wallet private keys are configured (without logging values)
        wallet_keys = [
            ("CREATOR_WALLET", settings.creator_wallet_private_key),
            ("BUYBACK_WALLET", settings.buyback_wallet_private_key),
            ("AIRDROP_POOL", settings.airdrop_pool_private_key),
        ]
        for name, key in wallet_keys:
            if not key:
                logger.error(f"CRITICAL: {name}_PRIVATE_KEY not configured")
            elif len(key) < 80 or len(key) > 90:
                logger.error(f"CRITICAL: {name}_PRIVATE_KEY invalid length (expected ~88 chars)")
            else:
                logger.info(f"{name} private key configured (length: {len(key)})")

        # Prevent test mode in production
        if settings.test_mode:
            logger.error("CRITICAL: TEST_MODE is enabled in production!")
            raise ValueError("TEST_MODE cannot be enabled in production")

    if settings.database_url:
        await init_db()
        logger.info("Database connected")
    else:
        logger.warning("No database URL configured, skipping DB init")

    # Setup WebSocket Redis adapter
    await setup_redis_adapter()
    logger.info("WebSocket server initialized")

    # Warm price cache at startup
    try:
        from app.utils.price_cache import warm_price_cache
        await warm_price_cache()
    except Exception as e:
        logger.warning(f"Failed to warm price cache: {e}")

    logger.info("$COPPER Backend ready")

    yield

    # Shutdown
    logger.info("$COPPER Backend shutting down...")

    # Close HTTP client
    await close_http_client()
    logger.info("HTTP client closed")

    # Close database
    await close_db()
    logger.info("Database connections closed")


# Create FastAPI app
app = FastAPI(
    title="$COPPER Mining API",
    description="Backend API for the $COPPER mining dashboard",
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs" if not settings.is_production else None,
    redoc_url="/redoc" if not settings.is_production else None,
)

# Add rate limiter to app state
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Add GZip compression for responses
app.add_middleware(GZipMiddleware, minimum_size=1000)

# Configure CORS with explicit allowed methods/headers
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],  # Only methods we use
    allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
    max_age=600,  # Cache preflight for 10 minutes
)


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Handle uncaught exceptions."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )


# Health check endpoint
@app.get("/api/health")
@limiter.limit("60/minute")
async def health_check(request: Request):
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "copper-backend",
        "version": "0.1.0"
    }


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "Welcome to the $COPPER Mining API",
        "docs": "/docs",
        "health": "/api/health"
    }


# Import and include routers
from app.api.routes import router as api_router
from app.api.webhook import router as webhook_router

app.include_router(api_router)
app.include_router(webhook_router)

# Mount WebSocket at /ws
app.mount("/ws", socket_app)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=not settings.is_production
    )
