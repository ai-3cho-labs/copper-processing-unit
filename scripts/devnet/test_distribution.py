#!/usr/bin/env python3
"""
Devnet Distribution Test

Tests distribution calculation and token transfers on devnet.

Usage:
    python -m scripts.devnet.test_distribution [command]

Commands:
    status              - Show pool status and trigger checks
    calculate           - Calculate distribution without executing
    execute             - Execute distribution (records + transfers)
    list                - List recent distributions
    history <wallet>    - Show distribution history for wallet
    stats               - Show distribution statistics
    simulate <amount>   - Simulate distribution with fake pool amount
    transfer <wallet> <amount> - Manual token transfer (for testing)
"""

import asyncio
import base64
import os
import sys
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from typing import Optional, List

import base58
import httpx

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "backend"))

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from solders.keypair import Keypair
from solders.pubkey import Pubkey
from solders.transaction import Transaction
from solders.system_program import TransferParams, transfer
from solders.message import Message
from solders.instruction import Instruction, AccountMeta
from solders.hash import Hash

from app.config import get_settings, TOKEN_MULTIPLIER, COPPER_DECIMALS
from app.models.models import Distribution, DistributionRecipient, Snapshot, Balance, HoldStreak


def utc_now() -> datetime:
    """Get current UTC time (timezone-aware)."""
    return datetime.now(timezone.utc)


# SPL Token Program ID
TOKEN_PROGRAM_ID = Pubkey.from_string("TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA")
ASSOCIATED_TOKEN_PROGRAM_ID = Pubkey.from_string("ATokenGPvbdGVxr1b2hvZbsiqW5xWH25efTNsLJA8knL")


