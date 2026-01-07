"""
$COPPER Distribution Service

Handles airdrop distribution to holders based on Hash Power.
Triggers: Pool reaches $250 USD OR 24 hours since last distribution.
"""

import logging
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Optional
from dataclasses import dataclass

from sqlalchemy import select, func, insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    Distribution, DistributionRecipient, SystemStats, ExcludedWallet
)
from app.services.twab import TWABService, HashPowerInfo
from app.services.helius import get_helius_service
from app.utils.http_client import get_http_client
from app.config import get_settings, COPPER_DECIMALS, TOKEN_MULTIPLIER

logger = logging.getLogger(__name__)
settings = get_settings()

# Price API (Jupiter for COPPER/USD via SOL)
JUPITER_PRICE_API = "https://price.jup.ag/v4/price"


def utc_now() -> datetime:
    """Get current UTC time (timezone-aware)."""
    return datetime.now(timezone.utc)


@dataclass
class DistributionPlan:
    """Planned distribution before execution."""
    pool_amount: int  # Raw token amount
    pool_value_usd: Decimal
    total_hashpower: Decimal
    recipient_count: int
    trigger_type: str  # 'threshold' or 'time'
    recipients: list["RecipientShare"]


@dataclass
class RecipientShare:
    """Individual recipient's share in a distribution."""
    wallet: str
    twab: int
    multiplier: float
    hash_power: Decimal
    share_percentage: Decimal
    amount: int  # Raw token amount


@dataclass
class PoolStatus:
    """Current pool status."""
    balance: int  # Raw token amount
    balance_formatted: float  # Human readable
    value_usd: Decimal
    last_distribution: Optional[datetime]
    hours_since_last: Optional[float]
    threshold_met: bool
    time_trigger_met: bool
    should_distribute: bool


