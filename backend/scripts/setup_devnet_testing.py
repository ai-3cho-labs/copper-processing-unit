#!/usr/bin/env python3
"""
$COPPER Devnet Testing Setup Script

This script helps set up and verify devnet testing configuration.

Usage:
    python scripts/setup_devnet_testing.py [--create-wallet] [--check]
"""

import os
import sys
import asyncio
import argparse
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))


def check_environment():
    """Check if environment variables are set for devnet testing."""
    print("\n=== Environment Check ===\n")

    required = {
        "HELIUS_API_KEY": "Helius API key for RPC access",
        "SOLANA_NETWORK": "Should be 'devnet' for testing",
    }

    optional = {
        "CREATOR_WALLET_PRIVATE_KEY": "Required for transaction tests",
        "COPPER_TOKEN_MINT": "Required for token-specific tests",
        "TEAM_WALLET_PUBLIC_KEY": "Required for team transfer tests",
    }

    all_good = True

    print("Required variables:")
    for var, desc in required.items():
        value = os.getenv(var)
        if value:
            display_value = value[:8] + "..." if len(value) > 10 else value
            print(f"  [OK] {var}: {display_value}")
        else:
            print(f"  [MISSING] {var}: {desc}")
            all_good = False

    print("\nOptional variables:")
    for var, desc in optional.items():
        value = os.getenv(var)
        if value:
            display_value = value[:8] + "..." if len(value) > 10 else value
            print(f"  [OK] {var}: {display_value}")
        else:
            print(f"  [--] {var}: {desc}")

    # Check SOLANA_NETWORK value
    network = os.getenv("SOLANA_NETWORK", "")
    if network and network != "devnet":
        print(f"\n[WARNING] SOLANA_NETWORK is '{network}', should be 'devnet' for testing!")
        all_good = False

    return all_good


def create_test_wallet():
    """Create a new test wallet for devnet testing."""
    try:
        from solders.keypair import Keypair
        import base58

        print("\n=== Creating Test Wallet ===\n")

        keypair = Keypair()
        public_key = str(keypair.pubkey())
        private_key = base58.b58encode(bytes(keypair)).decode()

        print(f"Public Key:  {public_key}")
        print(f"Private Key: {private_key[:20]}...{private_key[-10:]}")
        print("\nIMPORTANT: Save the private key securely!")
        print("\nTo fund this wallet on devnet:")
        print(f"  solana airdrop 2 {public_key} --url devnet")
        print("\nAdd to your .env:")
        print(f"  CREATOR_WALLET_PRIVATE_KEY={private_key}")

        return public_key, private_key

    except ImportError:
        print("Error: solders package not installed")
        print("Run: pip install solders")
        return None, None


async def test_rpc_connection():
    """Test RPC connection to devnet."""
    print("\n=== Testing RPC Connection ===\n")

    api_key = os.getenv("HELIUS_API_KEY")
    if not api_key:
        print("Error: HELIUS_API_KEY not set")
        return False

    try:
        import httpx

        rpc_url = f"https://devnet.helius-rpc.com/?api-key={api_key}"

        async with httpx.AsyncClient() as client:
            response = await client.post(
                rpc_url,
                json={
                    "jsonrpc": "2.0",
                    "id": "test",
                    "method": "getHealth"
                },
                timeout=10.0
            )

            data = response.json()
            if data.get("result") == "ok":
                print(f"[OK] RPC connection successful")

                # Get slot
                slot_response = await client.post(
                    rpc_url,
                    json={
                        "jsonrpc": "2.0",
                        "id": "slot",
                        "method": "getSlot"
                    }
                )
                slot = slot_response.json().get("result", 0)
                print(f"[OK] Current devnet slot: {slot}")
                return True
            else:
                print(f"[FAIL] RPC health check failed: {data}")
                return False

    except Exception as e:
        print(f"[FAIL] RPC connection error: {e}")
        return False


async def test_wallet_balance():
    """Test wallet balance on devnet."""
    print("\n=== Testing Wallet Balance ===\n")

    api_key = os.getenv("HELIUS_API_KEY")
    private_key = os.getenv("CREATOR_WALLET_PRIVATE_KEY")

    if not api_key or not private_key:
        print("Error: HELIUS_API_KEY and CREATOR_WALLET_PRIVATE_KEY required")
        return False

    try:
        import httpx
        import base58
        from solders.keypair import Keypair

        # Get public key from private key
        secret_bytes = base58.b58decode(private_key)
        keypair = Keypair.from_bytes(secret_bytes)
        public_key = str(keypair.pubkey())

        print(f"Wallet: {public_key}")

        rpc_url = f"https://devnet.helius-rpc.com/?api-key={api_key}"

        async with httpx.AsyncClient() as client:
            response = await client.post(
                rpc_url,
                json={
                    "jsonrpc": "2.0",
                    "id": "balance",
                    "method": "getBalance",
                    "params": [public_key]
                }
            )

            data = response.json()
            balance_lamports = data.get("result", {}).get("value", 0)
            balance_sol = balance_lamports / 1_000_000_000

            print(f"Balance: {balance_sol:.4f} SOL ({balance_lamports} lamports)")

            if balance_sol < 0.01:
                print(f"\n[WARNING] Low balance! Fund with:")
                print(f"  solana airdrop 2 {public_key} --url devnet")

            return True

    except Exception as e:
        print(f"[FAIL] Balance check error: {e}")
        return False


def print_test_commands():
    """Print helpful test commands."""
    print("\n=== Test Commands ===\n")

    print("Run all unit tests (no devnet required):")
    print("  pytest tests/ -v -m 'not integration'")
    print("")
    print("Run integration tests (requires devnet config):")
    print("  pytest tests/test_devnet_integration.py -v -s")
    print("")
    print("Run specific test class:")
    print("  pytest tests/test_devnet_integration.py::TestDevnetRPCConnection -v -s")
    print("")
    print("Run with coverage:")
    print("  pytest tests/ --cov=app --cov-report=html")


async def main():
    parser = argparse.ArgumentParser(description="Setup devnet testing for $COPPER")
    parser.add_argument("--create-wallet", action="store_true", help="Create a new test wallet")
    parser.add_argument("--check", action="store_true", help="Check configuration and connectivity")
    parser.add_argument("--commands", action="store_true", help="Show test commands")

    args = parser.parse_args()

    print("$COPPER Devnet Testing Setup")
    print("=" * 50)

    # Load .env file if exists
    env_file = Path(__file__).parent.parent / ".env"
    if env_file.exists():
        print(f"\nLoading environment from: {env_file}")
        from dotenv import load_dotenv
        load_dotenv(env_file)

    if args.create_wallet:
        create_test_wallet()
        return

    if args.commands:
        print_test_commands()
        return

    # Default: check everything
    env_ok = check_environment()

    if os.getenv("HELIUS_API_KEY"):
        rpc_ok = await test_rpc_connection()

        if os.getenv("CREATOR_WALLET_PRIVATE_KEY"):
            await test_wallet_balance()

    print_test_commands()

    if env_ok:
        print("\n[READY] Devnet testing is configured!")
    else:
        print("\n[NOT READY] Some configuration is missing.")
        print("See above for details.")


if __name__ == "__main__":
    asyncio.run(main())