class DistributionTester:
    """Tests distribution functionality on devnet."""

    def __init__(self):
        self.settings = get_settings()
        self.engine = None
        self.async_session = None

    async def setup(self):
        """Initialize database connection."""
        db_url = self.settings.database_url
        if db_url.startswith("postgres://"):
            db_url = db_url.replace("postgres://", "postgresql+asyncpg://", 1)
        elif db_url.startswith("postgresql://"):
            db_url = db_url.replace("postgresql://", "postgresql+asyncpg://", 1)

        self.engine = create_async_engine(db_url, echo=False)
        self.async_session = sessionmaker(
            self.engine, class_=AsyncSession, expire_on_commit=False
        )

    async def cleanup(self):
        """Close database connection."""
        if self.engine:
            await self.engine.dispose()

    def load_wallet(self) -> Optional[Keypair]:
        """Load wallet from private key."""
        private_key = self.settings.creator_wallet_private_key
        if not private_key:
            print("Error: CREATOR_WALLET_PRIVATE_KEY not set")
            return None

        try:
            secret_bytes = base58.b58decode(private_key)
            return Keypair.from_bytes(secret_bytes)
        except Exception as e:
            print(f"Error loading wallet: {e}")
            return None

    def get_associated_token_address(self, owner: Pubkey, mint: Pubkey) -> Pubkey:
        """Derive associated token account address."""
        seeds = [bytes(owner), bytes(TOKEN_PROGRAM_ID), bytes(mint)]
        pda, _ = Pubkey.find_program_address(seeds, ASSOCIATED_TOKEN_PROGRAM_ID)
        return pda

    async def rpc_call(self, method: str, params: list = None) -> dict:
        """Make RPC call to Solana."""
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                self.settings.helius_rpc_url,
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

    async def get_token_balance(self, wallet: str) -> int:
        """Get token balance for a wallet."""
        if not self.settings.copper_token_mint:
            return 0

        try:
            owner = Pubkey.from_string(wallet)
            mint = Pubkey.from_string(self.settings.copper_token_mint)
            ata = self.get_associated_token_address(owner, mint)

            result = await self.rpc_call("getTokenAccountBalance", [str(ata)])
            if result and "value" in result:
                return int(result["value"]["amount"])
        except Exception:
            pass
        return 0

    async def show_status(self):
        """Show pool status and trigger checks."""
        print("\n=== Pool Status ===\n")

        wallet = self.load_wallet()
        if not wallet:
            return

        # Get pool balance
        pool_balance = await self.get_token_balance(str(wallet.pubkey()))
        pool_formatted = pool_balance / TOKEN_MULTIPLIER

        print(f"  Pool Wallet:    {wallet.pubkey()}")
        print(f"  Token:          {self.settings.copper_token_mint}")
        print(f"  Pool Balance:   {pool_formatted:,.2f} tokens ({pool_balance:,} raw)")

        # Get last distribution
        async with self.async_session() as session:
            result = await session.execute(
                select(Distribution)
                .order_by(Distribution.executed_at.desc())
                .limit(1)
            )
            last_dist = result.scalar_one_or_none()

            if last_dist:
                hours_since = (utc_now() - last_dist.executed_at).total_seconds() / 3600
                print(f"\n  Last Distribution: {last_dist.executed_at}")
                print(f"  Hours Since:       {hours_since:.1f}h")
                print(f"  Recipients:        {last_dist.recipient_count}")
            else:
                print(f"\n  Last Distribution: Never")
                hours_since = None

            # Trigger checks
            print(f"\n  Triggers:")
            threshold_usd = self.settings.distribution_threshold_usd
            max_hours = self.settings.distribution_max_hours

            # Note: Can't get actual USD price easily, so skip threshold check
            print(f"    Threshold:  ${threshold_usd} (unable to check price)")

            time_trigger = hours_since is None or hours_since >= max_hours
            print(f"    Time:       {max_hours}h {'[MET]' if time_trigger else f'[{hours_since:.1f}h elapsed]'}")

    async def calculate_distribution(self, pool_amount: int = None):
        """Calculate distribution without executing."""
        print("\n=== Distribution Calculation ===\n")

        async with self.async_session() as session:
            # Get pool amount
            if pool_amount is None:
                wallet = self.load_wallet()
                if wallet:
                    pool_amount = await self.get_token_balance(str(wallet.pubkey()))

            if not pool_amount or pool_amount <= 0:
                print("  Pool is empty")
                return None

            pool_formatted = pool_amount / TOKEN_MULTIPLIER
            print(f"  Pool Amount: {pool_formatted:,.2f} tokens")

            # Get last distribution time
            result = await session.execute(
                select(Distribution)
                .order_by(Distribution.executed_at.desc())
                .limit(1)
            )
            last_dist = result.scalar_one_or_none()

            end = utc_now()
            if last_dist:
                start = last_dist.executed_at
            else:
                start = end - timedelta(hours=24)

            print(f"  Period:      {start} to {end}")

            # Get eligible wallets with TWAB
            # First, get snapshots in range
            result = await session.execute(
                select(Snapshot)
                .where(Snapshot.snapshot_at >= start)
                .where(Snapshot.snapshot_at <= end)
                .order_by(Snapshot.snapshot_at)
            )
            snapshots = result.scalars().all()

            if len(snapshots) < 2:
                print(f"\n  Error: Need at least 2 snapshots, found {len(snapshots)}")
                print("  Run some snapshots first with: python -m scripts.devnet.test_snapshot take")
                return None

            print(f"  Snapshots:   {len(snapshots)}")

            # Get all wallets with balances
            result = await session.execute(
                select(Balance.wallet_address, func.avg(Balance.balance))
                .where(Balance.snapshot_id.in_([s.id for s in snapshots]))
                .group_by(Balance.wallet_address)
            )
            avg_balances = {row[0]: float(row[1]) for row in result.fetchall()}

            if not avg_balances:
                print("\n  No holders found in snapshots")
                return None

            # Get streaks for multipliers
            result = await session.execute(select(HoldStreak))
            streaks = {s.wallet: s for s in result.scalars().all()}

            # Calculate hash powers
            from app.config import TIER_CONFIG

            hash_powers = []
            for wallet, twab in avg_balances.items():
                streak = streaks.get(wallet)
                tier = streak.current_tier if streak else 1
                multiplier = TIER_CONFIG[tier]["multiplier"]
                hash_power = Decimal(str(twab)) * Decimal(str(multiplier))

                if hash_power > 0:
                    hash_powers.append({
                        "wallet": wallet,
                        "twab": int(twab),
                        "tier": tier,
                        "multiplier": multiplier,
                        "hash_power": hash_power,
                    })

            if not hash_powers:
                print("\n  No wallets with hash power")
                return None

            # Sort by hash power
            hash_powers.sort(key=lambda x: x["hash_power"], reverse=True)
            total_hp = sum(hp["hash_power"] for hp in hash_powers)

            # Calculate shares
            recipients = []
            for hp in hash_powers:
                share_pct = hp["hash_power"] / total_hp
                amount = int(Decimal(pool_amount) * share_pct)

                if amount > 0:
                    recipients.append({
                        **hp,
                        "share_pct": float(share_pct * 100),
                        "amount": amount,
                        "amount_formatted": amount / TOKEN_MULTIPLIER,
                    })

            # Display results
            print(f"\n  Recipients:  {len(recipients)}")
            print(f"  Total HP:    {total_hp:,.2f}")

            print(f"\n  {'#':<4} {'Wallet':<20} {'TWAB':>12} {'Tier':>5} {'Mult':>6} {'Share':>8} {'Amount':>15}")
            print(f"  {'-'*4} {'-'*20} {'-'*12} {'-'*5} {'-'*6} {'-'*8} {'-'*15}")

            for i, r in enumerate(recipients[:20], 1):
                twab_fmt = f"{r['twab'] / TOKEN_MULTIPLIER:,.0f}"
                print(f"  {i:<4} {r['wallet'][:20]:<20} {twab_fmt:>12} {r['tier']:>5} {r['multiplier']:>5}x {r['share_pct']:>7.2f}% {r['amount_formatted']:>14,.2f}")

            if len(recipients) > 20:
                print(f"\n  ... and {len(recipients) - 20} more recipients")

            # Return plan
            return {
                "pool_amount": pool_amount,
                "total_hp": total_hp,
                "recipients": recipients,
            }

    async def execute_distribution(self):
        """Execute distribution with actual token transfers."""
        print("\n=== Executing Distribution ===\n")

        # Calculate distribution
        plan = await self.calculate_distribution()
        if not plan:
            return

        wallet = self.load_wallet()
        if not wallet:
            return

        print(f"\n  Executing transfers...")
        print(f"  This will send tokens to {len(plan['recipients'])} recipients")

        # Confirm
        confirm = input("\n  Proceed? (yes/no): ")
        if confirm.lower() != "yes":
            print("  Cancelled")
            return

        # Record distribution first
        async with self.async_session() as session:
            distribution = Distribution(
                pool_amount=plan["pool_amount"],
                pool_value_usd=Decimal("0"),  # Unknown on devnet
                total_hashpower=plan["total_hp"],
                recipient_count=len(plan["recipients"]),
                trigger_type="manual",
                executed_at=utc_now()
            )
            session.add(distribution)
            await session.flush()

            dist_id = distribution.id
            print(f"\n  Created distribution #{dist_id}")

            # Execute transfers
            successful = 0
            failed = 0

            for r in plan["recipients"]:
                try:
                    print(f"  Transferring {r['amount_formatted']:.2f} to {r['wallet'][:16]}...", end=" ")
                    sig = await self._transfer_tokens(
                        wallet,
                        r["wallet"],
                        r["amount"]
                    )

                    if sig:
                        # Record recipient
                        recipient = DistributionRecipient(
                            distribution_id=dist_id,
                            wallet=r["wallet"],
                            twab=r["twab"],
                            multiplier=Decimal(str(r["multiplier"])),
                            hash_power=r["hash_power"],
                            amount_received=r["amount"],
                            tx_signature=sig
                        )
                        session.add(recipient)
                        successful += 1
                        print(f"OK ({sig[:16]}...)")
                    else:
                        failed += 1
                        print("FAILED")

                except Exception as e:
                    failed += 1
                    print(f"ERROR: {e}")

            await session.commit()

            print(f"\n  Distribution complete!")
            print(f"  Successful: {successful}")
            print(f"  Failed:     {failed}")

    async def _transfer_tokens(
        self,
        from_wallet: Keypair,
        to_wallet: str,
        amount: int
    ) -> Optional[str]:
        """Transfer SPL tokens to a wallet."""
        if not self.settings.copper_token_mint:
            return None

        mint = Pubkey.from_string(self.settings.copper_token_mint)
        to_pubkey = Pubkey.from_string(to_wallet)

        # Get ATAs
        from_ata = self.get_associated_token_address(from_wallet.pubkey(), mint)
        to_ata = self.get_associated_token_address(to_pubkey, mint)

        # Check if to_ata exists, create if not
        try:
            result = await self.rpc_call("getAccountInfo", [str(to_ata)])
            if not result or not result.get("value"):
                # Need to create ATA
                await self._create_ata(from_wallet, to_pubkey, mint)
        except Exception:
            await self._create_ata(from_wallet, to_pubkey, mint)

        # Build transfer instruction
        # SPL Token transfer instruction (3 = Transfer)
        data = bytes([3]) + amount.to_bytes(8, "little")

        transfer_ix = Instruction(
            program_id=TOKEN_PROGRAM_ID,
            accounts=[
                AccountMeta(from_ata, False, True),
                AccountMeta(to_ata, False, True),
                AccountMeta(from_wallet.pubkey(), True, False),
            ],
            data=data
        )

        # Get recent blockhash
        blockhash_result = await self.rpc_call("getLatestBlockhash")
        blockhash = Hash.from_string(blockhash_result["value"]["blockhash"])

        # Build and sign transaction
        msg = Message.new_with_blockhash(
            [transfer_ix],
            from_wallet.pubkey(),
            blockhash
        )
        tx = Transaction.new_unsigned(msg)
        tx.sign([from_wallet], blockhash)

        # Send transaction
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                self.settings.helius_rpc_url,
                json={
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "sendTransaction",
                    "params": [
                        base64.b64encode(bytes(tx)).decode(),
                        {"encoding": "base64"}
                    ]
                }
            )
            result = response.json()

            if "error" in result:
                raise Exception(result["error"])

            return result.get("result")

    async def _create_ata(self, payer: Keypair, owner: Pubkey, mint: Pubkey):
        """Create associated token account."""
        ata = self.get_associated_token_address(owner, mint)

        # Create ATA instruction
        create_ix = Instruction(
            program_id=ASSOCIATED_TOKEN_PROGRAM_ID,
            accounts=[
                AccountMeta(payer.pubkey(), True, True),   # Payer
                AccountMeta(ata, False, True),             # ATA
                AccountMeta(owner, False, False),          # Owner
                AccountMeta(mint, False, False),           # Mint
                AccountMeta(Pubkey.from_string("11111111111111111111111111111111"), False, False),  # System
                AccountMeta(TOKEN_PROGRAM_ID, False, False),
            ],
            data=bytes()
        )

        # Get blockhash and send
        blockhash_result = await self.rpc_call("getLatestBlockhash")
        blockhash = Hash.from_string(blockhash_result["value"]["blockhash"])

        msg = Message.new_with_blockhash([create_ix], payer.pubkey(), blockhash)
        tx = Transaction.new_unsigned(msg)
        tx.sign([payer], blockhash)

        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                self.settings.helius_rpc_url,
                json={
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "sendTransaction",
                    "params": [
                        base64.b64encode(bytes(tx)).decode(),
                        {"encoding": "base64"}
                    ]
                }
            )
            # Wait for confirmation
            await asyncio.sleep(2)

    async def list_distributions(self, limit: int = 10):
        """List recent distributions."""
        print("\n=== Recent Distributions ===\n")

        async with self.async_session() as session:
            result = await session.execute(
                select(Distribution)
                .order_by(Distribution.executed_at.desc())
                .limit(limit)
            )
            distributions = result.scalars().all()

            if not distributions:
                print("  No distributions found")
                return

            print(f"  {'ID':<6} {'Time':<20} {'Recipients':>12} {'Amount':>18} {'Trigger':<10}")
            print(f"  {'-'*6} {'-'*20} {'-'*12} {'-'*18} {'-'*10}")

            for d in distributions:
                time_str = d.executed_at.strftime("%Y-%m-%d %H:%M")
                amount_fmt = f"{d.pool_amount / TOKEN_MULTIPLIER:,.2f}"
                print(f"  {d.id:<6} {time_str:<20} {d.recipient_count:>12} {amount_fmt:>18} {d.trigger_type:<10}")

    async def show_history(self, wallet: str):
        """Show distribution history for a wallet."""
        print(f"\n=== Distribution History: {wallet[:20]}... ===\n")

        async with self.async_session() as session:
            result = await session.execute(
                select(DistributionRecipient, Distribution)
                .join(Distribution)
                .where(DistributionRecipient.wallet == wallet)
                .order_by(Distribution.executed_at.desc())
                .limit(20)
            )
            rows = result.fetchall()

            if not rows:
                print("  No distributions for this wallet")
                return

            total_received = 0

            print(f"  {'Time':<20} {'Amount':>15} {'Share':>10} {'Tier':>6}")
            print(f"  {'-'*20} {'-'*15} {'-'*10} {'-'*6}")

            for recipient, dist in rows:
                time_str = dist.executed_at.strftime("%Y-%m-%d %H:%M")
                amount_fmt = f"{recipient.amount_received / TOKEN_MULTIPLIER:,.2f}"
                share = float(recipient.hash_power / dist.total_hashpower * 100) if dist.total_hashpower else 0
                total_received += recipient.amount_received
                print(f"  {time_str:<20} {amount_fmt:>15} {share:>9.2f}% {int(recipient.multiplier):>5}x")

            print(f"\n  Total received: {total_received / TOKEN_MULTIPLIER:,.2f} tokens")

    async def show_stats(self):
        """Show distribution statistics."""
        print("\n=== Distribution Statistics ===\n")

        async with self.async_session() as session:
            result = await session.execute(
                select(
                    func.count(Distribution.id),
                    func.sum(Distribution.pool_amount),
                    func.sum(Distribution.recipient_count),
                    func.avg(Distribution.recipient_count)
                )
            )
            row = result.one()

            count = row[0] or 0
            total_amount = int(row[1]) if row[1] else 0
            total_recipients = int(row[2]) if row[2] else 0
            avg_recipients = float(row[3]) if row[3] else 0

            print(f"  Total distributions: {count}")
            print(f"  Total distributed:   {total_amount / TOKEN_MULTIPLIER:,.2f} tokens")
            print(f"  Total recipients:    {total_recipients}")
            print(f"  Avg recipients/dist: {avg_recipients:.1f}")

            if count > 0:
                avg_amount = (total_amount / TOKEN_MULTIPLIER) / count
                print(f"  Avg amount/dist:     {avg_amount:,.2f} tokens")


async def main():
    tester = DistributionTester()

    try:
        await tester.setup()

        if len(sys.argv) < 2:
            print(__doc__)
            return

        command = sys.argv[1].lower()

        if command == "status":
            await tester.show_status()

        elif command == "calculate":
            pool_amount = int(sys.argv[2]) if len(sys.argv) > 2 else None
            await tester.calculate_distribution(pool_amount)

        elif command == "execute":
            await tester.execute_distribution()

        elif command == "list":
            limit = int(sys.argv[2]) if len(sys.argv) > 2 else 10
            await tester.list_distributions(limit)

        elif command == "history":
            if len(sys.argv) < 3:
                print("Usage: test_distribution.py history <wallet>")
                return
            await tester.show_history(sys.argv[2])

        elif command == "stats":
            await tester.show_stats()

        elif command == "simulate":
            if len(sys.argv) < 3:
                print("Usage: test_distribution.py simulate <pool_amount>")
                return
            amount = int(float(sys.argv[2]) * TOKEN_MULTIPLIER)
            await tester.calculate_distribution(amount)

        else:
            print(f"Unknown command: {command}")
            print(__doc__)

    finally:
        await tester.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
