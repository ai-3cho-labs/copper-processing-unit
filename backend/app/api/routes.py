"""
$COPPER API Routes

REST API endpoints for the mining dashboard.
"""

import re
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Optional, Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Path, Request
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.services.snapshot import SnapshotService
from app.services.streak import StreakService
from app.services.twab import TWABService
from app.services.buyback import BuybackService
from app.services.distribution import DistributionService
from app.config import TIER_CONFIG, TOKEN_MULTIPLIER
from app.utils.rate_limiter import limiter

router = APIRouter(prefix="/api", tags=["api"])


# ===========================================
# Validation
# ===========================================

# Solana wallet address: 32-44 base58 characters
WALLET_REGEX = re.compile(r'^[1-9A-HJ-NP-Za-km-z]{32,44}$')


def validate_wallet_address(wallet: str) -> str:
    """Validate Solana wallet address format."""
    if not wallet or not WALLET_REGEX.match(wallet):
        raise HTTPException(
            status_code=400,
            detail="Invalid wallet address format. Must be 32-44 base58 characters."
        )
    return wallet


# Type alias for validated wallet parameter
ValidatedWallet = Annotated[str, Path(
    min_length=32,
    max_length=44,
    pattern=r'^[1-9A-HJ-NP-Za-km-z]{32,44}$',
    description="Solana wallet address (base58)"
)]


# ===========================================
# Response Models
# ===========================================

class GlobalStatsResponse(BaseModel):
    """Global system statistics."""
    total_holders: int
    total_volume_24h: float
    total_buybacks_sol: float
    total_distributed: float
    last_snapshot_at: Optional[datetime]
    last_distribution_at: Optional[datetime]


class TierInfo(BaseModel):
    """Tier information."""
    tier: int
    name: str
    emoji: str
    multiplier: float


class UserStatsResponse(BaseModel):
    """User mining statistics."""
    wallet: str
    balance: float  # Token balance
    balance_raw: int
    twab: float  # Time-weighted average balance
    twab_raw: int
    tier: TierInfo
    multiplier: float
    hash_power: float
    streak_hours: float
    streak_start: Optional[datetime]
    next_tier: Optional[TierInfo]
    hours_to_next_tier: Optional[float]
    rank: Optional[int]
    pending_reward_estimate: float


class DistributionHistoryItem(BaseModel):
    """Distribution history item."""
    distribution_id: str
    executed_at: datetime
    twab: float
    multiplier: float
    hash_power: float
    amount_received: float
    tx_signature: Optional[str]


class LeaderboardEntry(BaseModel):
    """Leaderboard entry."""
    rank: int
    wallet: str
    wallet_short: str
    hash_power: float
    tier: TierInfo
    multiplier: float


class PoolStatusResponse(BaseModel):
    """Airdrop pool status."""
    balance: float
    balance_raw: int
    value_usd: float
    last_distribution: Optional[datetime]
    hours_since_last: Optional[float]
    hours_until_time_trigger: Optional[float]
    threshold_met: bool
    time_trigger_met: bool
    next_trigger: str  # 'threshold', 'time', or 'none'


class BuybackItem(BaseModel):
    """Buyback transaction."""
    tx_signature: str
    sol_amount: float
    copper_amount: float
    price_per_token: Optional[float]
    executed_at: datetime


class DistributionItem(BaseModel):
    """Distribution record."""
    id: str
    pool_amount: float
    pool_value_usd: Optional[float]
    total_hashpower: float
    recipient_count: int
    trigger_type: str
    executed_at: datetime


# ===========================================
# Helper Functions
# ===========================================

def utc_now() -> datetime:
    """Get current UTC time (timezone-aware)."""
    return datetime.now(timezone.utc)


def format_wallet(wallet: str) -> str:
    """Shorten wallet address for display."""
    if len(wallet) < 12:
        return wallet
    return f"{wallet[:4]}...{wallet[-4:]}"


def tier_to_info(tier: int) -> TierInfo:
    """Convert tier number to TierInfo."""
    config = TIER_CONFIG.get(tier, TIER_CONFIG[1])
    return TierInfo(
        tier=tier,
        name=config["name"],
        emoji=config["emoji"],
        multiplier=config["multiplier"]
    )


# ===========================================
# Endpoints
# ===========================================

