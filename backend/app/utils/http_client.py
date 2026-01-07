"""
$COPPER HTTP Client Manager

Manages shared HTTP client lifecycle for all services.
Ensures proper connection pool management and cleanup.
"""

import logging
from contextlib import asynccontextmanager
from typing import Optional

import httpx

logger = logging.getLogger(__name__)


class HTTPClientManager:
    """
    Singleton HTTP client manager.

    Provides a shared httpx.AsyncClient that is properly initialized
    and closed with the application lifecycle.
    """

    _instance: Optional["HTTPClientManager"] = None
    _client: Optional[httpx.AsyncClient] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @property
    def client(self) -> httpx.AsyncClient:
        """Get the shared HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(30.0, connect=10.0),
                limits=httpx.Limits(
                    max_keepalive_connections=20,
                    max_connections=100,
                    keepalive_expiry=30.0
                ),
                follow_redirects=True
            )
            logger.info("HTTP client initialized")
        return self._client

    async def close(self):
        """Close the HTTP client."""
        if self._client is not None and not self._client.is_closed:
            await self._client.aclose()
            self._client = None
            logger.info("HTTP client closed")

    async def __aenter__(self):
        return self.client

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        # Don't close on context exit - let app lifecycle manage it
        pass


# Global singleton instance
_http_manager = HTTPClientManager()


def get_http_client() -> httpx.AsyncClient:
    """Get the shared HTTP client."""
    return _http_manager.client


async def close_http_client():
    """Close the shared HTTP client. Call on app shutdown."""
    await _http_manager.close()


@asynccontextmanager
async def http_client_context():
    """
    Context manager for temporary HTTP client.

    Use when you need a client that's guaranteed to close,
    not the shared singleton.
    """
    client = httpx.AsyncClient(
        timeout=httpx.Timeout(30.0, connect=10.0),
        follow_redirects=True
    )
    try:
        yield client
    finally:
        await client.aclose()
