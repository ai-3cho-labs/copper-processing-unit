"""
$COPPER WebSocket Server

Socket.IO AsyncServer with Redis adapter and IP rate limiting.
"""

import logging
from typing import Optional

import socketio

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# Connection tracking for rate limiting
MAX_CONNECTIONS_PER_IP = 5

# Create Socket.IO server
sio = socketio.AsyncServer(
    async_mode="asgi",
    cors_allowed_origins=settings.cors_origins_list,
    logger=not settings.is_production,
    engineio_logger=False,  # Too verbose
    ping_timeout=20,
    ping_interval=25,
)

# Create ASGI app wrapper
socket_app = socketio.ASGIApp(
    sio,
    socketio_path="",  # Socket.IO path handled by FastAPI mount
)


async def setup_redis_adapter() -> None:
    """
    Setup Redis adapter for multi-worker pub/sub.

    Called during application startup if Redis is configured.
    """
    if not settings.redis_url:
        logger.warning("No Redis URL configured, WebSocket will run in single-worker mode")
        return

    try:
        # Use Redis manager for pub/sub across workers
        # Must set server reference for manager to work properly
        mgr = socketio.AsyncRedisManager(settings.redis_url)
        mgr.set_server(sio)
        sio.manager = mgr
        logger.info("WebSocket Redis adapter initialized")
    except Exception as e:
        logger.error(f"Failed to setup Redis adapter: {e}")


class ConnectionTracker:
    """
    Track connections per IP for rate limiting.

    Uses in-memory dict for single worker. For production with multiple
    workers, the Redis adapter handles cross-worker state; this tracker
    provides per-worker protection against connection floods.

    NOTE: Track sid->IP mapping to properly decrement on disconnect.
    """

    def __init__(self):
        self._connections: dict[str, int] = {}
        self._sid_to_ip: dict[str, str] = {}  # Track which IP each session belongs to

    def can_connect(self, ip: str) -> bool:
        """Check if IP can make another connection."""
        current = self._connections.get(ip, 0)
        return current < MAX_CONNECTIONS_PER_IP

    def add_connection(self, sid: str, ip: str) -> None:
        """Track a new connection."""
        self._connections[ip] = self._connections.get(ip, 0) + 1
        self._sid_to_ip[sid] = ip
        logger.debug(f"Connection added for {ip}: {self._connections[ip]} total")

    def remove_connection(self, sid: str) -> None:
        """Remove a connection from tracking by session ID."""
        ip = self._sid_to_ip.pop(sid, None)
        if ip and ip in self._connections:
            self._connections[ip] = max(0, self._connections[ip] - 1)
            if self._connections[ip] == 0:
                del self._connections[ip]
            logger.debug(f"Connection removed for {ip}")

    def get_count(self, ip: str) -> int:
        """Get current connection count for an IP."""
        return self._connections.get(ip, 0)

    def get_ip_for_sid(self, sid: str) -> Optional[str]:
        """Get the IP address for a session ID."""
        return self._sid_to_ip.get(sid)


# Global connection tracker instance
connection_tracker = ConnectionTracker()


def get_client_ip(environ: dict) -> str:
    """
    Extract client IP from ASGI environ.

    Handles X-Forwarded-For header for reverse proxies.

    SECURITY WARNING: X-Forwarded-For can be spoofed by clients!

    PRODUCTION REQUIREMENT: Your reverse proxy (Koyeb, nginx, etc.) MUST:
    1. Set X-Forwarded-For to the actual client IP
    2. Overwrite (not append to) any existing X-Forwarded-For header
    3. Not trust upstream X-Forwarded-For values

    Koyeb automatically handles this correctly for incoming requests.
    If using a different proxy, configure it accordingly.

    Without proper proxy configuration, attackers can:
    - Bypass per-IP rate limiting by spoofing different IPs
    - Evade IP-based blocking or monitoring
    """
    # Check for forwarded header (from reverse proxy)
    forwarded = environ.get("HTTP_X_FORWARDED_FOR", "")
    if forwarded:
        # First IP in the list is the original client (set by outermost proxy)
        # Validate it looks like an IP address (basic sanity check)
        client_ip = forwarded.split(",")[0].strip()
        # Basic validation: should contain only IP-valid characters
        if client_ip and all(c in "0123456789.:" for c in client_ip):
            return client_ip
        # If malformed, log and fall through to direct client
        logger.warning(f"Malformed X-Forwarded-For header: {forwarded[:50]}")

    # Fall back to direct client address
    client = environ.get("asgi.scope", {}).get("client", ("unknown", 0))
    if isinstance(client, (list, tuple)) and len(client) >= 1:
        return str(client[0])

    return "unknown"


# Room names
GLOBAL_ROOM = "global"


def wallet_room(wallet: str) -> str:
    """Get room name for a wallet."""
    return f"wallet:{wallet}"
