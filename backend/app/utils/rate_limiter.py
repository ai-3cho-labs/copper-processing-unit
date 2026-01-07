"""
$COPPER Rate Limiter Configuration

Shared rate limiter instance for the application.
"""

from slowapi import Limiter
from slowapi.util import get_remote_address

from app.config import get_settings

settings = get_settings()

# Create shared limiter instance
# Uses in-memory storage by default, configure Redis for production
limiter = Limiter(
    key_func=get_remote_address,
    storage_uri=settings.redis_url if settings.redis_url else None,
    default_limits=["200/minute"]  # Global default limit
)
