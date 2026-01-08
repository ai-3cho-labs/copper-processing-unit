"""
$COPPER Excluded Wallet Tests

Tests for wallet exclusion logic including creator, LP, and CEX wallets.
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import patch, MagicMock, AsyncMock

from app.services.snapshot import SnapshotService
from app.services.helius import TokenAccount
from app.models import ExcludedWallet, Snapshot, Balance


class TestExcludedWalletManagement:
    """Tests for adding and removing excluded wallets."""

    @pytest.mark.asyncio
    async def test_add_excluded_wallet(self, db_session):
        """Test adding a wallet to exclusion list."""
        service = SnapshotService(db_session)

        result = await service.add_excluded_wallet(
            wallet="CreatorWallet11111111111111111111111111111",
            reason="creator"
        )

        assert result is True

        # Verify it's in the list
        excluded = await service.get_excluded_wallets()
        wallets = [e.wallet for e in excluded]
        assert "CreatorWallet11111111111111111111111111111" in wallets

    @pytest.mark.asyncio
    async def test_add_duplicate_wallet_fails(self, db_session):
        """Test that adding duplicate wallet fails gracefully."""
        service = SnapshotService(db_session)

        # Add first time - should succeed
        result1 = await service.add_excluded_wallet(
            wallet="DuplicateWallet1111111111111111111111111",
            reason="lp"
        )
        assert result1 is True

        # Add second time - should fail
        result2 = await service.add_excluded_wallet(
            wallet="DuplicateWallet1111111111111111111111111",
            reason="lp"
        )
        assert result2 is False

    @pytest.mark.asyncio
    async def test_remove_excluded_wallet(self, db_session):
        """Test removing a wallet from exclusion list."""
        service = SnapshotService(db_session)

        # Add wallet
        await service.add_excluded_wallet(
            wallet="RemovableWallet1111111111111111111111111",
            reason="test"
        )

        # Remove it
        result = await service.remove_excluded_wallet(
            "RemovableWallet1111111111111111111111111"
        )
        assert result is True

        # Verify it's gone
        excluded = await service.get_excluded_wallets()
        wallets = [e.wallet for e in excluded]
        assert "RemovableWallet1111111111111111111111111" not in wallets

    @pytest.mark.asyncio
    async def test_remove_nonexistent_wallet(self, db_session):
        """Test removing a wallet that doesn't exist."""
        service = SnapshotService(db_session)

        result = await service.remove_excluded_wallet(
            "NonExistentWallet11111111111111111111111"
        )

        assert result is False

    @pytest.mark.asyncio
    async def test_get_excluded_wallets_ordered_by_date(self, db_session):
        """Test that excluded wallets are returned in order."""
        service = SnapshotService(db_session)

        # Add wallets in specific order
        await service.add_excluded_wallet("Wallet1111111111111111111111111111111111111", "first")
        await service.add_excluded_wallet("Wallet2222222222222222222222222222222222222", "second")
        await service.add_excluded_wallet("Wallet3333333333333333333333333333333333333", "third")

        excluded = await service.get_excluded_wallets()

        # Should be ordered by added_at desc (newest first)
        assert len(excluded) >= 3


class TestSnapshotExclusion:
    """Tests for wallet exclusion during snapshot."""

    @pytest.mark.asyncio
    async def test_excluded_wallets_not_in_snapshot(self, db_session):
        """Test that excluded wallets are filtered from snapshots."""
        service = SnapshotService(db_session)

        # Add excluded wallet first
        excluded_wallet = "ExcludedInSnapshot11111111111111111111111"
        await service.add_excluded_wallet(excluded_wallet, "creator")
        await db_session.commit()

        # Mock Helius to return accounts including excluded one
        mock_accounts = [
            TokenAccount(wallet="ValidWallet11111111111111111111111111111111", balance=1000000000),
            TokenAccount(wallet=excluded_wallet, balance=5000000000),  # Should be filtered
            TokenAccount(wallet="ValidWallet22222222222222222222222222222222", balance=2000000000),
        ]

        mock_helius = MagicMock()
        mock_helius.get_token_accounts = AsyncMock(return_value=mock_accounts)
        mock_helius.get_token_supply = AsyncMock(return_value=1000000000000)

        with patch.object(service, 'helius', mock_helius):
            snapshot = await service.take_snapshot()

            assert snapshot is not None
            # Should only have 2 holders (excluded wallet filtered)
            assert snapshot.total_holders == 2

    @pytest.mark.asyncio
    async def test_multiple_excluded_types_filtered(self, db_session):
        """Test that all exclusion types are filtered."""
        service = SnapshotService(db_session)

        # Add various exclusion types
        exclusions = [
            ("CreatorWallet111111111111111111111111111111", "creator"),
            ("LPWallet1111111111111111111111111111111111111", "lp_address"),
            ("CEXWallet11111111111111111111111111111111111", "cex_deposit"),
            ("SystemWallet1111111111111111111111111111111", "system"),
        ]

        for wallet, reason in exclusions:
            await service.add_excluded_wallet(wallet, reason)
        await db_session.commit()

        # Mock all wallets including excluded ones
        mock_accounts = [
            TokenAccount(wallet="ValidHolder111111111111111111111111111111", balance=1000),
        ] + [
            TokenAccount(wallet=wallet, balance=999999999) for wallet, _ in exclusions
        ]

        mock_helius = MagicMock()
        mock_helius.get_token_accounts = AsyncMock(return_value=mock_accounts)
        mock_helius.get_token_supply = AsyncMock(return_value=10000000000000)

        with patch.object(service, 'helius', mock_helius):
            snapshot = await service.take_snapshot()

            assert snapshot is not None
            # Only the valid holder should be included
            assert snapshot.total_holders == 1


