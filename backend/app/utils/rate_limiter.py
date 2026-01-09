"""
$COPPER Rate Limiter Configuration

Shared rate limiter instance for the application.
Requires Redis in production for proper multi-worker rate limiting.
"""

import logging
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


def _get_storage_uri() -> str | None:
    """
    Get storage URI for rate limiter.

    In production, Redis is required for proper rate limiting across workers.
    In development, falls back to in-memory storage with a warning.

    Returns:
        Redis URL or None for in-memory storage.

    Raises:
        ValueError: If production mode and Redis is not configured.
    """
    if settings.redis_url:
        logger.info("Rate limiter: using Redis storage")
        return settings.redis_url

    if settings.is_production:
        logger.error(
            "CRITICAL: Redis URL not configured in production! "
            "Rate limiting will not work correctly across multiple workers. "
            "Set REDIS_URL environment variable."
        )
        # In production, we raise an error to prevent startup without proper config
        raise ValueError(
            "Redis URL is required for rate limiting in production. "
            "Set REDIS_URL environment variable."
        )

    logger.warning(
        "Rate limiter: using in-memory storage (development only). "
        "This will not work correctly with multiple workers."
    )
    return None


def _create_limiter() -> Limiter:
    """
    Create and configure the rate limiter instance.

    SECURITY: In production, Redis is REQUIRED for proper rate limiting.
    Without Redis, rate limits don't work across workers and attackers
    can bypass limits by hitting different workers.
    """
    try:
        storage_uri = _get_storage_uri()
    except ValueError as e:
        # SECURITY: Fail hard in production - do not allow startup without Redis
        # This prevents running production with ineffective rate limiting
        if settings.is_production:
            logger.critical(f"FATAL: {e}")
            raise RuntimeError(
                "Cannot start in production without Redis for rate limiting. "
                "Set REDIS_URL environment variable."
            )
        # In development, log warning but continue with in-memory storage
        logger.warning(str(e))
        storage_uri = None

    return Limiter(
        key_func=get_remote_address,
        storage_uri=storage_uri,
        default_limits=["200/minute"],
        strategy="fixed-window"
    )


# Create shared limiter instance
limiter = _create_limiter()


def validate_rate_limiter_config() -> bool:
    """
    Validate rate limiter configuration at startup.

    Returns:
        True if properly configured, False otherwise.
    """
    if settings.is_production and not settings.redis_url:
        logger.error(
            "Rate limiter validation failed: Redis required in production"
        )
        return False

    return True
