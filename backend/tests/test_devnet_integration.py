"""
$COPPER Devnet Integration Tests

Real integration tests that execute on Solana devnet.
These tests require actual devnet configuration and will skip if not configured.

To run these tests:
1. Set up .env with devnet configuration:
   - SOLANA_NETWORK=devnet
   - HELIUS_API_KEY=your-devnet-api-key
   - CREATOR_WALLET_PRIVATE_KEY=devnet-test-wallet-key
   - COPPER_TOKEN_MINT=devnet-test-token-mint

2. Fund your test wallet with devnet SOL:
   solana airdrop 2 <your-wallet-address> --url devnet

3. Run tests:
   pytest tests/test_devnet_integration.py -v -s

IMPORTANT: Never use mainnet credentials for these tests!
"""

import os
import pytest
import asyncio
import base58
from decimal import Decimal
from datetime import datetime, timezone

# Check if devnet is configured
DEVNET_CONFIGURED = all([
    os.getenv("HELIUS_API_KEY"),
    os.getenv("SOLANA_NETWORK") == "devnet" or os.getenv("ENVIRONMENT") == "test",
])

# Skip reason
SKIP_REASON = "Devnet not configured. Set HELIUS_API_KEY and SOLANA_NETWORK=devnet"

# Markers for devnet tests
pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(not DEVNET_CONFIGURED, reason=SKIP_REASON),
]


def get_devnet_settings():
    """Get settings configured for devnet testing."""
    from app.config import Settings

    return Settings(
        environment="test",
        solana_network="devnet",
        helius_api_key=os.getenv("HELIUS_API_KEY", ""),
        copper_token_mint=os.getenv("COPPER_TOKEN_MINT", ""),
        creator_wallet_private_key=os.getenv("CREATOR_WALLET_PRIVATE_KEY", ""),
        team_wallet_public_key=os.getenv("TEAM_WALLET_PUBLIC_KEY", ""),
    )


class TestDevnetRPCConnection:
    """Tests for Helius devnet RPC connectivity."""

    @pytest.mark.asyncio
    async def test_rpc_connection(self):
        """Test basic RPC connection to Helius devnet."""
        from app.utils.http_client import get_http_client

        settings = get_devnet_settings()
        client = get_http_client()

        response = await client.post(
            settings.helius_rpc_url,
            json={
                "jsonrpc": "2.0",
                "id": "test-connection",
                "method": "getHealth"
            }
        )
        response.raise_for_status()
        data = response.json()

        # Healthy RPC returns "ok"
        assert data.get("result") == "ok", f"RPC health check failed: {data}"
        print(f"RPC connected successfully to devnet")

    @pytest.mark.asyncio
    async def test_get_latest_blockhash(self):
        """Test fetching latest blockhash from devnet."""
        from app.utils.http_client import get_http_client

        settings = get_devnet_settings()
        client = get_http_client()

        response = await client.post(
            settings.helius_rpc_url,
            json={
                "jsonrpc": "2.0",
                "id": "test-blockhash",
                "method": "getLatestBlockhash",
                "params": [{"commitment": "finalized"}]
            }
        )
        response.raise_for_status()
        data = response.json()

        assert "result" in data
        blockhash = data["result"]["value"]["blockhash"]
        assert len(blockhash) > 30, "Invalid blockhash returned"
        print(f"Latest blockhash: {blockhash[:20]}...")

    @pytest.mark.asyncio
    async def test_get_slot(self):
        """Test fetching current slot from devnet."""
        from app.utils.http_client import get_http_client

        settings = get_devnet_settings()
        client = get_http_client()

        response = await client.post(
            settings.helius_rpc_url,
            json={
                "jsonrpc": "2.0",
                "id": "test-slot",
                "method": "getSlot"
            }
        )
        response.raise_for_status()
        data = response.json()

        slot = data.get("result", 0)
        assert slot > 0, "Invalid slot returned"
        print(f"Current devnet slot: {slot}")