class DistributionService:
    """Service for managing token distributions."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.twab_service = TWABService(db)
        self.helius = get_helius_service()

    @property
    def client(self):
        """Get shared HTTP client."""
        return get_http_client()

    async def get_pool_balance(self) -> int:
        """
        Get current airdrop pool balance.

        Returns:
            Raw token balance of airdrop pool wallet.
        """
        # Fetch from Helius
        try:
            accounts = await self.helius.get_token_accounts()
            # Find airdrop pool wallet
            pool_wallet = settings.team_wallet_public_key  # Using single wallet

            for account in accounts:
                if account.wallet == pool_wallet:
                    return account.balance

            return 0

        except Exception as e:
            logger.error(f"Error fetching pool balance: {e}")
            return 0

    async def get_copper_price_usd(self) -> Decimal:
        """
        Get current COPPER price in USD.

        Uses Jupiter price API via SOL price.

        Returns:
            Price per token in USD.
        """
        if not settings.copper_token_mint:
            return Decimal(0)

        try:
            response = await self.client.get(
                JUPITER_PRICE_API,
                params={"ids": settings.copper_token_mint}
            )
            response.raise_for_status()
            data = response.json()

            price_data = data.get("data", {}).get(settings.copper_token_mint, {})
            price = price_data.get("price", 0)

            return Decimal(str(price))

        except Exception as e:
            logger.error(f"Error fetching COPPER price: {e}")
            return Decimal(0)

    async def get_pool_value_usd(self) -> Decimal:
        """
        Get current pool value in USD.

        Returns:
            Pool value in USD.
        """
        balance = await self.get_pool_balance()
        price = await self.get_copper_price_usd()

        # Convert raw balance to token amount
        tokens = Decimal(balance) / TOKEN_MULTIPLIER
        return tokens * price

    async def get_last_distribution(self) -> Optional[Distribution]:
        """
        Get the most recent distribution.

        Returns:
            Last Distribution record, or None.
        """
        result = await self.db.execute(
            select(Distribution)
            .order_by(Distribution.executed_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def get_pool_status(self) -> PoolStatus:
        """
        Get complete pool status including trigger checks.

        Returns:
            PoolStatus with all relevant info.
        """
        balance = await self.get_pool_balance()
        value_usd = await self.get_pool_value_usd()
        last_dist = await self.get_last_distribution()

        # Calculate time since last distribution
        hours_since = None
        if last_dist:
            delta = utc_now() - last_dist.executed_at
            hours_since = delta.total_seconds() / 3600

        # Check triggers
        threshold_met = value_usd >= settings.distribution_threshold_usd
        time_trigger_met = (
            hours_since is None or
            hours_since >= settings.distribution_max_hours
        )

        return PoolStatus(
            balance=balance,
            balance_formatted=float(Decimal(balance) / TOKEN_MULTIPLIER),
            value_usd=value_usd,
            last_distribution=last_dist.executed_at if last_dist else None,
            hours_since_last=hours_since,
            threshold_met=threshold_met,
            time_trigger_met=time_trigger_met,
            should_distribute=threshold_met or time_trigger_met
        )

    async def should_distribute(self) -> tuple[bool, str]:
        """
        Check if distribution should be triggered.

        Returns:
            Tuple of (should_distribute, trigger_type).
        """
        status = await self.get_pool_status()

        if status.threshold_met:
            return True, "threshold"
        if status.time_trigger_met:
            return True, "time"

        return False, ""

    async def calculate_distribution(
        self,
        pool_amount: Optional[int] = None
    ) -> Optional[DistributionPlan]:
        """
        Calculate distribution shares for all eligible wallets.

        Args:
            pool_amount: Override pool amount (for testing).

        Returns:
            DistributionPlan with all recipient shares.
        """
        # Get pool info
        if pool_amount is None:
            pool_amount = await self.get_pool_balance()

        if pool_amount <= 0:
            logger.warning("Pool is empty, cannot distribute")
            return None

        pool_value_usd = await self.get_pool_value_usd()

        # Determine trigger type
        should, trigger_type = await self.should_distribute()
        if not should:
            trigger_type = "manual"  # Allow manual distributions

        # Calculate period (since last distribution or 24h)
        last_dist = await self.get_last_distribution()
        end = utc_now()

        if last_dist:
            start = last_dist.executed_at
        else:
            start = end - timedelta(hours=24)

        # Get minimum balance threshold (convert USD to tokens)
        price = await self.get_copper_price_usd()
        min_balance_tokens = 0
        if price > 0:
            min_balance_tokens = int(
                (Decimal(settings.min_balance_usd) / price) * TOKEN_MULTIPLIER
            )

        # Calculate hash powers for all wallets
        hash_powers = await self.twab_service.calculate_all_hash_powers(
            start, end, min_balance=min_balance_tokens
        )

        if not hash_powers:
            logger.warning("No eligible wallets for distribution")
            return None

        # Calculate total hash power
        total_hp = sum(hp.hash_power for hp in hash_powers)
        if total_hp == 0:
            return None

        # Calculate shares
        recipients = []
        for hp in hash_powers:
            share_pct = hp.hash_power / total_hp
            amount = int(Decimal(pool_amount) * share_pct)

            if amount > 0:
                recipients.append(RecipientShare(
                    wallet=hp.wallet,
                    twab=hp.twab,
                    multiplier=hp.multiplier,
                    hash_power=hp.hash_power,
                    share_percentage=share_pct * 100,
                    amount=amount
                ))

        return DistributionPlan(
            pool_amount=pool_amount,
            pool_value_usd=pool_value_usd,
            total_hashpower=total_hp,
            recipient_count=len(recipients),
            trigger_type=trigger_type,
            recipients=recipients
        )

    async def execute_distribution(
        self,
        plan: DistributionPlan
    ) -> Optional[Distribution]:
        """
        Execute a distribution plan (send tokens to recipients).

        Args:
            plan: DistributionPlan to execute.

        Returns:
            Distribution record if successful.
        """
        try:
            # Create distribution record
            distribution = Distribution(
                pool_amount=plan.pool_amount,
                pool_value_usd=plan.pool_value_usd,
                total_hashpower=plan.total_hashpower,
                recipient_count=plan.recipient_count,
                trigger_type=plan.trigger_type,
                executed_at=utc_now()
            )
            self.db.add(distribution)
            await self.db.flush()

            # BULK INSERT: Create all recipient records at once
            if plan.recipients:
                recipient_data = [
                    {
                        "distribution_id": distribution.id,
                        "wallet": r.wallet,
                        "twab": r.twab,
                        "multiplier": Decimal(str(r.multiplier)),
                        "hash_power": r.hash_power,
                        "amount_received": r.amount,
                        "tx_signature": None  # Set after actual transfer
                    }
                    for r in plan.recipients
                ]
                await self.db.execute(insert(DistributionRecipient), recipient_data)

            # Update system stats
            await self._update_system_stats(distribution)

            await self.db.commit()

            logger.info(
                f"Distribution executed: id={distribution.id}, "
                f"recipients={plan.recipient_count}, "
                f"pool={plan.pool_amount}"
            )

            # TODO: Execute actual token transfers
            # This would use ZK compression for efficient batch transfers
            # For now, distribution is recorded but transfers are manual

            return distribution

        except Exception as e:
            logger.error(f"Error executing distribution: {e}")
            await self.db.rollback()
            return None

    async def get_recent_distributions(
        self,
        limit: int = 10
    ) -> list[Distribution]:
        """
        Get recent distributions.

        Args:
            limit: Maximum number to return.

        Returns:
            List of recent Distribution records.
        """
        result = await self.db.execute(
            select(Distribution)
            .order_by(Distribution.executed_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_wallet_distributions(
        self,
        wallet: str,
        limit: int = 10
    ) -> list[DistributionRecipient]:
        """
        Get distribution history for a wallet.

        Args:
            wallet: Wallet address.
            limit: Maximum number to return.

        Returns:
            List of DistributionRecipient records.
        """
        result = await self.db.execute(
            select(DistributionRecipient)
            .where(DistributionRecipient.wallet == wallet)
            .order_by(DistributionRecipient.id.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_total_distributed(self) -> int:
        """
        Get total tokens distributed.

        Returns:
            Total raw token amount distributed.
        """
        result = await self.db.execute(
            select(func.sum(Distribution.pool_amount))
        )
        total = result.scalar_one_or_none()
        return int(total) if total else 0

    async def get_distribution_stats(self) -> dict:
        """
        Get distribution statistics.

        Returns:
            Dict with distribution stats.
        """
        result = await self.db.execute(
            select(
                func.count(Distribution.id),
                func.sum(Distribution.pool_amount),
                func.sum(Distribution.recipient_count)
            )
        )
        row = result.one()

        return {
            "total_distributions": row[0] or 0,
            "total_distributed": row[1] or 0,
            "total_recipients": row[2] or 0
        }

    async def _update_system_stats(self, distribution: Distribution):
        """Update system stats with distribution info."""
        result = await self.db.execute(
            select(SystemStats).where(SystemStats.id == 1)
        )
        stats = result.scalar_one_or_none()

        if stats:
            stats.total_distributed = (
                (stats.total_distributed or 0) + distribution.pool_amount
            )
            stats.last_distribution_at = distribution.executed_at
            stats.updated_at = utc_now()


async def check_and_distribute(db: AsyncSession) -> Optional[Distribution]:
    """
    Check triggers and execute distribution if needed.

    Main entry point for the distribution task.

    Args:
        db: Database session.

    Returns:
        Distribution record if executed, None otherwise.
    """
    service = DistributionService(db)

    should, trigger = await service.should_distribute()

    if not should:
        logger.info("Distribution not triggered")
        return None

    logger.info(f"Distribution triggered by: {trigger}")

    plan = await service.calculate_distribution()
    if not plan:
        logger.warning("Could not create distribution plan")
        return None

    return await service.execute_distribution(plan)
