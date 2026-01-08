"""
$COPPER SQLAlchemy Models

All database models for the mining rewards system.
"""

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Optional, List

from sqlalchemy import (
    String, Integer, BigInteger, Boolean, DateTime, Numeric,
    ForeignKey, CheckConstraint, UniqueConstraint, Index, Text
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from app.database import Base


class Snapshot(Base):
    """Balance snapshot metadata."""
    __tablename__ = "snapshots"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=datetime.utcnow
    )
    total_holders: Mapped[int] = mapped_column(Integer, nullable=False)
    total_supply: Mapped[int] = mapped_column(BigInteger, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )

    # Relationships
    balances: Mapped[List["Balance"]] = relationship(
        "Balance", back_populates="snapshot", cascade="all, delete-orphan"
    )


class Balance(Base):
    """Wallet balance at a specific snapshot."""
    __tablename__ = "balances"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    snapshot_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("snapshots.id", ondelete="CASCADE")
    )
    wallet: Mapped[str] = mapped_column(String(44), nullable=False)
    balance: Mapped[int] = mapped_column(BigInteger, nullable=False)

    # Relationships
    snapshot: Mapped["Snapshot"] = relationship("Snapshot", back_populates="balances")

    __table_args__ = (
        CheckConstraint("balance >= 0", name="non_negative_balance"),
        UniqueConstraint("snapshot_id", "wallet", name="uq_balance_snapshot_wallet"),
        Index("idx_balances_wallet", "wallet"),
        Index("idx_balances_snapshot", "snapshot_id"),
        Index("idx_balances_wallet_snapshot", "wallet", "snapshot_id"),
    )


class HoldStreak(Base):
    """Wallet holding streak and tier tracking."""
    __tablename__ = "hold_streaks"

    wallet: Mapped[str] = mapped_column(String(44), primary_key=True)
    streak_start: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    current_tier: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    last_sell_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow
    )

    __table_args__ = (
        CheckConstraint(
            "current_tier >= 1 AND current_tier <= 6", name="valid_tier"
        ),
        Index("idx_hold_streaks_tier", "current_tier"),
        Index("idx_hold_streaks_updated", "updated_at"),
    )


class CreatorReward(Base):
    """Incoming Pump.fun creator rewards."""
    __tablename__ = "creator_rewards"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    amount_sol: Mapped[Decimal] = mapped_column(
        Numeric(18, 9), nullable=False
    )
    source: Mapped[str] = mapped_column(String(20), nullable=False)
    tx_signature: Mapped[Optional[str]] = mapped_column(String(88), nullable=True)
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    processed: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )

    __table_args__ = (
        CheckConstraint("amount_sol > 0", name="positive_amount"),
        CheckConstraint(
            "source IN ('pumpfun', 'pumpswap')", name="valid_source"
        ),
        Index("idx_creator_rewards_processed", "processed", postgresql_where="processed = FALSE"),
        Index("idx_creator_rewards_received", "received_at"),
    )


class Buyback(Base):
    """Jupiter swap buyback transactions."""
    __tablename__ = "buybacks"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tx_signature: Mapped[str] = mapped_column(String(88), nullable=False, unique=True)
    sol_amount: Mapped[Decimal] = mapped_column(Numeric(18, 9), nullable=False)
    copper_amount: Mapped[int] = mapped_column(BigInteger, nullable=False)
    price_per_token: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(18, 12), nullable=True
    )
    executed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )

    __table_args__ = (
        Index("idx_buybacks_executed", "executed_at"),
    )


class Distribution(Base):
    """Airdrop distribution cycles."""
    __tablename__ = "distributions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    pool_amount: Mapped[int] = mapped_column(BigInteger, nullable=False)
    pool_value_usd: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(18, 2), nullable=True
    )
    total_hashpower: Mapped[Decimal] = mapped_column(
        Numeric(24, 2), nullable=False
    )
    recipient_count: Mapped[int] = mapped_column(Integer, nullable=False)
    trigger_type: Mapped[str] = mapped_column(String(20), nullable=False)
    executed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )

    # Relationships
    recipients: Mapped[List["DistributionRecipient"]] = relationship(
        "DistributionRecipient", back_populates="distribution", cascade="all, delete-orphan"
    )

    __table_args__ = (
        CheckConstraint("pool_amount > 0", name="positive_pool"),
        CheckConstraint("total_hashpower > 0", name="positive_hashpower"),
        CheckConstraint("recipient_count > 0", name="positive_recipients"),
        CheckConstraint(
            "trigger_type IN ('threshold', 'time')", name="valid_trigger"
        ),
        Index("idx_distributions_executed", "executed_at"),
    )


class DistributionRecipient(Base):
    """Per-wallet distribution records."""
    __tablename__ = "distribution_recipients"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    distribution_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("distributions.id", ondelete="CASCADE")
    )
    wallet: Mapped[str] = mapped_column(String(44), nullable=False)
    twab: Mapped[int] = mapped_column(BigInteger, nullable=False)
    multiplier: Mapped[Decimal] = mapped_column(Numeric(4, 2), nullable=False)
    hash_power: Mapped[Decimal] = mapped_column(Numeric(24, 2), nullable=False)
    amount_received: Mapped[int] = mapped_column(BigInteger, nullable=False)
    tx_signature: Mapped[Optional[str]] = mapped_column(String(88), nullable=True)

    # Relationships
    distribution: Mapped["Distribution"] = relationship(
        "Distribution", back_populates="recipients"
    )

    __table_args__ = (
        UniqueConstraint(
            "distribution_id", "wallet", name="uq_distribution_recipient"
        ),
        Index("idx_distribution_recipients_wallet", "wallet"),
        Index("idx_distribution_recipients_dist", "distribution_id"),
    )


class ExcludedWallet(Base):
    """Wallets excluded from distributions."""
    __tablename__ = "excluded_wallets"

    wallet: Mapped[str] = mapped_column(String(44), primary_key=True)
    reason: Mapped[str] = mapped_column(String(100), nullable=False)
    added_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )


class SystemStats(Base):
    """Cached global statistics (single row)."""
    __tablename__ = "system_stats"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    total_holders: Mapped[int] = mapped_column(Integer, default=0)
    total_volume_24h: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=0)
    total_buybacks: Mapped[Decimal] = mapped_column(Numeric(18, 9), default=0)
    total_distributed: Mapped[int] = mapped_column(BigInteger, default=0)
    last_snapshot_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_distribution_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow
    )

    __table_args__ = (
        CheckConstraint("id = 1", name="single_row"),
    )


class DistributionLock(Base):
    """
    Concurrency control for distribution execution.

    Single-row table used with SELECT FOR UPDATE NOWAIT to prevent
    race conditions where multiple Celery workers could execute
    the same distribution twice.
    """
    __tablename__ = "distribution_lock"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    locked_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    locked_by: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow
    )

    __table_args__ = (
        CheckConstraint("id = 1", name="distribution_lock_single_row"),
    )