@router.get("/stats", response_model=GlobalStatsResponse)
@limiter.limit("60/minute")
async def get_global_stats(request: Request, db: AsyncSession = Depends(get_db)):
    """Get global system statistics."""
    from app.models import SystemStats
    from sqlalchemy import select

    result = await db.execute(
        select(SystemStats).where(SystemStats.id == 1)
    )
    stats = result.scalar_one_or_none()

    if not stats:
        return GlobalStatsResponse(
            total_holders=0,
            total_volume_24h=0,
            total_buybacks_sol=0,
            total_distributed=0,
            last_snapshot_at=None,
            last_distribution_at=None
        )

    return GlobalStatsResponse(
        total_holders=stats.total_holders or 0,
        total_volume_24h=float(stats.total_volume_24h or 0),
        total_buybacks_sol=float(stats.total_buybacks or 0),
        total_distributed=float(Decimal(stats.total_distributed or 0) / TOKEN_MULTIPLIER),
        last_snapshot_at=stats.last_snapshot_at,
        last_distribution_at=stats.last_distribution_at
    )


@router.get("/user/{wallet}", response_model=UserStatsResponse)
@limiter.limit("30/minute")
async def get_user_stats(
    request: Request,
    wallet: ValidatedWallet,
    db: AsyncSession = Depends(get_db)
):
    """Get mining statistics for a specific wallet."""
    # Additional validation
    validate_wallet_address(wallet)

    streak_service = StreakService(db)
    twab_service = TWABService(db)
    distribution_service = DistributionService(db)

    # Get current period
    end = utc_now()
    start = end - timedelta(hours=24)

    # Get hash power info
    hp_info = await twab_service.calculate_hash_power(wallet, start, end)

    # Get streak info
    streak_info = await streak_service.get_streak_info(wallet)

    # Get current balance from latest snapshot
    snapshot_service = SnapshotService(db)
    latest_snapshot = await snapshot_service.get_latest_snapshot()

    balance_raw = 0
    if latest_snapshot:
        from app.models import Balance
        from sqlalchemy import select, and_

        result = await db.execute(
            select(Balance.balance).where(and_(
                Balance.snapshot_id == latest_snapshot.id,
                Balance.wallet == wallet
            ))
        )
        balance_raw = result.scalar_one_or_none() or 0

    # Get rank
    rank = await twab_service.get_wallet_rank(wallet)

    # Estimate pending reward
    pool_status = await distribution_service.get_pool_status()
    pending_estimate = 0
    if pool_status.balance > 0:
        estimate, _ = await twab_service.estimate_reward_share(
            wallet, pool_status.balance, start, end
        )
        pending_estimate = float(Decimal(estimate) / TOKEN_MULTIPLIER)

    # Build next tier info
    next_tier_info = None
    hours_to_next = None
    if streak_info and streak_info.next_tier:
        next_tier_info = tier_to_info(streak_info.next_tier)
        hours_to_next = streak_info.hours_to_next_tier

    return UserStatsResponse(
        wallet=wallet,
        balance=float(Decimal(balance_raw) / TOKEN_MULTIPLIER),
        balance_raw=balance_raw,
        twab=float(Decimal(hp_info.twab) / TOKEN_MULTIPLIER),
        twab_raw=hp_info.twab,
        tier=tier_to_info(hp_info.tier),
        multiplier=hp_info.multiplier,
        hash_power=float(hp_info.hash_power / TOKEN_MULTIPLIER),
        streak_hours=streak_info.streak_hours if streak_info else 0,
        streak_start=streak_info.streak_start if streak_info else None,
        next_tier=next_tier_info,
        hours_to_next_tier=hours_to_next,
        rank=rank,
        pending_reward_estimate=pending_estimate
    )


@router.get("/user/{wallet}/history", response_model=list[DistributionHistoryItem])
@limiter.limit("30/minute")
async def get_user_history(
    request: Request,
    wallet: ValidatedWallet,
    limit: int = Query(default=10, ge=1, le=50),
    db: AsyncSession = Depends(get_db)
):
    """Get distribution history for a wallet."""
    validate_wallet_address(wallet)

    distribution_service = DistributionService(db)
    recipients = await distribution_service.get_wallet_distributions(wallet, limit)

    return [
        DistributionHistoryItem(
            distribution_id=str(r.distribution_id),
            executed_at=r.distribution.executed_at if r.distribution else utc_now(),
            twab=float(Decimal(r.twab) / TOKEN_MULTIPLIER),
            multiplier=float(r.multiplier),
            hash_power=float(r.hash_power / TOKEN_MULTIPLIER),
            amount_received=float(Decimal(r.amount_received) / TOKEN_MULTIPLIER),
            tx_signature=r.tx_signature
        )
        for r in recipients
    ]


