#!/usr/bin/env python3
"""
Devnet Setup Script

Creates test token, wallets, and distributes tokens for devnet testing.

Usage:
    python -m scripts.devnet.setup [command]

Commands:
    init        - Full setup: create wallets, token, distribute
    wallets     - Create test wallets only
    token       - Create test token only
    distribute  - Distribute tokens to test holders
    fund        - Request devnet SOL airdrops
    status      - Show current devnet setup status
    export      - Export configuration for .env file
"""

import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Optional
import base58
import struct

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "backend"))

import httpx
from solders.keypair import Keypair
from solders.pubkey import Pubkey
from solders.system_program import TransferParams, transfer
from solders.transaction import Transaction
from solders.message import Message
from solders.hash import Hash

# Configuration
DEVNET_RPC = "https://api.devnet.solana.com"
NUM_TEST_HOLDERS = 5
TOKEN_DECIMALS = 9
TOTAL_SUPPLY = 1_000_000_000  # 1 billion tokens
WALLET_DIR = Path.home() / ".config" / "solana" / "copper-devnet"

# Token distribution for test holders (in whole tokens)
HOLDER_DISTRIBUTIONS = [
    10_000_000,   # Holder 1: 10M (largest holder)
    5_000_000,    # Holder 2: 5M
    2_500_000,    # Holder 3: 2.5M
    1_000_000,    # Holder 4: 1M
    500_000,      # Holder 5: 500K (smallest holder)
]