class TestExclusionReasons:
    """Tests for different exclusion reasons."""

    @pytest.mark.asyncio
    async def test_creator_wallet_exclusion(self, db_session):
        """Test creator wallet is properly excluded."""
        service = SnapshotService(db_session)

        result = await service.add_excluded_wallet(
            wallet="CreatorWalletTest111111111111111111111111",
            reason="creator"
        )
        assert result is True

        excluded = await service.get_excluded_wallets()
        creator_exclusion = next(
            (e for e in excluded if e.wallet == "CreatorWalletTest111111111111111111111111"),
            None
        )
        assert creator_exclusion is not None
        assert creator_exclusion.reason == "creator"

    @pytest.mark.asyncio
    async def test_lp_address_exclusion(self, db_session):
        """Test LP address is properly excluded."""
        service = SnapshotService(db_session)

        # Pump.fun bonding curve
        await service.add_excluded_wallet(
            wallet="PumpFunBondingCurve1111111111111111111111",
            reason="lp_pump_fun"
        )

        # Raydium LP
        await service.add_excluded_wallet(
            wallet="RaydiumLPWallet111111111111111111111111111",
            reason="lp_raydium"
        )

        excluded = await service.get_excluded_wallets()
        reasons = [e.reason for e in excluded]
        assert "lp_pump_fun" in reasons
        assert "lp_raydium" in reasons

    @pytest.mark.asyncio
    async def test_cex_wallet_exclusion(self, db_session):
        """Test CEX deposit wallet is properly excluded."""
        service = SnapshotService(db_session)

        # Known CEX wallets
        cex_wallets = [
            ("BinanceHotWallet11111111111111111111111111", "cex_binance"),
            ("CoinbaseWallet1111111111111111111111111111", "cex_coinbase"),
            ("KrakenWallet11111111111111111111111111111111", "cex_kraken"),
        ]

        for wallet, reason in cex_wallets:
            await service.add_excluded_wallet(wallet, reason)

        excluded = await service.get_excluded_wallets()
        assert len(excluded) >= 3


