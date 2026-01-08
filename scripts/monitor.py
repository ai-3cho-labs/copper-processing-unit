#!/usr/bin/env python3
"""
$COPPER System Monitor

Comprehensive health checks for all system components.

Usage:
    python monitor.py                    # Single check
    python monitor.py --continuous       # Daemon mode
    python monitor.py --interval 30      # Custom interval (seconds)
    python monitor.py --json             # JSON output
"""

import argparse
import asyncio
import json
import sys
import time
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Optional

# Add backend to path for imports
sys.path.insert(0, '../backend')

import httpx


@dataclass
class HealthCheck:
    """Result of a health check."""
    name: str
    status: str  # 'ok', 'warn', 'fail'
    latency_ms: Optional[float] = None
    message: Optional[str] = None


def utc_now() -> datetime:
    """Get current UTC time."""
    return datetime.now(timezone.utc)


async def check_database() -> HealthCheck:
    """Check database connectivity."""
    start = time.perf_counter()
    try:
        # Import here to avoid issues if backend not installed
        from app.database import async_session_maker
        from sqlalchemy import text

        async with async_session_maker() as db:
            await db.execute(text("SELECT 1"))

        latency = (time.perf_counter() - start) * 1000
        return HealthCheck(
            name="Database",
            status="ok",
            latency_ms=round(latency, 2),
        )
    except Exception as e:
        return HealthCheck(
            name="Database",
            status="fail",
            message=str(e),
        )


async def check_redis() -> HealthCheck:
    """Check Redis connectivity."""
    start = time.perf_counter()
    try:
        from app.config import get_settings
        import redis.asyncio as redis

        settings = get_settings()
        if not settings.redis_url:
            return HealthCheck(
                name="Redis",
                status="warn",
                message="No Redis URL configured",
            )

        client = redis.from_url(settings.redis_url)
        await client.ping()
        await client.close()

        latency = (time.perf_counter() - start) * 1000
        return HealthCheck(
            name="Redis",
            status="ok",
            latency_ms=round(latency, 2),
        )
    except Exception as e:
        return HealthCheck(
            name="Redis",
            status="fail",
            message=str(e),
        )


async def check_api() -> HealthCheck:
    """Check API health endpoint."""
    start = time.perf_counter()
    try:
        from app.config import get_settings
        settings = get_settings()

        url = f"http://{settings.api_host}:{settings.api_port}/api/health"

        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(url)
            response.raise_for_status()

        latency = (time.perf_counter() - start) * 1000
        return HealthCheck(
            name="API",
            status="ok",
            latency_ms=round(latency, 2),
        )
    except Exception as e:
        return HealthCheck(
            name="API",
            status="fail",
            message=str(e),
        )


async def check_helius() -> HealthCheck:
    """Check Helius API connectivity."""
    start = time.perf_counter()
    try:
        from app.config import get_settings
        settings = get_settings()

        if not settings.helius_api_key:
            return HealthCheck(
                name="Helius API",
                status="warn",
                message="No API key configured",
            )

        url = f"https://api.helius.xyz/v0/webhooks?api-key={settings.helius_api_key}"

        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(url)
            response.raise_for_status()

        latency = (time.perf_counter() - start) * 1000
        return HealthCheck(
            name="Helius API",
            status="ok",
            latency_ms=round(latency, 2),
        )
    except Exception as e:
        return HealthCheck(
            name="Helius API",
            status="fail",
            message=str(e),
        )


async def check_solana_rpc() -> HealthCheck:
    """Check Solana RPC connectivity."""
    start = time.perf_counter()
    try:
        from app.config import get_settings
        settings = get_settings()

        if not settings.solana_rpc_url:
            return HealthCheck(
                name="Solana RPC",
                status="warn",
                message="No RPC URL configured",
            )

        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.post(
                settings.solana_rpc_url,
                json={
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "getHealth",
                },
            )
            response.raise_for_status()
            data = response.json()

            if "error" in data:
                return HealthCheck(
                    name="Solana RPC",
                    status="warn",
                    message=data["error"].get("message", "Unknown error"),
                )

        latency = (time.perf_counter() - start) * 1000
        return HealthCheck(
            name="Solana RPC",
            status="ok",
            latency_ms=round(latency, 2),
        )
    except Exception as e:
        return HealthCheck(
            name="Solana RPC",
            status="fail",
            message=str(e),
        )


async def check_celery() -> HealthCheck:
    """Check Celery worker status via Redis."""
    try:
        from app.config import get_settings
        import redis.asyncio as redis

        settings = get_settings()
        if not settings.redis_url:
            return HealthCheck(
                name="Celery Workers",
                status="warn",
                message="No Redis URL configured",
            )

        client = redis.from_url(settings.redis_url)

        # Check for active workers by looking at celery keys
        keys = await client.keys("celery*")
        await client.close()

        if keys:
            return HealthCheck(
                name="Celery Workers",
                status="ok",
                message=f"{len(keys)} celery keys found",
            )
        else:
            return HealthCheck(
                name="Celery Workers",
                status="warn",
                message="No celery keys found (workers may not be running)",
            )
    except Exception as e:
        return HealthCheck(
            name="Celery Workers",
            status="fail",
            message=str(e),
        )