class DevnetSetup:
    """Manages devnet testing setup."""

    def __init__(self):
        self.rpc_url = os.getenv("DEVNET_RPC_URL", DEVNET_RPC)
        self.wallet_dir = WALLET_DIR
        self.wallet_dir.mkdir(parents=True, exist_ok=True)

        # Wallet paths
        self.main_wallet_path = self.wallet_dir / "main.json"
        self.holder_wallet_paths = [
            self.wallet_dir / f"holder-{i+1}.json" for i in range(NUM_TEST_HOLDERS)
        ]
        self.token_info_path = self.wallet_dir / "token.json"

    async def rpc_call(self, method: str, params: list = None) -> dict:
        """Make RPC call to Solana devnet."""
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                self.rpc_url,
                json={
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": method,
                    "params": params or [],
                },
            )
            result = response.json()
            if "error" in result:
                raise Exception(f"RPC error: {result['error']}")
            return result.get("result")

    def load_keypair(self, path: Path) -> Optional[Keypair]:
        """Load keypair from JSON file."""
        if not path.exists():
            return None
        with open(path) as f:
            secret_key = json.load(f)
        return Keypair.from_bytes(bytes(secret_key))

    def save_keypair(self, keypair: Keypair, path: Path):
        """Save keypair to JSON file (Solana CLI compatible format)."""
        with open(path, "w") as f:
            json.dump(list(bytes(keypair)), f)
        print(f"  Saved: {path}")

    def create_wallet(self, path: Path, name: str) -> Keypair:
        """Create or load a wallet."""
        existing = self.load_keypair(path)
        if existing:
            print(f"  {name}: {existing.pubkey()} (existing)")
            return existing

        keypair = Keypair()
        self.save_keypair(keypair, path)
        print(f"  {name}: {keypair.pubkey()} (created)")
        return keypair

    async def request_airdrop(self, pubkey: Pubkey, amount_sol: float = 2.0) -> str:
        """Request devnet SOL airdrop."""
        lamports = int(amount_sol * 1_000_000_000)
        try:
            signature = await self.rpc_call(
                "requestAirdrop", [str(pubkey), lamports]
            )
            print(f"  Airdrop requested: {amount_sol} SOL to {str(pubkey)[:8]}...")
            return signature
        except Exception as e:
            print(f"  Airdrop failed for {str(pubkey)[:8]}...: {e}")
            return None

    async def get_balance(self, pubkey: Pubkey) -> float:
        """Get SOL balance for a wallet."""
        result = await self.rpc_call("getBalance", [str(pubkey)])
        return result.get("value", 0) / 1_000_000_000

    async def get_token_balance(self, pubkey: Pubkey, mint: Pubkey) -> float:
        """Get token balance for a wallet."""
        try:
            # Get associated token account
            ata = self.get_associated_token_address(pubkey, mint)
            result = await self.rpc_call(
                "getTokenAccountBalance", [str(ata)]
            )
            if result and "value" in result:
                return float(result["value"]["uiAmount"] or 0)
        except Exception:
            pass
        return 0

    def get_associated_token_address(self, owner: Pubkey, mint: Pubkey) -> Pubkey:
        """Derive associated token account address."""
        # SPL Associated Token Account Program ID
        ATA_PROGRAM_ID = Pubkey.from_string(
            "ATokenGPvbdGVxr1b2hvZbsiqW5xWH25efTNsLJA8knL"
        )
        TOKEN_PROGRAM_ID = Pubkey.from_string(
            "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"
        )

        # Derive PDA
        seeds = [bytes(owner), bytes(TOKEN_PROGRAM_ID), bytes(mint)]
        pda, _ = Pubkey.find_program_address(seeds, ATA_PROGRAM_ID)
        return pda

    async def confirm_transaction(self, signature: str, max_retries: int = 30) -> bool:
        """Wait for transaction confirmation."""
        for _ in range(max_retries):
            result = await self.rpc_call(
                "getSignatureStatuses", [[signature]]
            )
            if result and result["value"][0]:
                status = result["value"][0]
                if status.get("confirmationStatus") in ["confirmed", "finalized"]:
                    return True
                if status.get("err"):
                    print(f"  Transaction failed: {status['err']}")
                    return False
            await asyncio.sleep(1)
        return False

    # =========================================================================
    # Commands
    # =========================================================================

    async def cmd_wallets(self):
        """Create all test wallets."""
        print("\n=== Creating Wallets ===\n")

        # Main wallet (creator/buyback/distribution)
        main_wallet = self.create_wallet(self.main_wallet_path, "Main Wallet")

        # Test holder wallets
        holder_wallets = []
        for i, path in enumerate(self.holder_wallet_paths):
            wallet = self.create_wallet(path, f"Holder {i+1}")
            holder_wallets.append(wallet)

        return main_wallet, holder_wallets

    async def cmd_fund(self):
        """Fund all wallets with devnet SOL."""
        print("\n=== Funding Wallets ===\n")

        main_wallet = self.load_keypair(self.main_wallet_path)
        if not main_wallet:
            print("Error: Main wallet not found. Run 'wallets' first.")
            return

        # Fund main wallet
        balance = await self.get_balance(main_wallet.pubkey())
        if balance < 1.0:
            await self.request_airdrop(main_wallet.pubkey(), 2.0)
            await asyncio.sleep(2)
            await self.request_airdrop(main_wallet.pubkey(), 2.0)
        else:
            print(f"  Main wallet has {balance:.2f} SOL")

        # Fund holder wallets
        for i, path in enumerate(self.holder_wallet_paths):
            wallet = self.load_keypair(path)
            if wallet:
                balance = await self.get_balance(wallet.pubkey())
                if balance < 0.5:
                    await self.request_airdrop(wallet.pubkey(), 1.0)
                else:
                    print(f"  Holder {i+1} has {balance:.2f} SOL")

        print("\n  Waiting for confirmations...")
        await asyncio.sleep(15)

        # Check final balances
        print("\n=== Final Balances ===\n")
        balance = await self.get_balance(main_wallet.pubkey())
        print(f"  Main: {balance:.4f} SOL")
        for i, path in enumerate(self.holder_wallet_paths):
            wallet = self.load_keypair(path)
            if wallet:
                balance = await self.get_balance(wallet.pubkey())
                print(f"  Holder {i+1}: {balance:.4f} SOL")

    async def cmd_token(self):
        """Create test token on devnet using SPL Token CLI."""
        print("\n=== Creating Test Token ===\n")

        main_wallet = self.load_keypair(self.main_wallet_path)
        if not main_wallet:
            print("Error: Main wallet not found. Run 'wallets' first.")
            return None

        # Check if token already exists
        if self.token_info_path.exists():
            with open(self.token_info_path) as f:
                token_info = json.load(f)
            print(f"  Token already exists: {token_info['mint']}")
            return token_info["mint"]

        print("  Creating token requires SPL Token CLI.")
        print("  Run the following commands manually:\n")

        wallet_path = str(self.main_wallet_path)
        print(f"  # Set Solana to devnet")
        print(f"  solana config set --url devnet")
        print(f"  solana config set --keypair {wallet_path}")
        print()
        print(f"  # Create token")
        print(f"  spl-token create-token --decimals {TOKEN_DECIMALS}")
        print()
        print(f"  # After creating, save the mint address:")
        print(f"  # Then run: python -m scripts.devnet.setup save-token <MINT_ADDRESS>")

        return None

    async def cmd_save_token(self, mint_address: str):
        """Save token mint address after manual creation."""
        print(f"\n=== Saving Token Info ===\n")

        try:
            mint = Pubkey.from_string(mint_address)
        except Exception as e:
            print(f"Error: Invalid mint address: {e}")
            return

        token_info = {
            "mint": mint_address,
            "decimals": TOKEN_DECIMALS,
            "network": "devnet",
        }

        with open(self.token_info_path, "w") as f:
            json.dump(token_info, f, indent=2)

        print(f"  Saved token info: {self.token_info_path}")
        print(f"  Mint: {mint_address}")
        print(f"  Decimals: {TOKEN_DECIMALS}")

    async def cmd_mint(self):
        """Mint tokens to main wallet (requires SPL Token CLI)."""
        print("\n=== Minting Tokens ===\n")

        if not self.token_info_path.exists():
            print("Error: Token not found. Run 'token' first.")
            return

        with open(self.token_info_path) as f:
            token_info = json.load(f)

        mint = token_info["mint"]
        wallet_path = str(self.main_wallet_path)

        print("  Run the following commands:\n")
        print(f"  # Create token account")
        print(f"  spl-token create-account {mint}")
        print()
        print(f"  # Mint tokens")
        print(f"  spl-token mint {mint} {TOTAL_SUPPLY}")
        print()
        print(f"  # Verify balance")
        print(f"  spl-token balance {mint}")

    async def cmd_distribute(self):
        """Distribute tokens to test holders (requires SPL Token CLI)."""
        print("\n=== Distributing Tokens ===\n")

        if not self.token_info_path.exists():
            print("Error: Token not found. Run 'token' first.")
            return

        with open(self.token_info_path) as f:
            token_info = json.load(f)

        mint = token_info["mint"]

        print("  Run the following commands to distribute tokens:\n")

        for i, path in enumerate(self.holder_wallet_paths):
            wallet = self.load_keypair(path)
            if wallet:
                amount = HOLDER_DISTRIBUTIONS[i]
                print(f"  # Holder {i+1}: {amount:,} tokens")
                print(f"  spl-token transfer {mint} {amount} {wallet.pubkey()} --fund-recipient")
                print()

    async def cmd_status(self):
        """Show current devnet setup status."""
        print("\n=== Devnet Setup Status ===\n")

        # Main wallet
        main_wallet = self.load_keypair(self.main_wallet_path)
        if main_wallet:
            balance = await self.get_balance(main_wallet.pubkey())
            print(f"Main Wallet:")
            print(f"  Address: {main_wallet.pubkey()}")
            print(f"  Balance: {balance:.4f} SOL")
        else:
            print("Main Wallet: Not created")

        print()

        # Token
        if self.token_info_path.exists():
            with open(self.token_info_path) as f:
                token_info = json.load(f)
            print(f"Test Token:")
            print(f"  Mint: {token_info['mint']}")
            print(f"  Decimals: {token_info['decimals']}")

            mint = Pubkey.from_string(token_info["mint"])

            if main_wallet:
                token_bal = await self.get_token_balance(main_wallet.pubkey(), mint)
                print(f"  Main wallet tokens: {token_bal:,.0f}")
        else:
            print("Test Token: Not created")

        print()

        # Holders
        print("Test Holders:")
        for i, path in enumerate(self.holder_wallet_paths):
            wallet = self.load_keypair(path)
            if wallet:
                sol_bal = await self.get_balance(wallet.pubkey())
                status = f"{sol_bal:.4f} SOL"

                if self.token_info_path.exists():
                    with open(self.token_info_path) as f:
                        token_info = json.load(f)
                    mint = Pubkey.from_string(token_info["mint"])
                    token_bal = await self.get_token_balance(wallet.pubkey(), mint)
                    status += f", {token_bal:,.0f} tokens"

                print(f"  Holder {i+1}: {str(wallet.pubkey())[:16]}... ({status})")
            else:
                print(f"  Holder {i+1}: Not created")

    async def cmd_export(self):
        """Export configuration for .env file."""
        print("\n=== Environment Configuration ===\n")
        print("# Add these to your .env file for devnet testing:\n")

        print("# Solana Network")
        print("SOLANA_NETWORK=devnet")
        print()

        # Main wallet
        main_wallet = self.load_keypair(self.main_wallet_path)
        if main_wallet:
            private_key = base58.b58encode(bytes(main_wallet)).decode()
            print("# Main Wallet (Creator/Buyback/Distribution)")
            print(f"TEAM_WALLET_PUBLIC_KEY={main_wallet.pubkey()}")
            print(f"CREATOR_WALLET_PRIVATE_KEY={private_key}")
            print(f"BUYBACK_WALLET_PRIVATE_KEY={private_key}")
            print(f"AIRDROP_POOL_PRIVATE_KEY={private_key}")
            print()

        # Token
        if self.token_info_path.exists():
            with open(self.token_info_path) as f:
                token_info = json.load(f)
            print("# Test Token")
            print(f"COPPER_TOKEN_MINT={token_info['mint']}")
            print(f"COPPER_TOKEN_DECIMALS={token_info['decimals']}")
            print()

        # Test holders (for testing scripts)
        print("# Test Holders (for scripts only)")
        for i, path in enumerate(self.holder_wallet_paths):
            wallet = self.load_keypair(path)
            if wallet:
                print(f"TEST_HOLDER_{i+1}={wallet.pubkey()}")
        print()

        # RPC
        print("# Helius RPC (use your API key)")
        print("# SOLANA_RPC_URL=https://devnet.helius-rpc.com/?api-key=YOUR_KEY")

    async def cmd_init(self):
        """Full initialization: wallets, fund, and show token instructions."""
        await self.cmd_wallets()
        await self.cmd_fund()
        await self.cmd_token()
        print("\n" + "=" * 60)
        print("After creating the token, run:")
        print("  python -m scripts.devnet.setup save-token <MINT_ADDRESS>")
        print("  python -m scripts.devnet.setup mint")
        print("  python -m scripts.devnet.setup distribute")
        print("  python -m scripts.devnet.setup status")
        print("  python -m scripts.devnet.setup export")
        print("=" * 60)


async def main():
    setup = DevnetSetup()

    if len(sys.argv) < 2:
        print(__doc__)
        return

    command = sys.argv[1].lower()

    if command == "init":
        await setup.cmd_init()
    elif command == "wallets":
        await setup.cmd_wallets()
    elif command == "fund":
        await setup.cmd_fund()
    elif command == "token":
        await setup.cmd_token()
    elif command == "save-token":
        if len(sys.argv) < 3:
            print("Usage: setup.py save-token <MINT_ADDRESS>")
            return
        await setup.cmd_save_token(sys.argv[2])
    elif command == "mint":
        await setup.cmd_mint()
    elif command == "distribute":
        await setup.cmd_distribute()
    elif command == "status":
        await setup.cmd_status()
    elif command == "export":
        await setup.cmd_export()
    else:
        print(f"Unknown command: {command}")
        print(__doc__)


if __name__ == "__main__":
    asyncio.run(main())