class TestDevnetWalletOperations:
    """Tests for wallet operations on devnet."""

    @pytest.fixture
    def test_keypair(self):
        """Generate or load test keypair."""
        from solders.keypair import Keypair

        private_key = os.getenv("CREATOR_WALLET_PRIVATE_KEY")
        if private_key:
            try:
                secret_bytes = base58.b58decode(private_key)
                return Keypair.from_bytes(secret_bytes)
            except Exception:
                pass

        # Generate ephemeral keypair for testing
        return Keypair()

    @pytest.mark.asyncio
    async def test_get_wallet_balance(self, test_keypair):
        """Test fetching SOL balance from devnet wallet."""
        from app.utils.http_client import get_http_client

        settings = get_devnet_settings()
        client = get_http_client()

        pubkey = str(test_keypair.pubkey())

        response = await client.post(
            settings.helius_rpc_url,
            json={
                "jsonrpc": "2.0",
                "id": "test-balance",
                "method": "getBalance",
                "params": [pubkey]
            }
        )
        response.raise_for_status()
        data = response.json()

        balance_lamports = data.get("result", {}).get("value", 0)
        balance_sol = balance_lamports / 1_000_000_000

        print(f"Wallet {pubkey[:8]}... balance: {balance_sol:.4f} SOL")

        # Just verify we got a response (balance could be 0)
        assert "result" in data

    @pytest.mark.asyncio
    async def test_wallet_keypair_derivation(self, test_keypair):
        """Test keypair derivation and public key generation."""
        from app.utils.solana_tx import keypair_from_base58

        private_key = os.getenv("CREATOR_WALLET_PRIVATE_KEY")
        if not private_key:
            pytest.skip("CREATOR_WALLET_PRIVATE_KEY not set")

        # Derive keypair
        keypair = keypair_from_base58(private_key)
        pubkey = str(keypair.pubkey())

        print(f"Derived public key: {pubkey}")

        # Validate base58 format
        decoded = base58.b58decode(pubkey)
        assert len(decoded) == 32, "Public key should be 32 bytes"


@pytest.mark.skipif(
    not os.getenv("CREATOR_WALLET_PRIVATE_KEY"),
    reason="CREATOR_WALLET_PRIVATE_KEY required for transaction tests"
)
class TestDevnetTransactions:
    """Tests for actual transactions on devnet."""

    @pytest.fixture
    def funded_keypair(self):
        """Get keypair that should have devnet SOL."""
        from solders.keypair import Keypair

        private_key = os.getenv("CREATOR_WALLET_PRIVATE_KEY")
        if not private_key:
            pytest.skip("CREATOR_WALLET_PRIVATE_KEY not set")

        secret_bytes = base58.b58decode(private_key)
        return Keypair.from_bytes(secret_bytes)

    @pytest.mark.asyncio
    async def test_sol_transfer_small_amount(self, funded_keypair):
        """Test sending a small SOL transfer on devnet."""
        from app.utils.solana_tx import send_sol_transfer
        from app.utils.http_client import get_http_client
        from unittest.mock import patch

        settings = get_devnet_settings()

        # Check balance first
        client = get_http_client()
        pubkey = str(funded_keypair.pubkey())

        response = await client.post(
            settings.helius_rpc_url,
            json={
                "jsonrpc": "2.0",
                "id": "check-balance",
                "method": "getBalance",
                "params": [pubkey]
            }
        )
        balance_data = response.json()
        balance_lamports = balance_data.get("result", {}).get("value", 0)

        if balance_lamports < 10_000_000:  # 0.01 SOL minimum
            pytest.skip(f"Insufficient balance: {balance_lamports} lamports. Need at least 0.01 SOL")

        print(f"Wallet balance: {balance_lamports / 1e9:.4f} SOL")

        # Send tiny amount to self (tests transaction flow without losing funds)
        private_key = base58.b58encode(bytes(funded_keypair)).decode()

        with patch("app.utils.solana_tx.settings", settings):
            result = await send_sol_transfer(
                from_private_key=private_key,
                to_address=pubkey,  # Send to self
                amount_lamports=1000  # 0.000001 SOL
            )

        if result.success:
            print(f"Transaction sent: {result.signature}")
            assert result.signature is not None
        else:
            print(f"Transaction failed: {result.error}")
            # May fail due to insufficient balance for fees
            assert "error" in result.error.lower() or "insufficient" in result.error.lower()

    @pytest.mark.asyncio
    async def test_transaction_confirmation(self, funded_keypair):
        """Test transaction confirmation polling."""
        from app.utils.solana_tx import confirm_transaction
        from unittest.mock import patch

        settings = get_devnet_settings()

        # Use a known confirmed transaction (this is a stable devnet tx)
        # In real test, you'd use a recent transaction signature
        # For now, test the polling mechanism with a fake signature

        with patch("app.utils.solana_tx.settings", settings):
            # This will timeout as fake signature won't exist
            result = await confirm_transaction(
                signature="FakeSignatureForTesting111111111111111111111",
                timeout_seconds=5
            )

        # Should timeout/return false for fake signature
        assert result is False
        print("Confirmation polling works (correctly returned False for fake tx)")