async def check_pool_balance() -> HealthCheck:
    """Check airdrop pool balance."""
    try:
        from app.database import async_session_maker
        from app.services.distribution import DistributionService

        async with async_session_maker() as db:
            service = DistributionService(db)
            balance = await service.get_pool_balance()
            value_usd = await service.get_pool_value_usd()

        return HealthCheck(
            name="Pool Balance",
            status="ok",
            message=f"{balance:,} tokens (${float(value_usd):.2f} USD)",
        )
    except Exception as e:
        return HealthCheck(
            name="Pool Balance",
            status="fail",
            message=str(e),
        )


async def check_recent_snapshots() -> HealthCheck:
    """Check if snapshots are being taken."""
    try:
        from app.database import async_session_maker
        from app.models import Snapshot
        from sqlalchemy import select

        async with async_session_maker() as db:
            result = await db.execute(
                select(Snapshot)
                .order_by(Snapshot.created_at.desc())
                .limit(1)
            )
            snapshot = result.scalar_one_or_none()

        if not snapshot:
            return HealthCheck(
                name="Snapshots",
                status="warn",
                message="No snapshots found",
            )

        # Check if last snapshot was within 6 hours
        age_hours = (utc_now() - snapshot.created_at).total_seconds() / 3600

        if age_hours > 6:
            return HealthCheck(
                name="Snapshots",
                status="warn",
                message=f"Last snapshot {age_hours:.1f}h ago (>6h)",
            )

        return HealthCheck(
            name="Snapshots",
            status="ok",
            message=f"Last snapshot {age_hours:.1f}h ago",
        )
    except Exception as e:
        return HealthCheck(
            name="Snapshots",
            status="fail",
            message=str(e),
        )


async def check_webhooks() -> HealthCheck:
    """Check Helius webhook status."""
    try:
        from app.config import get_settings
        settings = get_settings()

        if not settings.helius_api_key:
            return HealthCheck(
                name="Webhooks",
                status="warn",
                message="No Helius API key configured",
            )

        url = f"https://api.helius.xyz/v0/webhooks?api-key={settings.helius_api_key}"

        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(url)
            response.raise_for_status()
            webhooks = response.json()

        if not webhooks:
            return HealthCheck(
                name="Webhooks",
                status="warn",
                message="No webhooks registered",
            )

        return HealthCheck(
            name="Webhooks",
            status="ok",
            message=f"{len(webhooks)} webhook(s) registered",
        )
    except Exception as e:
        return HealthCheck(
            name="Webhooks",
            status="fail",
            message=str(e),
        )


async def run_all_checks() -> list[HealthCheck]:
    """Run all health checks in parallel."""
    checks = await asyncio.gather(
        check_database(),
        check_redis(),
        check_api(),
        check_helius(),
        check_solana_rpc(),
        check_celery(),
        check_pool_balance(),
        check_recent_snapshots(),
        check_webhooks(),
    )
    return list(checks)


def format_status(status: str) -> str:
    """Format status with color indicator."""
    if status == "ok":
        return "[OK]"
    elif status == "warn":
        return "[WARN]"
    else:
        return "[FAIL]"


def print_results(checks: list[HealthCheck], as_json: bool = False):
    """Print health check results."""
    if as_json:
        output = {
            "timestamp": utc_now().isoformat(),
            "checks": [asdict(c) for c in checks],
            "summary": {
                "ok": sum(1 for c in checks if c.status == "ok"),
                "warn": sum(1 for c in checks if c.status == "warn"),
                "fail": sum(1 for c in checks if c.status == "fail"),
            },
        }
        print(json.dumps(output, indent=2))
    else:
        print(f"\n$COPPER Health Check - {utc_now().strftime('%Y-%m-%d %H:%M:%S UTC')}")
        print("=" * 60)

        for check in checks:
            status_str = format_status(check.status)
            latency_str = f" ({check.latency_ms}ms)" if check.latency_ms else ""
            message_str = f" - {check.message}" if check.message else ""
            print(f"{status_str:8} {check.name:20}{latency_str}{message_str}")

        print("=" * 60)
        ok = sum(1 for c in checks if c.status == "ok")
        warn = sum(1 for c in checks if c.status == "warn")
        fail = sum(1 for c in checks if c.status == "fail")
        print(f"Summary: {ok} OK, {warn} WARN, {fail} FAIL")


def get_exit_code(checks: list[HealthCheck]) -> int:
    """Get exit code based on check results."""
    if any(c.status == "fail" for c in checks):
        return 2  # Critical failure
    if any(c.status == "warn" for c in checks):
        return 1  # Some warnings
    return 0  # All healthy


async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="$COPPER System Monitor - Health checks for all components"
    )
    parser.add_argument(
        "--continuous",
        action="store_true",
        help="Run continuously in daemon mode",
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=60,
        help="Interval between checks in seconds (default: 60)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output results as JSON",
    )

    args = parser.parse_args()

    if args.continuous:
        print(f"Starting continuous monitoring (interval: {args.interval}s)...")
        print("Press Ctrl+C to stop.\n")

        try:
            while True:
                checks = await run_all_checks()
                print_results(checks, as_json=args.json)
                await asyncio.sleep(args.interval)
        except KeyboardInterrupt:
            print("\nMonitoring stopped.")
    else:
        checks = await run_all_checks()
        print_results(checks, as_json=args.json)
        sys.exit(get_exit_code(checks))


if __name__ == "__main__":
    asyncio.run(main())