@router.get("/leaderboard", response_model=list[LeaderboardEntry])
@limiter.limit("20/minute")
async def get_leaderboard(
    request: Request,
    limit: int = Query(default=10, ge=1, le=100),
    db: AsyncSession = Depends(get_db)
):
    """Get top miners by hash power."""
    twab_service = TWABService(db)

    leaders = await twab_service.get_leaderboard(limit=limit)

    return [
        LeaderboardEntry(
            rank=i + 1,
            wallet=hp.wallet,
            wallet_short=format_wallet(hp.wallet),
            hash_power=float(hp.hash_power / TOKEN_MULTIPLIER),
            tier=tier_to_info(hp.tier),
            multiplier=hp.multiplier
        )
        for i, hp in enumerate(leaders)
    ]


@router.get("/pool", response_model=PoolStatusResponse)
@limiter.limit("60/minute")
async def get_pool_status(request: Request, db: AsyncSession = Depends(get_db)):
    """Get airdrop pool status."""
    from app.config import get_settings
    settings = get_settings()

    distribution_service = DistributionService(db)
    status = await distribution_service.get_pool_status()

    # Calculate hours until time trigger
    hours_until_time = None
    if status.hours_since_last is not None:
        hours_until_time = max(
            0,
            settings.distribution_max_hours - status.hours_since_last
        )

    # Determine next trigger
    if status.threshold_met:
        next_trigger = "threshold"
    elif status.time_trigger_met:
        next_trigger = "time"
    else:
        next_trigger = "none"

    return PoolStatusResponse(
        balance=status.balance_formatted,
        balance_raw=status.balance,
        value_usd=float(status.value_usd),
        last_distribution=status.last_distribution,
        hours_since_last=status.hours_since_last,
        hours_until_time_trigger=hours_until_time,
        threshold_met=status.threshold_met,
        time_trigger_met=status.time_trigger_met,
        next_trigger=next_trigger
    )


@router.get("/buybacks", response_model=list[BuybackItem])
@limiter.limit("30/minute")
async def get_buybacks(
    request: Request,
    limit: int = Query(default=10, ge=1, le=50),
    db: AsyncSession = Depends(get_db)
):
    """Get recent buyback transactions."""
    buyback_service = BuybackService(db)

    buybacks = await buyback_service.get_recent_buybacks(limit)

    return [
        BuybackItem(
            tx_signature=b.tx_signature,
            sol_amount=float(b.sol_amount),
            copper_amount=float(Decimal(b.copper_amount) / TOKEN_MULTIPLIER),
            price_per_token=float(b.price_per_token) if b.price_per_token else None,
            executed_at=b.executed_at
        )
        for b in buybacks
    ]


@router.get("/distributions", response_model=list[DistributionItem])
@limiter.limit("30/minute")
async def get_distributions(
    request: Request,
    limit: int = Query(default=10, ge=1, le=50),
    db: AsyncSession = Depends(get_db)
):
    """Get recent distributions."""
    distribution_service = DistributionService(db)

    distributions = await distribution_service.get_recent_distributions(limit)

    return [
        DistributionItem(
            id=str(d.id),
            pool_amount=float(Decimal(d.pool_amount) / TOKEN_MULTIPLIER),
            pool_value_usd=float(d.pool_value_usd) if d.pool_value_usd else None,
            total_hashpower=float(d.total_hashpower / TOKEN_MULTIPLIER),
            recipient_count=d.recipient_count,
            trigger_type=d.trigger_type,
            executed_at=d.executed_at
        )
        for d in distributions
    ]


@router.get("/tiers")
@limiter.limit("60/minute")
async def get_tiers(request: Request):
    """Get all tier configurations."""
    return [
        {
            "tier": tier,
            "name": config["name"],
            "emoji": config["emoji"],
            "multiplier": config["multiplier"],
            "min_hours": config["min_hours"]
        }
        for tier, config in TIER_CONFIG.items()
    ]