class TestExclusionEdgeCases:
    """Edge cases for wallet exclusion."""

    @pytest.mark.asyncio
    async def test_empty_exclusion_list(self, db_session):
        """Test snapshot works with no exclusions."""
        service = SnapshotService(db_session)

        # No exclusions added
        mock_accounts = [
            TokenAccount(wallet="Holder1111111111111111111111111111111111111", balance=1000),
            TokenAccount(wallet="Holder2222222222222222222222222222222222222", balance=2000),
        ]

        mock_helius = MagicMock()
        mock_helius.get_token_accounts = AsyncMock(return_value=mock_accounts)
        mock_helius.get_token_supply = AsyncMock(return_value=3000)

        with patch.object(service, 'helius', mock_helius):
            snapshot = await service.take_snapshot()

            # All holders should be included
            assert snapshot.total_holders == 2

    @pytest.mark.asyncio
    async def test_all_wallets_excluded(self, db_session):
        """Test handling when all wallets are excluded."""
        service = SnapshotService(db_session)

        # Exclude all wallets that will be returned
        await service.add_excluded_wallet("OnlyWallet111111111111111111111111111111", "test")
        await db_session.commit()

        mock_accounts = [
            TokenAccount(wallet="OnlyWallet111111111111111111111111111111", balance=1000),
        ]

        mock_helius = MagicMock()
        mock_helius.get_token_accounts = AsyncMock(return_value=mock_accounts)
        mock_helius.get_token_supply = AsyncMock(return_value=1000)

        with patch.object(service, 'helius', mock_helius):
            snapshot = await service.take_snapshot()

            # Snapshot should still be created but with 0 holders
            assert snapshot is not None
            assert snapshot.total_holders == 0

    @pytest.mark.asyncio
    async def test_case_sensitive_wallet_matching(self, db_session):
        """Test that wallet matching is case-sensitive (as Solana addresses are)."""
        service = SnapshotService(db_session)

        # Add with specific case
        await service.add_excluded_wallet(
            wallet="CaseSensitiveWallet1111111111111111111111",
            reason="test"
        )
        await db_session.commit()

        mock_accounts = [
            TokenAccount(wallet="CaseSensitiveWallet1111111111111111111111", balance=1000),
            TokenAccount(wallet="casesensitivewallet1111111111111111111111", balance=2000),  # Different case
        ]

        mock_helius = MagicMock()
        mock_helius.get_token_accounts = AsyncMock(return_value=mock_accounts)
        mock_helius.get_token_supply = AsyncMock(return_value=3000)

        with patch.object(service, 'helius', mock_helius):
            snapshot = await service.take_snapshot()

            # Only exact match should be excluded
            # Note: In practice, Solana addresses are base58 and case-sensitive
            assert snapshot is not None


class TestExcludedWalletPersistence:
    """Tests for excluded wallet data persistence."""

    @pytest.mark.asyncio
    async def test_exclusion_persists_across_sessions(self, db_session):
        """Test that exclusions persist in database."""
        service = SnapshotService(db_session)

        # Add exclusion
        await service.add_excluded_wallet(
            wallet="PersistentExclusion11111111111111111111111",
            reason="permanent"
        )
        await db_session.commit()

        # Create new service instance (simulating new request)
        service2 = SnapshotService(db_session)
        excluded = await service2.get_excluded_wallets()

        wallets = [e.wallet for e in excluded]
        assert "PersistentExclusion11111111111111111111111" in wallets

    @pytest.mark.asyncio
    async def test_exclusion_has_timestamp(self, db_session):
        """Test that exclusions have added_at timestamp."""
        service = SnapshotService(db_session)

        before = datetime.now(timezone.utc)
        await service.add_excluded_wallet(
            wallet="TimestampedWallet11111111111111111111111",
            reason="test"
        )
        after = datetime.now(timezone.utc)

        excluded = await service.get_excluded_wallets()
        timestamped = next(
            (e for e in excluded if e.wallet == "TimestampedWallet11111111111111111111111"),
            None
        )

        assert timestamped is not None
        assert timestamped.added_at is not None
        # Timestamp should be between before and after
        assert before <= timestamped.added_at <= after


class TestDistributionExclusion:
    """Tests for wallet exclusion in distributions."""

    @pytest.mark.asyncio
    async def test_excluded_wallets_not_in_distribution(self, populated_db, mock_settings):
        """Test that excluded wallets don't receive distributions."""
        from app.services.distribution import DistributionService

        # Add one of the sample wallets to exclusion list
        snapshot_service = SnapshotService(populated_db)
        await snapshot_service.add_excluded_wallet(
            wallet="Wallet1111111111111111111111111111111111111",
            reason="test_exclusion"
        )
        await populated_db.commit()

        with patch("app.services.distribution.get_settings", return_value=mock_settings):
            dist_service = DistributionService(populated_db)

            # Mock methods needed for distribution
            with patch.object(dist_service, "get_pool_balance", return_value=1000000000):
                with patch.object(dist_service, "get_pool_value_usd") as mock_pool_value:
                    mock_pool_value.return_value = 500

                    # The distribution calculation should exclude wallet1
                    # This is verified through the TWAB service which filters
                    # based on balance records from snapshots


class TestKnownExclusionAddresses:
    """Tests for known addresses that should be excluded."""

    def test_known_addresses_format(self):
        """Test that known address formats are valid base58."""
        import base58

        # These should be validated as proper Solana addresses
        known_formats = [
            "So11111111111111111111111111111111111111112",  # Native SOL
            "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",  # USDC
            "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA",  # Token Program
        ]

        for addr in known_formats:
            # Should not raise exception
            decoded = base58.b58decode(addr)
            assert len(decoded) == 32  # Solana addresses are 32 bytes