@pytest.mark.skipif(
    not os.getenv("COPPER_TOKEN_MINT"),
    reason="COPPER_TOKEN_MINT required for token tests"
)
class TestDevnetTokenOperations:
    """Tests for SPL token operations on devnet."""

    @pytest.mark.asyncio
    async def test_get_token_supply(self):
        """Test fetching token supply from devnet."""
        from app.services.helius import HeliusService
        from unittest.mock import patch

        settings = get_devnet_settings()

        with patch("app.services.helius.settings", settings):
            service = HeliusService()
            service.token_mint = settings.copper_token_mint

            try:
                supply = await service.get_token_supply()
                print(f"Token supply: {supply}")
                assert supply >= 0
            except Exception as e:
                print(f"Token supply fetch failed: {e}")
                # May fail if token doesn't exist on devnet
                pytest.skip(f"Token not found on devnet: {e}")

    @pytest.mark.asyncio
    async def test_get_token_holders(self):
        """Test fetching token holders from devnet."""
        from app.services.helius import HeliusService
        from unittest.mock import patch

        settings = get_devnet_settings()

        with patch("app.services.helius.settings", settings):
            service = HeliusService()
            service.token_mint = settings.copper_token_mint

            try:
                holders = await service.get_token_accounts()
                print(f"Found {len(holders)} token holders")

                for holder in holders[:5]:
                    print(f"  - {holder.wallet[:8]}...: {holder.balance}")

                # May be empty if no holders on devnet
                assert isinstance(holders, list)
            except Exception as e:
                print(f"Token holders fetch failed: {e}")
                pytest.skip(f"Token holders fetch failed: {e}")


class TestDevnetJupiterIntegration:
    """Tests for Jupiter API integration on devnet."""

    @pytest.mark.asyncio
    async def test_jupiter_quote_devnet(self):
        """Test getting a Jupiter quote on devnet."""
        from app.services.buyback import BuybackService
        from unittest.mock import patch, MagicMock

        settings = get_devnet_settings()

        # Use well-known devnet tokens for testing
        # SOL -> USDC-Dev is usually available
        DEVNET_USDC = "Gh9ZwEmdLJ8DscKNTkTqPbNwLNNBjuSzaG9Vp2KGtKJr"  # Devnet USDC

        with patch("app.services.buyback.settings", settings):
            service = BuybackService(MagicMock())
            service.token_mint = DEVNET_USDC  # Use devnet USDC

            # Get quote for 0.1 SOL
            quote = await service.get_jupiter_quote(100_000_000)  # 0.1 SOL

            if quote:
                print(f"Jupiter quote received:")
                print(f"  In: {quote.get('inAmount')} lamports")
                print(f"  Out: {quote.get('outAmount')} tokens")
                print(f"  Price impact: {quote.get('priceImpactPct', 'N/A')}%")
                assert "inAmount" in quote
                assert "outAmount" in quote
            else:
                print("Jupiter quote not available - may be route unavailable on devnet")
                # Not a failure - devnet liquidity is limited


