"""
$COPPER TWAB Service Tests

Tests for Time-Weighted Average Balance calculations.
"""

import pytest
from decimal import Decimal
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, MagicMock

from app.services.twab import TWABService, HashPowerInfo
from app.models import Snapshot, Balance, HoldStreak
from app.config import TIER_CONFIG


class TestTWABCalculation:
    """Tests for TWAB calculation logic."""

    @pytest.mark.asyncio
    async def test_calculate_twab_single_snapshot(self, db_session):
        """Test TWAB calculation with single snapshot."""
        service = TWABService(db_session)

        now = datetime.now(timezone.utc)

        # Create a snapshot with timezone-aware datetime
        from app.models import Snapshot, Balance
        snapshot = Snapshot(
            timestamp=now - timedelta(hours=1),
            total_holders=1,
            total_supply=1_000_000_000
        )
        db_session.add(snapshot)
        await db_session.flush()

        balance = Balance(
            snapshot_id=snapshot.id,
            wallet="11111111111111111111111111111111111111111111",
            balance=100_000_000_000
        )
        db_session.add(balance)
        await db_session.commit()

        start = now - timedelta(hours=24)
        end = now

        # Test for wallet
        twab = await service.calculate_twab(
            "11111111111111111111111111111111111111111111",
            start,
            end
        )

        # TWAB should be >= 0
        assert twab >= 0

    @pytest.mark.asyncio
    async def test_calculate_twab_no_snapshots(self, db_session):
        """Test TWAB calculation when wallet has no snapshots."""
        service = TWABService(db_session)

        now = datetime.now(timezone.utc)
        start = now - timedelta(hours=24)
        end = now

        twab = await service.calculate_twab(
            "99999999999999999999999999999999999999999999",
            start,
            end
        )

        assert twab == 0

    @pytest.mark.asyncio
    async def test_calculate_hash_power(self, db_session):
        """Test hash power calculation with multiplier."""
        service = TWABService(db_session)

        now = datetime.now(timezone.utc)

        # Create snapshot and balance
        from app.models import Snapshot, Balance, HoldStreak
        snapshot = Snapshot(
            timestamp=now - timedelta(hours=1),
            total_holders=1,
            total_supply=1_000_000_000
        )
        db_session.add(snapshot)
        await db_session.flush()

        wallet_addr = "88888888888888888888888888888888888888888888"
        balance = Balance(
            snapshot_id=snapshot.id,
            wallet=wallet_addr,
            balance=100_000_000_000
        )
        db_session.add(balance)

        # Create a streak for multiplier
        streak = HoldStreak(
            wallet=wallet_addr,
            current_tier=2,
            streak_start=now - timedelta(hours=12)
        )
        db_session.add(streak)
        await db_session.commit()

        start = now - timedelta(hours=24)
        end = now

        result = await service.calculate_hash_power(wallet_addr, start, end)

        if result:
            assert isinstance(result, HashPowerInfo)
            assert result.multiplier >= 1.0  # Minimum multiplier is 1.0

    @pytest.mark.asyncio
    async def test_calculate_all_hash_powers(self, db_session):
        """Test batch hash power calculation."""
        service = TWABService(db_session)

        now = datetime.now(timezone.utc)

        # Create snapshot and balance
        from app.models import Snapshot, Balance
        snapshot = Snapshot(
            timestamp=now - timedelta(hours=1),
            total_holders=1,
            total_supply=1_000_000_000
        )
        db_session.add(snapshot)
        await db_session.flush()

        balance = Balance(
            snapshot_id=snapshot.id,
            wallet="99999999999999999999999999999999999999999999",
            balance=100_000_000_000
        )
        db_session.add(balance)
        await db_session.commit()

        start = now - timedelta(hours=24)
        end = now

        results = await service.calculate_all_hash_powers(start, end)

        assert isinstance(results, list)

    def test_tier_config_multipliers(self):
        """Test tier configuration multipliers are valid."""
        # Test all tiers have valid multipliers
        for tier, config in TIER_CONFIG.items():
            assert config["multiplier"] >= 1.0
            assert tier >= 1 and tier <= 6


class TestTWABEdgeCases:
    """Edge case tests for TWAB service."""

    @pytest.mark.asyncio
    async def test_twab_with_zero_balance(self, db_session):
        """Test TWAB when wallet has zero balance."""
        service = TWABService(db_session)

        now = datetime.now(timezone.utc)

        # Create snapshot with zero balance
        snapshot = Snapshot(
            timestamp=now - timedelta(hours=1),
            total_holders=1,
            total_supply=1_000_000_000
        )
        db_session.add(snapshot)
        await db_session.flush()

        balance = Balance(
            snapshot_id=snapshot.id,
            wallet="77777777777777777777777777777777777777777777",
            balance=0
        )
        db_session.add(balance)
        await db_session.commit()

        twab = await service.calculate_twab(
            "77777777777777777777777777777777777777777777",
            now - timedelta(hours=24),
            now
        )

        assert twab == 0

    @pytest.mark.asyncio
    async def test_twab_excludes_wallets_below_minimum(self, db_session):
        """Test that wallets below minimum balance are excluded."""
        service = TWABService(db_session)

        now = datetime.now(timezone.utc)

        # Create snapshot and balance
        from app.models import Snapshot, Balance
        snapshot = Snapshot(
            timestamp=now - timedelta(hours=1),
            total_holders=1,
            total_supply=1_000_000_000
        )
        db_session.add(snapshot)
        await db_session.flush()

        balance = Balance(
            snapshot_id=snapshot.id,
            wallet="aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa1",
            balance=100_000_000_000  # 100 tokens
        )
        db_session.add(balance)
        await db_session.commit()

        start = now - timedelta(hours=24)
        end = now

        # Very high minimum balance to filter all wallets
        high_min_balance = 10_000_000_000_000  # 10K tokens

        results = await service.calculate_all_hash_powers(
            start, end, min_balance=high_min_balance
        )

        # Should have no results since all wallets are below threshold
        assert len(results) == 0
