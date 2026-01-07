"""
$COPPER Buyback Tasks

Background tasks for processing creator rewards and executing buybacks.
"""

import logging
from decimal import Decimal

from app.tasks.celery_app import celery_app
from app.database import async_session_maker
from app.services.buyback import BuybackService, process_pending_rewards
from app.utils.async_utils import run_async

logger = logging.getLogger(__name__)


@celery_app.task(name="app.tasks.buyback_task.process_creator_rewards")
def process_creator_rewards() -> dict:
    """
    Process pending creator rewards.

    Executes 80/20 split:
    - 80% → Jupiter swap SOL → COPPER → Airdrop pool
    - 20% → Team wallet
    """
    return run_async(_process_creator_rewards())


async def _process_creator_rewards() -> dict:
    """Async implementation of process_creator_rewards."""
    async with async_session_maker() as db:
        service = BuybackService(db)

        try:
            # Check for pending rewards
            total_pending = await service.get_total_unprocessed_sol()

            if total_pending == 0:
                logger.info("No pending rewards to process")
                return {
                    "status": "skipped",
                    "reason": "no_pending_rewards"
                }

            # Process rewards
            result = await process_pending_rewards(db)

            if result and result.success:
                return {
                    "status": "success",
                    "sol_spent": float(result.sol_spent),
                    "copper_received": result.copper_received,
                    "tx_signature": result.tx_signature
                }
            elif result:
                return {
                    "status": "failed",
                    "error": result.error
                }
            else:
                return {
                    "status": "skipped",
                    "reason": "no_result"
                }

        except Exception as e:
            logger.error(f"Error processing rewards: {e}")
            return {
                "status": "error",
                "error": str(e)
            }


@celery_app.task(name="app.tasks.buyback_task.record_incoming_reward")
def record_incoming_reward(
    amount_sol: float,
    source: str,
    tx_signature: str = None
) -> dict:
    """
    Record an incoming creator reward.

    Called when Pump.fun fees are detected.
    """
    return run_async(_record_incoming_reward(amount_sol, source, tx_signature))


async def _record_incoming_reward(
    amount_sol: float,
    source: str,
    tx_signature: str
) -> dict:
    """Async implementation of record_incoming_reward."""
    async with async_session_maker() as db:
        service = BuybackService(db)

        reward = await service.record_creator_reward(
            Decimal(str(amount_sol)),
            source,
            tx_signature
        )

        return {
            "status": "success",
            "reward_id": str(reward.id),
            "amount_sol": amount_sol,
            "source": source
        }


@celery_app.task(name="app.tasks.buyback_task.get_buyback_stats")
def get_buyback_stats() -> dict:
    """Get buyback statistics."""
    return run_async(_get_buyback_stats())


async def _get_buyback_stats() -> dict:
    """Async implementation of get_buyback_stats."""
    async with async_session_maker() as db:
        service = BuybackService(db)

        total_sol, total_copper = await service.get_total_buybacks()
        pending_sol = await service.get_total_unprocessed_sol()

        return {
            "total_sol_spent": float(total_sol),
            "total_copper_bought": total_copper,
            "pending_sol": float(pending_sol)
        }


# Allow running as script for testing
if __name__ == "__main__":
    result = process_creator_rewards()
    print(f"Result: {result}")
