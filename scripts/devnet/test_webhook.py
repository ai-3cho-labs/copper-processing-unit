#!/usr/bin/env python3
"""
Devnet Webhook Test

Simulates Helius webhook payloads for testing sell detection.

Usage:
    python -m scripts.devnet.test_webhook [command]

Commands:
    simulate-sell <wallet>  - Simulate a sell webhook for a wallet
    simulate-buy <wallet>   - Simulate a buy webhook (should be ignored)
    simulate-transfer       - Simulate a transfer webhook (should be ignored)
    send <wallet>           - Send simulated webhook to running server
    status                  - Check webhook configuration status
    test-signature          - Test signature verification
    generate-payload        - Generate sample Helius webhook payload
"""

import asyncio
import hashlib
import hmac
import json
import os
import secrets
import sys
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Optional

import httpx
import base58

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "backend"))

from app.config import get_settings, SOL_MINT, USDC_MINT


def utc_now() -> datetime:
    """Get current UTC time (timezone-aware)."""
    return datetime.now(timezone.utc)


class WebhookTester:
    """Tests webhook handling."""

    def __init__(self):
        self.settings = get_settings()
        self.api_url = os.getenv("API_URL", "http://localhost:8000")

    def generate_signature(self, payload: str) -> str:
        """Generate HMAC signature for webhook payload."""
        if not self.settings.helius_webhook_secret:
            return ""

        return hmac.new(
            self.settings.helius_webhook_secret.encode(),
            payload.encode(),
            hashlib.sha256
        ).hexdigest()

    def generate_fake_signature(self) -> str:
        """Generate a random 64-character signature."""
        return base58.b58encode(secrets.token_bytes(64)).decode()

    def create_sell_payload(self, wallet: str, amount: int = 1000000) -> dict:
        """
        Create a simulated Helius webhook payload for a SELL.

        A sell is: COPPER → SOL/USDC swap

        Args:
            wallet: Wallet address that sold.
            amount: Amount of COPPER sold (raw, with decimals).

        Returns:
            Helius webhook payload dict.
        """
        signature = self.generate_fake_signature()
        sol_received = int(amount * 0.0001)  # Fake price

        return {
            "signature": signature,
            "type": "SWAP",
            "feePayer": wallet,
            "slot": 123456789,
            "timestamp": int(datetime.now(timezone.utc).timestamp()),
            "tokenTransfers": [
                {
                    # COPPER being sold (sent out)
                    "mint": self.settings.copper_token_mint,
                    "fromUserAccount": wallet,
                    "toUserAccount": "DEXPoolAddress111111111111111111111111111",
                    "tokenAmount": amount / 1e6,  # Convert to human readable
                },
            ],
            "nativeTransfers": [
                {
                    # SOL being received
                    "fromUserAccount": "DEXPoolAddress111111111111111111111111111",
                    "toUserAccount": wallet,
                    "amount": sol_received,
                }
            ],
            "source": "JUPITER",
            "description": f"Swapped {amount / 1e6:.2f} COPPER for {sol_received / 1e9:.4f} SOL",
        }

    def create_buy_payload(self, wallet: str, amount: int = 1000000) -> dict:
        """
        Create a simulated Helius webhook payload for a BUY.

        A buy is: SOL/USDC → COPPER swap (should be IGNORED)

        Args:
            wallet: Wallet address that bought.
            amount: Amount of COPPER received (raw, with decimals).

        Returns:
            Helius webhook payload dict.
        """
        signature = self.generate_fake_signature()
        sol_spent = int(amount * 0.0001)

        return {
            "signature": signature,
            "type": "SWAP",
            "feePayer": wallet,
            "slot": 123456789,
            "timestamp": int(datetime.now(timezone.utc).timestamp()),
            "tokenTransfers": [
                {
                    # COPPER being received
                    "mint": self.settings.copper_token_mint,
                    "fromUserAccount": "DEXPoolAddress111111111111111111111111111",
                    "toUserAccount": wallet,
                    "tokenAmount": amount / 1e6,
                },
            ],
            "nativeTransfers": [
                {
                    # SOL being sent out
                    "fromUserAccount": wallet,
                    "toUserAccount": "DEXPoolAddress111111111111111111111111111",
                    "amount": sol_spent,
                }
            ],
            "source": "JUPITER",
            "description": f"Swapped {sol_spent / 1e9:.4f} SOL for {amount / 1e6:.2f} COPPER",
        }

    def create_transfer_payload(self, from_wallet: str, to_wallet: str, amount: int = 1000000) -> dict:
        """
        Create a simulated Helius webhook payload for a TRANSFER.

        A transfer is: COPPER → COPPER (wallet to wallet, should be IGNORED)

        Args:
            from_wallet: Sender wallet.
            to_wallet: Receiver wallet.
            amount: Amount transferred.

        Returns:
            Helius webhook payload dict.
        """
        signature = self.generate_fake_signature()

        return {
            "signature": signature,
            "type": "TRANSFER",
            "feePayer": from_wallet,
            "slot": 123456789,
            "timestamp": int(datetime.now(timezone.utc).timestamp()),
            "tokenTransfers": [
                {
                    "mint": self.settings.copper_token_mint,
                    "fromUserAccount": from_wallet,
                    "toUserAccount": to_wallet,
                    "tokenAmount": amount / 1e6,
                },
            ],
            "nativeTransfers": [],
            "source": "SYSTEM",
            "description": f"Transferred {amount / 1e6:.2f} COPPER",
        }

    async def simulate_sell(self, wallet: str, amount: int = 1000000):
        """Simulate a sell webhook and show parsed result."""
        print(f"\n=== Simulating SELL Webhook ===\n")

        if not self.settings.copper_token_mint:
            print("Error: COPPER_TOKEN_MINT not set")
            return

        payload = self.create_sell_payload(wallet, amount)

        print(f"  Wallet:     {wallet}")
        print(f"  Amount:     {amount / 1e6:,.2f} COPPER")
        print(f"  Signature:  {payload['signature'][:32]}...")
        print(f"  Type:       {payload['type']}")

        # Parse using backend service
        from app.services.helius import HeliusService

        helius = HeliusService(self.settings)
        parsed = helius.parse_webhook_transaction(payload)

        print(f"\n  Parsed Result:")
        if parsed:
            print(f"    Is Sell:       {parsed.is_sell}")
            print(f"    Source Wallet: {parsed.source_wallet}")
            print(f"    Token Out:     {parsed.token_out[:16]}...")
            print(f"    Amount Out:    {parsed.amount_out:,}")
            print(f"    Token In:      {parsed.token_in}")
            print(f"    Amount In:     {parsed.amount_in:,}")

            if parsed.is_sell:
                print(f"\n  This would trigger a streak penalty for {wallet[:16]}...")
        else:
            print("    Not parsed as a valid sell transaction")

        print(f"\n  Raw Payload:")
        print(f"    {json.dumps(payload, indent=4)[:500]}...")

    async def simulate_buy(self, wallet: str, amount: int = 1000000):
        """Simulate a buy webhook (should be ignored)."""
        print(f"\n=== Simulating BUY Webhook ===\n")

        if not self.settings.copper_token_mint:
            print("Error: COPPER_TOKEN_MINT not set")
            return

        payload = self.create_buy_payload(wallet, amount)

        print(f"  Wallet:     {wallet}")
        print(f"  Amount:     {amount / 1e6:,.2f} COPPER (received)")
        print(f"  Type:       {payload['type']}")

        # Parse using backend service
        from app.services.helius import HeliusService

        helius = HeliusService(self.settings)
        parsed = helius.parse_webhook_transaction(payload)

        print(f"\n  Parsed Result:")
        if parsed and parsed.is_sell:
            print("    WARNING: Incorrectly detected as sell!")
        else:
            print("    Correctly ignored (not a sell)")

    async def simulate_transfer(self):
        """Simulate a transfer webhook (should be ignored)."""
        print(f"\n=== Simulating TRANSFER Webhook ===\n")

        if not self.settings.copper_token_mint:
            print("Error: COPPER_TOKEN_MINT not set")
            return

        from_wallet = "FromWallet111111111111111111111111111111111"
        to_wallet = "ToWallet11111111111111111111111111111111111"
        payload = self.create_transfer_payload(from_wallet, to_wallet)

        print(f"  From:   {from_wallet}")
        print(f"  To:     {to_wallet}")
        print(f"  Type:   {payload['type']}")

        # Parse using backend service
        from app.services.helius import HeliusService

        helius = HeliusService(self.settings)
        parsed = helius.parse_webhook_transaction(payload)

        print(f"\n  Parsed Result:")
        if parsed and parsed.is_sell:
            print("    WARNING: Incorrectly detected as sell!")
        else:
            print("    Correctly ignored (not a sell)")

    async def send_webhook(self, wallet: str, amount: int = 1000000):
        """Send simulated webhook to running server."""
        print(f"\n=== Sending Webhook to Server ===\n")

        if not self.settings.copper_token_mint:
            print("Error: COPPER_TOKEN_MINT not set")
            return

        payload = self.create_sell_payload(wallet, amount)
        payload_json = json.dumps([payload])  # Helius sends batches

        # Generate signature
        signature = self.generate_signature(payload_json)

        if not signature:
            print("Error: HELIUS_WEBHOOK_SECRET not set - cannot sign request")
            print("  Set this in your .env to test authenticated webhooks")
            return

        url = f"{self.api_url}/api/webhook/helius"
        print(f"  URL:        {url}")
        print(f"  Wallet:     {wallet}")
        print(f"  Amount:     {amount / 1e6:,.2f} COPPER")
        print(f"  Signature:  {signature[:32]}...")

        async with httpx.AsyncClient(timeout=30) as client:
            try:
                response = await client.post(
                    url,
                    content=payload_json,
                    headers={
                        "Content-Type": "application/json",
                        "x-helius-signature": signature,
                    }
                )

                print(f"\n  Response:")
                print(f"    Status: {response.status_code}")
                print(f"    Body:   {response.text}")

                if response.status_code == 200:
                    print("\n  Webhook processed successfully!")
                    print("  Check the database or API to verify streak was updated.")

            except httpx.ConnectError:
                print(f"\n  Error: Could not connect to {self.api_url}")
                print("  Make sure the backend server is running.")

    async def check_status(self):
        """Check webhook configuration status."""
        print(f"\n=== Webhook Status ===\n")

        url = f"{self.api_url}/api/webhook/helius/status"
        print(f"  Checking: {url}")

        async with httpx.AsyncClient(timeout=10) as client:
            try:
                response = await client.get(url)
                print(f"  Status: {response.status_code}")
                print(f"  Response: {json.dumps(response.json(), indent=4)}")

            except httpx.ConnectError:
                print(f"\n  Error: Could not connect to {self.api_url}")

        # Local config check
        print(f"\n  Local Configuration:")
        print(f"    HELIUS_WEBHOOK_SECRET: {'Set' if self.settings.helius_webhook_secret else 'NOT SET'}")
        print(f"    COPPER_TOKEN_MINT: {self.settings.copper_token_mint or 'NOT SET'}")

    async def test_signature(self):
        """Test signature verification."""
        print(f"\n=== Testing Signature Verification ===\n")

        test_payload = '{"test": "data"}'

        # Generate valid signature
        valid_sig = self.generate_signature(test_payload)

        print(f"  Payload: {test_payload}")
        print(f"  Valid Signature: {valid_sig}")

        # Test verification
        from app.api.webhook import verify_webhook_signature

        # Test valid signature
        result = verify_webhook_signature(
            test_payload.encode(),
            valid_sig,
            self.settings.helius_webhook_secret
        )
        print(f"\n  Valid signature check: {'PASS' if result else 'FAIL'}")

        # Test invalid signature
        result = verify_webhook_signature(
            test_payload.encode(),
            "invalid_signature",
            self.settings.helius_webhook_secret
        )
        print(f"  Invalid signature check: {'FAIL (expected)' if not result else 'UNEXPECTED PASS'}")

        # Test empty secret
        result = verify_webhook_signature(
            test_payload.encode(),
            valid_sig,
            ""
        )
        print(f"  Empty secret check: {'FAIL (expected)' if not result else 'UNEXPECTED PASS'}")

    def generate_payload_example(self):
        """Generate and print sample webhook payloads."""
        print(f"\n=== Sample Helius Webhook Payloads ===\n")

        print("1. SELL Transaction (triggers streak penalty):")
        sell_payload = {
            "signature": "5abc123...",
            "type": "SWAP",
            "feePayer": "WalletAddressHere...",
            "slot": 123456789,
            "timestamp": 1704067200,
            "tokenTransfers": [
                {
                    "mint": "<COPPER_TOKEN_MINT>",
                    "fromUserAccount": "WalletAddressHere...",
                    "toUserAccount": "DEXPoolAddress...",
                    "tokenAmount": 1000.0,
                }
            ],
            "nativeTransfers": [
                {
                    "fromUserAccount": "DEXPoolAddress...",
                    "toUserAccount": "WalletAddressHere...",
                    "amount": 100000000,  # 0.1 SOL
                }
            ],
            "source": "JUPITER",
        }
        print(json.dumps(sell_payload, indent=2))

        print("\n\n2. BUY Transaction (ignored):")
        buy_payload = {
            "signature": "5def456...",
            "type": "SWAP",
            "feePayer": "WalletAddressHere...",
            "tokenTransfers": [
                {
                    "mint": "<COPPER_TOKEN_MINT>",
                    "fromUserAccount": "DEXPoolAddress...",
                    "toUserAccount": "WalletAddressHere...",
                    "tokenAmount": 1000.0,
                }
            ],
            "nativeTransfers": [
                {
                    "fromUserAccount": "WalletAddressHere...",
                    "toUserAccount": "DEXPoolAddress...",
                    "amount": 100000000,
                }
            ],
        }
        print(json.dumps(buy_payload, indent=2))

        print("\n\n3. TRANSFER (ignored):")
        transfer_payload = {
            "signature": "5ghi789...",
            "type": "TRANSFER",
            "feePayer": "FromWallet...",
            "tokenTransfers": [
                {
                    "mint": "<COPPER_TOKEN_MINT>",
                    "fromUserAccount": "FromWallet...",
                    "toUserAccount": "ToWallet...",
                    "tokenAmount": 500.0,
                }
            ],
            "nativeTransfers": [],
        }
        print(json.dumps(transfer_payload, indent=2))


