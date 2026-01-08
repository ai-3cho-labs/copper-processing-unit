"""
$COPPER Buyback Service

Processes creator rewards and executes Jupiter swaps.
80% → Buybacks (SOL → COPPER) → Airdrop Pool
20% → Team Operations
"""

import logging
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional
from dataclasses import dataclass

from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import CreatorReward, Buyback, SystemStats
from app.config import get_settings, LAMPORTS_PER_SOL, SOL_MINT
from app.utils.http_client import get_http_client
from app.utils.solana_tx import sign_and_send_transaction, send_sol_transfer, confirm_transaction

logger = logging.getLogger(__name__)
settings = get_settings()


def utc_now() -> datetime:
    """Get current UTC time (timezone-aware)."""
    return datetime.now(timezone.utc)

JUPITER_QUOTE_API = "https://quote-api.jup.ag/v6/quote"
JUPITER_SWAP_API = "https://quote-api.jup.ag/v6/swap"


@dataclass
class BuybackResult:
    """Result of a buyback execution."""
    success: bool
    tx_signature: Optional[str]
    sol_spent: Decimal
    copper_received: int
    price_per_token: Optional[Decimal]
    error: Optional[str] = None


@dataclass
class RewardSplit:
    """80/20 split of creator rewards."""
    total_sol: Decimal
    buyback_sol: Decimal  # 80%
    team_sol: Decimal  # 20%


