"""
$COPPER Backend API

FastAPI application entry point.
"""

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.config import get_settings
from app.database import init_db, close_db
from app.utils.http_client import close_http_client
from app.utils.rate_limiter import limiter

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("copper")

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    # Startup
    logger.info("$COPPER Backend initializing...")

    if settings.database_url:
        await init_db()
        logger.info("Database connected")
    else:
        logger.warning("No database URL configured, skipping DB init")

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


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=not settings.is_production
    )
