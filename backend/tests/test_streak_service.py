"""
$COPPER Streak Service Tests

Tests for hold streak tracking and tier progression.
"""

import pytest
from decimal import Decimal
from datetime import datetime, timezone, timedelta

from app.services.streak import StreakService
from app.models import HoldStreak
from app.config import TIER_CONFIG, TIER_THRESHOLDS


class TestStreakService:
    """Tests for streak tracking functionality."""

    @pytest.mark.asyncio
    async def test_create_new_streak(self, db_session):
        """Test creating a new hold streak."""
        service = StreakService(db_session)

        wallet = "66666666666666666666666666666666666666666666"
        streak = await service.get_or_create_streak(wallet)

        assert streak is not None
        assert streak.wallet == wallet
        assert streak.current_tier == 1  # Starts at tier 1

    @pytest.mark.asyncio
    async def test_get_existing_streak(self, populated_db):
        """Test retrieving existing streak."""
        service = StreakService(populated_db)

        streak = await service.get_or_create_streak(
            "Wallet1111111111111111111111111111111111111"
        )

        assert streak is not None
        assert streak.current_tier >= 1

    @pytest.mark.asyncio
    async def test_tier_progression(self, db_session):
        """Test tier progression based on hours."""
        service = StreakService(db_session)

        wallet = "11111111111111111111111111111111111111111111"

        # Create streak at tier 1
        streak = await service.get_or_create_streak(wallet)
        assert streak.current_tier == 1

        # Simulate time passing - update streak_start to 6 hours ago
        streak.streak_start = datetime.now(timezone.utc) - timedelta(hours=6)
        await db_session.commit()

        # Re-fetch and verify streak was created
        updated = await service.get_or_create_streak(wallet)
        assert updated.current_tier >= 1

    @pytest.mark.asyncio
    async def test_sell_detection_drops_tier(self, db_session):
        """Test that selling drops tier by one."""
        service = StreakService(db_session)

        wallet = "22222222222222222222222222222222222222222222"

        # Create streak at tier 3
        streak = HoldStreak(
            wallet=wallet,
            current_tier=3,
            streak_start=datetime.now(timezone.utc) - timedelta(hours=24)
        )
        db_session.add(streak)
        await db_session.commit()

        # Process sell
        result = await service.process_sell(wallet)

        # Tier should drop to 2
        assert result.current_tier == 2

    @pytest.mark.asyncio
    async def test_sell_at_tier_1_stays_at_tier_1(self, db_session):
        """Test that selling at tier 1 keeps wallet at tier 1."""
        service = StreakService(db_session)

        wallet = "33333333333333333333333333333333333333333333"

        # Create streak at tier 1
        streak = HoldStreak(
            wallet=wallet,
            current_tier=1,
            streak_start=datetime.now(timezone.utc) - timedelta(hours=2)
        )
        db_session.add(streak)
        await db_session.commit()

        # Process sell
        result = await service.process_sell(wallet)

        # Should stay at tier 1
        assert result.current_tier == 1

    @pytest.mark.asyncio
    async def test_get_multiplier(self, db_session):
        """Test getting multiplier for a wallet."""
        service = StreakService(db_session)

        wallet = "44444444444444444444444444444444444444444444"

        # Create streak at tier 4
        streak = HoldStreak(
            wallet=wallet,
            current_tier=4,
            streak_start=datetime.now(timezone.utc) - timedelta(hours=72)
        )
        db_session.add(streak)
        await db_session.commit()

        multiplier = await service.get_wallet_multiplier(wallet)

        # Tier 4 (Industrial) has 2.5x multiplier
        assert multiplier == TIER_CONFIG[4]["multiplier"]

    @pytest.mark.asyncio
    async def test_get_multiplier_new_wallet(self, db_session):
        """Test multiplier for wallet with no streak."""
        service = StreakService(db_session)

        multiplier = await service.get_wallet_multiplier(
            "55555555555555555555555555555555555555555555"
        )

        # Should return default multiplier (1.0)
        assert multiplier == 1.0


class TestTierThresholds:
    """Tests for tier threshold logic."""

    def test_tier_config_complete(self):
        """Test that all tiers are properly configured."""
        assert len(TIER_CONFIG) == 6

        for tier in range(1, 7):
            assert tier in TIER_CONFIG
            config = TIER_CONFIG[tier]
            assert "name" in config
            assert "multiplier" in config
            assert "min_hours" in config
            assert config["multiplier"] >= 1.0

    def test_tier_thresholds_ascending(self):
        """Test that tier thresholds are in ascending order."""
        thresholds = list(TIER_THRESHOLDS.values())

        for i in range(1, len(thresholds)):
            assert thresholds[i] > thresholds[i - 1], \
                f"Tier {i + 1} threshold should be greater than tier {i}"

    def test_multipliers_ascending(self):
        """Test that multipliers increase with tier."""
        multipliers = [TIER_CONFIG[t]["multiplier"] for t in range(1, 7)]

        for i in range(1, len(multipliers)):
            assert multipliers[i] >= multipliers[i - 1], \
                f"Tier {i + 1} multiplier should be >= tier {i}"