class BuybackService:
    """Service for processing buybacks from creator rewards."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.token_mint = settings.copper_token_mint

    @property
    def client(self):
        """Get shared HTTP client."""
        return get_http_client()

    async def get_unprocessed_rewards(self) -> list[CreatorReward]:
        """
        Get all unprocessed creator rewards.

        Returns:
            List of unprocessed CreatorReward records.
        """
        result = await self.db.execute(
            select(CreatorReward)
            .where(CreatorReward.processed == False)
            .order_by(CreatorReward.received_at.asc())
        )
        return list(result.scalars().all())

    async def get_total_unprocessed_sol(self) -> Decimal:
        """
        Get total SOL from unprocessed rewards.

        Returns:
            Total unprocessed SOL amount.
        """
        result = await self.db.execute(
            select(func.sum(CreatorReward.amount_sol))
            .where(CreatorReward.processed == False)
        )
        total = result.scalar_one_or_none()
        return Decimal(total) if total else Decimal(0)

    def calculate_split(self, total_sol: Decimal) -> RewardSplit:
        """
        Calculate 80/20 split of rewards.

        Args:
            total_sol: Total SOL to split.

        Returns:
            RewardSplit with buyback and team amounts.
        """
        buyback_sol = total_sol * Decimal("0.8")
        team_sol = total_sol * Decimal("0.2")

        return RewardSplit(
            total_sol=total_sol,
            buyback_sol=buyback_sol,
            team_sol=team_sol
        )

    async def get_jupiter_quote(
        self,
        sol_amount_lamports: int
    ) -> Optional[dict]:
        """
        Get swap quote from Jupiter.

        Args:
            sol_amount_lamports: Amount of SOL in lamports.

        Returns:
            Jupiter quote response, or None if error.
        """
        if not self.token_mint:
            logger.error("Token mint not configured")
            return None

        try:
            response = await self.client.get(
                JUPITER_QUOTE_API,
                params={
                    "inputMint": SOL_MINT,
                    "outputMint": self.token_mint,
                    "amount": str(sol_amount_lamports),
                    "slippageBps": 100,  # 1% slippage
                    "onlyDirectRoutes": False,
                    "asLegacyTransaction": False
                }
            )
            response.raise_for_status()
            return response.json()

        except Exception as e:
            logger.error(f"Error getting Jupiter quote: {e}")
            return None

    async def execute_swap(
        self,
        sol_amount: Decimal,
        wallet_private_key: str
    ) -> BuybackResult:
        """
        Execute a Jupiter swap (SOL → COPPER).

        Args:
            sol_amount: Amount of SOL to swap.
            wallet_private_key: Base58 private key of buyback wallet.

        Returns:
            BuybackResult with transaction details.
        """
        if not wallet_private_key:
            return BuybackResult(
                success=False,
                tx_signature=None,
                sol_spent=Decimal(0),
                copper_received=0,
                price_per_token=None,
                error="Wallet private key not configured"
            )

        lamports = int(sol_amount * LAMPORTS_PER_SOL)

        # Get quote
        quote = await self.get_jupiter_quote(lamports)
        if not quote:
            return BuybackResult(
                success=False,
                tx_signature=None,
                sol_spent=Decimal(0),
                copper_received=0,
                price_per_token=None,
                error="Failed to get Jupiter quote"
            )

        try:
            # Get the public key from private key for the swap
            from app.utils.solana_tx import keypair_from_base58
            keypair = keypair_from_base58(wallet_private_key)
            user_public_key = str(keypair.pubkey())

            # Get swap transaction from Jupiter
            swap_response = await self.client.post(
                JUPITER_SWAP_API,
                json={
                    "quoteResponse": quote,
                    "userPublicKey": user_public_key,
                    "wrapAndUnwrapSol": True,
                    "dynamicComputeUnitLimit": True,
                    "prioritizationFeeLamports": "auto"
                }
            )
            swap_response.raise_for_status()
            swap_data = swap_response.json()

            swap_tx = swap_data.get("swapTransaction")
            if not swap_tx:
                return BuybackResult(
                    success=False,
                    tx_signature=None,
                    sol_spent=Decimal(0),
                    copper_received=0,
                    price_per_token=None,
                    error="No swap transaction returned from Jupiter"
                )

            # Sign and send the transaction
            tx_result = await sign_and_send_transaction(
                serialized_tx=swap_tx,
                private_key=wallet_private_key,
                skip_preflight=False
            )

            if not tx_result.success:
                return BuybackResult(
                    success=False,
                    tx_signature=None,
                    sol_spent=Decimal(0),
                    copper_received=0,
                    price_per_token=None,
                    error=tx_result.error or "Transaction failed"
                )

            # Wait for confirmation
            confirmed = await confirm_transaction(tx_result.signature, timeout_seconds=30)
            if not confirmed:
                logger.warning(f"Transaction sent but not confirmed: {tx_result.signature}")

            # Calculate results from quote
            out_amount = int(quote.get("outAmount", 0))
            price_per_token = None
            if out_amount > 0:
                price_per_token = sol_amount / Decimal(out_amount)

            logger.info(
                f"Swap executed: {tx_result.signature}, "
                f"{sol_amount} SOL → {out_amount} COPPER"
            )

            return BuybackResult(
                success=True,
                tx_signature=tx_result.signature,
                sol_spent=sol_amount,
                copper_received=out_amount,
                price_per_token=price_per_token
            )

        except Exception as e:
            logger.error(f"Error executing swap: {e}", exc_info=True)
            return BuybackResult(
                success=False,
                tx_signature=None,
                sol_spent=Decimal(0),
                copper_received=0,
                price_per_token=None,
                error=str(e)
            )

    async def record_buyback(
        self,
        tx_signature: str,
        sol_amount: Decimal,
        copper_amount: int,
        price_per_token: Optional[Decimal] = None
    ) -> Buyback:
        """
        Record a buyback transaction in the database.

        Args:
            tx_signature: Solana transaction signature.
            sol_amount: SOL spent.
            copper_amount: COPPER received.
            price_per_token: Price per COPPER token in SOL.

        Returns:
            Created Buyback record.
        """
        buyback = Buyback(
            tx_signature=tx_signature,
            sol_amount=sol_amount,
            copper_amount=copper_amount,
            price_per_token=price_per_token,
            executed_at=utc_now()
        )
        self.db.add(buyback)

        # Update system stats
        await self._update_system_stats(sol_amount)

        await self.db.commit()

        logger.info(
            f"Recorded buyback: {tx_signature}, "
            f"{sol_amount} SOL → {copper_amount} COPPER"
        )
        return buyback

    async def mark_rewards_processed(self, reward_ids: list) -> None:
        """
        Mark creator rewards as processed.

        Args:
            reward_ids: List of reward IDs to mark.
        """
        result = await self.db.execute(
            select(CreatorReward)
            .where(CreatorReward.id.in_(reward_ids))
        )
        rewards = result.scalars().all()

        for reward in rewards:
            reward.processed = True

        await self.db.commit()
        logger.info(f"Marked {len(reward_ids)} rewards as processed")

    async def record_creator_reward(
        self,
        amount_sol: Decimal,
        source: str,
        tx_signature: Optional[str] = None
    ) -> CreatorReward:
        """
        Record an incoming creator reward.

        Args:
            amount_sol: Amount of SOL received.
            source: Source of reward ('pumpfun' or 'pumpswap').
            tx_signature: Transaction signature.

        Returns:
            Created CreatorReward record.
        """
        reward = CreatorReward(
            amount_sol=amount_sol,
            source=source,
            tx_signature=tx_signature,
            received_at=utc_now()
        )
        self.db.add(reward)
        await self.db.commit()

        logger.info(f"Recorded creator reward: {amount_sol} SOL from {source}")
        return reward

    async def get_recent_buybacks(self, limit: int = 10) -> list[Buyback]:
        """
        Get recent buyback transactions.

        Args:
            limit: Maximum number to return.

        Returns:
            List of recent Buyback records.
        """
        result = await self.db.execute(
            select(Buyback)
            .order_by(Buyback.executed_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_total_buybacks(self) -> tuple[Decimal, int]:
        """
        Get total buyback statistics.

        Returns:
            Tuple of (total_sol_spent, total_copper_bought).
        """
        result = await self.db.execute(
            select(
                func.sum(Buyback.sol_amount),
                func.sum(Buyback.copper_amount)
            )
        )
        row = result.one()
        return (
            Decimal(row[0]) if row[0] else Decimal(0),
            int(row[1]) if row[1] else 0
        )

    async def _update_system_stats(self, sol_amount: Decimal):
        """Update system stats with buyback amount."""
        result = await self.db.execute(
            select(SystemStats).where(SystemStats.id == 1)
        )
        stats = result.scalar_one_or_none()

        if stats:
            stats.total_buybacks = (stats.total_buybacks or Decimal(0)) + sol_amount
            stats.updated_at = utc_now()


async def transfer_to_team_wallet(
    amount_sol: Decimal,
    from_private_key: str,
    to_address: str
) -> Optional[str]:
    """
    Transfer SOL to team wallet (20% of creator rewards).

    Args:
        amount_sol: Amount of SOL to transfer.
        from_private_key: Private key of source wallet.
        to_address: Team wallet public address.

    Returns:
        Transaction signature if successful, None otherwise.
    """
    if not from_private_key or not to_address:
        logger.error("Team wallet transfer: missing private key or address")
        return None

    if amount_sol <= 0:
        logger.warning("Team wallet transfer: amount is zero or negative")
        return None

    lamports = int(amount_sol * LAMPORTS_PER_SOL)

    result = await send_sol_transfer(
        from_private_key=from_private_key,
        to_address=to_address,
        amount_lamports=lamports
    )

    if result.success:
        logger.info(f"Team wallet transfer: {result.signature}, {amount_sol} SOL")
        return result.signature
    else:
        logger.error(f"Team wallet transfer failed: {result.error}")
        return None


async def process_pending_rewards(db: AsyncSession) -> Optional[BuybackResult]:
    """
    Process all pending creator rewards.

    Main entry point for the buyback task.
    - 80% goes to Jupiter swap (SOL → COPPER) for airdrop pool
    - 20% goes to team wallet for operations

    Args:
        db: Database session.

    Returns:
        BuybackResult if buyback was executed, None if no rewards.
    """
    service = BuybackService(db)

    # Get unprocessed rewards
    rewards = await service.get_unprocessed_rewards()
    if not rewards:
        logger.info("No pending rewards to process")
        return None

    total_sol = sum(r.amount_sol for r in rewards)
    split = service.calculate_split(total_sol)

    logger.info(
        f"Processing {len(rewards)} rewards: "
        f"total={split.total_sol} SOL, "
        f"buyback={split.buyback_sol} SOL, "
        f"team={split.team_sol} SOL"
    )

    # Execute buyback (80%)
    result = await service.execute_swap(
        split.buyback_sol,
        settings.creator_wallet_private_key
    )

    buyback_success = result.success and result.tx_signature

    if buyback_success:
        # Record buyback
        await service.record_buyback(
            result.tx_signature,
            result.sol_spent,
            result.copper_received,
            result.price_per_token
        )
        logger.info(f"Buyback recorded: {result.tx_signature}")
    else:
        logger.error(f"Buyback failed: {result.error}")

    # Transfer 20% to team wallet
    team_tx = None
    if settings.team_wallet_public_key and settings.creator_wallet_private_key:
        team_tx = await transfer_to_team_wallet(
            amount_sol=split.team_sol,
            from_private_key=settings.creator_wallet_private_key,
            to_address=settings.team_wallet_public_key
        )
        if team_tx:
            logger.info(f"Team wallet transfer: {team_tx}")
        else:
            logger.warning("Team wallet transfer failed or skipped")
    else:
        logger.warning("Team wallet transfer skipped: missing configuration")

    # Mark rewards as processed if at least one operation succeeded
    if buyback_success or team_tx:
        reward_ids = [r.id for r in rewards]
        await service.mark_rewards_processed(reward_ids)
        logger.info(f"Marked {len(reward_ids)} rewards as processed")

    return result
