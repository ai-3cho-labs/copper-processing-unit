"""
$COPPER Snapshot Tasks

Background tasks for balance snapshot collection.
"""

import logging
from typing import Optional

from app.tasks.celery_app import celery_app
from app.database import async_session_maker
from app.services.snapshot import SnapshotService
from app.services.streak import StreakService
from app.utils.async_utils import run_async

logger = logging.getLogger(__name__)


@celery_app.task(name="app.tasks.snapshot_task.maybe_take_snapshot")
def maybe_take_snapshot() -> dict:
    """
    Maybe take a balance snapshot (40% probability).

    Called hourly to achieve 3-6 snapshots per day.
    """
    return run_async(_maybe_take_snapshot())


async def _maybe_take_snapshot() -> dict:
    """Async implementation of maybe_take_snapshot."""
    async with async_session_maker() as db:
        service = SnapshotService(db)

        # RNG check
        if not service.should_take_snapshot():
            logger.info("Snapshot RNG: skipping this hour")
            return {
                "status": "skipped",
                "reason": "rng"
            }

        # Take snapshot
        snapshot = await service.take_snapshot()

        if snapshot:
            return {
                "status": "success",
                "snapshot_id": str(snapshot.id),
                "holders": snapshot.total_holders,
                "supply": snapshot.total_supply
            }
        else:
            return {
                "status": "failed",
                "reason": "snapshot_error"
            }


@celery_app.task(name="app.tasks.snapshot_task.force_snapshot")
def force_snapshot() -> dict:
    """
    Force take a snapshot (bypass RNG).

    Use for testing or manual triggers.
    """
    return run_async(_force_snapshot())


async def _force_snapshot() -> dict:
    """Async implementation of force_snapshot."""
    async with async_session_maker() as db:
        service = SnapshotService(db)
        snapshot = await service.take_snapshot()

        if snapshot:
            return {
                "status": "success",
                "snapshot_id": str(snapshot.id),
                "holders": snapshot.total_holders,
                "supply": snapshot.total_supply
            }
        else:
            return {
                "status": "failed",
                "reason": "snapshot_error"
            }


@celery_app.task(name="app.tasks.snapshot_task.update_all_tiers")
def update_all_tiers() -> dict:
    """
    Update tier progressions for all wallets.

    Checks if any wallets should be promoted to higher tiers
    based on their streak duration.
    """
    return run_async(_update_all_tiers())


async def _update_all_tiers() -> dict:
    """Async implementation of update_all_tiers."""
    async with async_session_maker() as db:
        streak_service = StreakService(db)

        # Get all streaks
        streaks = await streak_service.get_all_streaks()

        updated = 0
        for streak in streaks:
            result = await streak_service.update_tier_if_needed(streak.wallet)
            if result:
                updated += 1

        logger.info(f"Tier update complete: {updated} wallets upgraded")

        return {
            "status": "success",
            "total_checked": len(streaks),
            "upgraded": updated
        }


# Allow running as script for testing
if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "force":
        result = force_snapshot()
    else:
        result = maybe_take_snapshot()

    print(f"Result: {result}")