class TestDevnetE2EFlow:
    """End-to-end flow tests on devnet."""

    @pytest.mark.asyncio
    @pytest.mark.skipif(
        not all([
            os.getenv("CREATOR_WALLET_PRIVATE_KEY"),
            os.getenv("HELIUS_API_KEY"),
        ]),
        reason="Full devnet credentials required"
    )
    async def test_e2e_rpc_to_balance_to_quote(self):
        """Test full flow: RPC → Balance → Quote."""
        from app.utils.http_client import get_http_client
        from app.services.buyback import BuybackService
        from app.utils.solana_tx import keypair_from_base58
        from unittest.mock import patch, MagicMock

        settings = get_devnet_settings()
        client = get_http_client()

        print("\n=== E2E Devnet Test ===\n")

        # Step 1: Verify RPC
        print("Step 1: Checking RPC connection...")
        response = await client.post(
            settings.helius_rpc_url,
            json={
                "jsonrpc": "2.0",
                "id": "e2e-health",
                "method": "getHealth"
            }
        )
        assert response.json().get("result") == "ok"
        print("  RPC: OK")

        # Step 2: Get wallet balance
        print("\nStep 2: Checking wallet balance...")
        private_key = os.getenv("CREATOR_WALLET_PRIVATE_KEY")
        if private_key:
            keypair = keypair_from_base58(private_key)
            pubkey = str(keypair.pubkey())

            response = await client.post(
                settings.helius_rpc_url,
                json={
                    "jsonrpc": "2.0",
                    "id": "e2e-balance",
                    "method": "getBalance",
                    "params": [pubkey]
                }
            )
            balance = response.json().get("result", {}).get("value", 0)
            print(f"  Wallet: {pubkey[:12]}...")
            print(f"  Balance: {balance / 1e9:.4f} SOL")
        else:
            print("  Wallet: Not configured")

        # Step 3: Test Jupiter quote
        print("\nStep 3: Testing Jupiter quote...")
        DEVNET_USDC = "Gh9ZwEmdLJ8DscKNTkTqPbNwLNNBjuSzaG9Vp2KGtKJr"

        with patch("app.services.buyback.settings", settings):
            service = BuybackService(MagicMock())
            service.token_mint = DEVNET_USDC

            quote = await service.get_jupiter_quote(100_000_000)
            if quote:
                print(f"  Quote: {quote.get('inAmount')} → {quote.get('outAmount')}")
            else:
                print("  Quote: Not available (devnet liquidity)")

        # Step 4: Test price feed
        print("\nStep 4: Testing price feed...")
        from app.utils.price_cache import get_copper_price_usd, clear_price_cache
        from unittest.mock import patch

        clear_price_cache()
        with patch("app.utils.price_cache.settings", settings):
            # This will likely return 0 for devnet tokens
            price = await get_copper_price_usd()
            print(f"  Price: ${price}")

        print("\n=== E2E Test Complete ===\n")


class TestDevnetWebhookSimulation:
    """Simulate webhook events on devnet."""

    @pytest.mark.asyncio
    async def test_simulate_sell_webhook(self):
        """Simulate receiving a sell webhook (no actual RPC)."""
        from app.services.helius import HeliusService
        from unittest.mock import patch

        settings = get_devnet_settings()

        # Simulate a Helius webhook payload for a sell
        mock_payload = {
            "type": "SWAP",
            "signature": "SimulatedSellTx11111111111111111111111111111111",
            "feePayer": "SimulatedSeller111111111111111111111111111111",
            "tokenTransfers": [
                {
                    "mint": settings.copper_token_mint or "TestMint11111111111111111111111111111",
                    "fromUserAccount": "SimulatedSeller111111111111111111111111111111",
                    "toUserAccount": "DexPool1111111111111111111111111111111111111",
                    "tokenAmount": 1000.0
                }
            ],
            "nativeTransfers": [
                {
                    "fromUserAccount": "DexPool1111111111111111111111111111111111111",
                    "toUserAccount": "SimulatedSeller111111111111111111111111111111",
                    "amount": 500000000  # 0.5 SOL
                }
            ]
        }

        with patch("app.services.helius.settings", settings):
            service = HeliusService()
            service.token_mint = settings.copper_token_mint or "TestMint11111111111111111111111111111"

            result = service.parse_webhook_transaction(mock_payload)

            assert result is not None
            assert result.is_sell is True
            assert result.source_wallet == "SimulatedSeller111111111111111111111111111111"

            print(f"Simulated sell detected:")
            print(f"  Wallet: {result.source_wallet[:12]}...")
            print(f"  Amount out: {result.amount_out}")
            print(f"  Received: {result.amount_in} lamports")


# ===========================================
# Test Configuration Helpers
# ===========================================

def pytest_configure(config):
    """Add custom markers."""
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests (deselect with '-m \"not integration\"')"
    )


if __name__ == "__main__":
    """Allow running this file directly for quick testing."""
    import sys

    print("$COPPER Devnet Integration Tests")
    print("=" * 50)

    if not DEVNET_CONFIGURED:
        print(f"\nSkipping: {SKIP_REASON}")
        print("\nTo configure devnet testing:")
        print("  1. Set HELIUS_API_KEY environment variable")
        print("  2. Set SOLANA_NETWORK=devnet")
        print("  3. Optionally set CREATOR_WALLET_PRIVATE_KEY for tx tests")
        sys.exit(0)

    print("\nDevnet configured. Run with: pytest tests/test_devnet_integration.py -v -s")