async def main():
    tester = WebhookTester()

    if len(sys.argv) < 2:
        print(__doc__)
        return

    command = sys.argv[1].lower()

    if command == "simulate-sell":
        if len(sys.argv) < 3:
            print("Usage: test_webhook.py simulate-sell <wallet> [amount]")
            return
        wallet = sys.argv[2]
        amount = int(float(sys.argv[3]) * 1e6) if len(sys.argv) > 3 else 1000000
        await tester.simulate_sell(wallet, amount)

    elif command == "simulate-buy":
        if len(sys.argv) < 3:
            print("Usage: test_webhook.py simulate-buy <wallet> [amount]")
            return
        wallet = sys.argv[2]
        amount = int(float(sys.argv[3]) * 1e6) if len(sys.argv) > 3 else 1000000
        await tester.simulate_buy(wallet, amount)

    elif command == "simulate-transfer":
        await tester.simulate_transfer()

    elif command == "send":
        if len(sys.argv) < 3:
            print("Usage: test_webhook.py send <wallet> [amount]")
            return
        wallet = sys.argv[2]
        amount = int(float(sys.argv[3]) * 1e6) if len(sys.argv) > 3 else 1000000
        await tester.send_webhook(wallet, amount)

    elif command == "status":
        await tester.check_status()

    elif command == "test-signature":
        await tester.test_signature()

    elif command == "generate-payload":
        tester.generate_payload_example()

    else:
        print(f"Unknown command: {command}")
        print(__doc__)


if __name__ == "__main__":
    asyncio.run(main())
