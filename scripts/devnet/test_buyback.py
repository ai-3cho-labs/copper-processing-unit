#!/usr/bin/env python3
"""
Devnet Buyback Test

Tests Jupiter swap execution on devnet.

Usage:
    python -m scripts.devnet.test_buyback [command]

Commands:
    quote <amount>      - Get Jupiter quote for SOL → Token swap
    execute <amount>    - Execute swap on devnet (requires funded wallet)
    record <amount>     - Record a simulated buyback in DB
    list                - List recent buybacks
    stats               - Show buyback statistics
    add-reward <amount> - Add simulated creator reward
    rewards             - List pending creator rewards
    process             - Process pending rewards (full flow)
"""

import asyncio
import base64
import os
import sys
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Optional

import base58
import httpx

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "backend"))

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from solders.keypair import Keypair
from solders.transaction import VersionedTransaction
from solders.commitment_config import CommitmentLevel

from app.config import get_settings, LAMPORTS_PER_SOL, SOL_MINT
from app.models.models import Buyback, CreatorReward, SystemStats


def utc_now() -> datetime:
    """Get current UTC time (timezone-aware)."""
    return datetime.now(timezone.utc)


class BuybackTester:
    """Tests buyback functionality on devnet."""

    def __init__(self):
        self.settings = get_settings()
        self.engine = None
        self.async_session = None
        self.jupiter_quote_api = "https://quote-api.jup.ag/v6/quote"
        self.jupiter_swap_api = "https://quote-api.jup.ag/v6/swap"

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

    async def get_quote(self, sol_amount: float) -> Optional[dict]:
        """Get Jupiter quote for swap."""
        print(f"\n=== Getting Jupiter Quote ===\n")

        if not self.settings.copper_token_mint:
            print("Error: COPPER_TOKEN_MINT not set")
            return None

        lamports = int(sol_amount * LAMPORTS_PER_SOL)
        print(f"  Input:  {sol_amount} SOL ({lamports:,} lamports)")
        print(f"  Output: {self.settings.copper_token_mint[:16]}...")

        async with httpx.AsyncClient(timeout=30) as client:
            try:
                response = await client.get(
                    self.jupiter_quote_api,
                    params={
                        "inputMint": SOL_MINT,
                        "outputMint": self.settings.copper_token_mint,
                        "amount": str(lamports),
                        "slippageBps": 100,  # 1% slippage
                    }
                )

                if response.status_code != 200:
                    print(f"  Error: {response.status_code} - {response.text}")
                    return None

                quote = response.json()

                # Parse output
                out_amount = int(quote.get("outAmount", 0))
                decimals = self.settings.copper_token_decimals
                token_amount = out_amount / (10 ** decimals)

                print(f"\n  Quote received:")
                print(f"    Output: {token_amount:,.2f} tokens")
                print(f"    Price:  {sol_amount / token_amount:.10f} SOL/token")
                print(f"    Route:  {len(quote.get('routePlan', []))} hops")

                # Show price impact
                price_impact = float(quote.get("priceImpactPct", 0))
                print(f"    Impact: {price_impact:.4f}%")

                return quote

            except Exception as e:
                print(f"  Error: {e}")
                return None

    async def execute_swap(self, sol_amount: float) -> Optional[str]:
        """Execute Jupiter swap on devnet."""
        print(f"\n=== Executing Swap ===\n")

        wallet = self.load_wallet()
        if not wallet:
            return None

        print(f"  Wallet: {wallet.pubkey()}")
        print(f"  Amount: {sol_amount} SOL")
        print(f"  Network: {self.settings.solana_network}")

        # Get quote
        quote = await self.get_quote(sol_amount)
        if not quote:
            return None

        # Get swap transaction
        async with httpx.AsyncClient(timeout=30) as client:
            try:
                print("\n  Getting swap transaction...")
                response = await client.post(
                    self.jupiter_swap_api,
                    json={
                        "quoteResponse": quote,
                        "userPublicKey": str(wallet.pubkey()),
                        "wrapAndUnwrapSol": True,
                        "dynamicComputeUnitLimit": True,
                        "prioritizationFeeLamports": "auto"
                    }
                )

                if response.status_code != 200:
                    print(f"  Error: {response.status_code} - {response.text}")
                    return None

                swap_data = response.json()
                swap_tx_b64 = swap_data.get("swapTransaction")

                if not swap_tx_b64:
                    print("  Error: No swap transaction returned")
                    return None

                # Decode and sign transaction
                print("  Signing transaction...")
                tx_bytes = base64.b64decode(swap_tx_b64)
                tx = VersionedTransaction.from_bytes(tx_bytes)

                # Sign with wallet
                signed_tx = VersionedTransaction(tx.message, [wallet])

                # Send transaction
                print("  Sending transaction...")
                rpc_url = self.settings.helius_rpc_url

                send_response = await client.post(
                    rpc_url,
                    json={
                        "jsonrpc": "2.0",
                        "id": 1,
                        "method": "sendTransaction",
                        "params": [
                            base64.b64encode(bytes(signed_tx)).decode(),
                            {
                                "encoding": "base64",
                                "skipPreflight": False,
                                "preflightCommitment": "confirmed",
                                "maxRetries": 3
                            }
                        ]
                    }
                )

                result = send_response.json()

                if "error" in result:
                    print(f"  Error: {result['error']}")
                    return None

                signature = result.get("result")
                print(f"\n  Transaction sent!")
                print(f"  Signature: {signature}")
                print(f"  Explorer:  https://solscan.io/tx/{signature}?cluster=devnet")

                # Wait for confirmation
                print("\n  Waiting for confirmation...")
                confirmed = await self._confirm_transaction(client, rpc_url, signature)

                if confirmed:
                    print("  Transaction confirmed!")

                    # Record in database
                    out_amount = int(quote.get("outAmount", 0))
                    await self._record_buyback(
                        signature,
                        Decimal(str(sol_amount)),
                        out_amount
                    )
                else:
                    print("  Warning: Transaction may not be confirmed")

                return signature

            except Exception as e:
                print(f"  Error: {e}")
                import traceback
                traceback.print_exc()
                return None

    async def _confirm_transaction(
        self,
        client: httpx.AsyncClient,
        rpc_url: str,
        signature: str,
        max_retries: int = 30
    ) -> bool:
        """Wait for transaction confirmation."""
        for i in range(max_retries):
            try:
                response = await client.post(
                    rpc_url,
                    json={
                        "jsonrpc": "2.0",
                        "id": 1,
                        "method": "getSignatureStatuses",
                        "params": [[signature]]
                    }
                )
                result = response.json()
                statuses = result.get("result", {}).get("value", [])

                if statuses and statuses[0]:
                    status = statuses[0]
                    if status.get("confirmationStatus") in ["confirmed", "finalized"]:
                        return True
                    if status.get("err"):
                        print(f"  Transaction failed: {status['err']}")
                        return False

            except Exception:
                pass

            await asyncio.sleep(1)

        return False

    async def _record_buyback(
        self,
        signature: str,
        sol_amount: Decimal,
        copper_amount: int
    ):
        """Record buyback in database."""
        async with self.async_session() as session:
            price_per_token = None
            if copper_amount > 0:
                price_per_token = sol_amount / Decimal(copper_amount)

            buyback = Buyback(
                tx_signature=signature,
                sol_amount=sol_amount,
                copper_amount=copper_amount,
                price_per_token=price_per_token,
                executed_at=utc_now()
            )
            session.add(buyback)
            await session.commit()
            print(f"\n  Recorded buyback in database")

    async def record_simulated(self, sol_amount: float):
        """Record a simulated buyback (for testing without actual swap)."""
        print(f"\n=== Recording Simulated Buyback ===\n")

        # Generate fake signature
        import secrets
        fake_sig = base58.b58encode(secrets.token_bytes(64)).decode()

        # Estimate tokens (assuming some price)
        estimated_tokens = int(sol_amount * 1_000_000)  # Fake 1M tokens per SOL

        async with self.async_session() as session:
            buyback = Buyback(
                tx_signature=fake_sig,
                sol_amount=Decimal(str(sol_amount)),
                copper_amount=estimated_tokens,
                price_per_token=Decimal(str(sol_amount)) / Decimal(estimated_tokens),
                executed_at=utc_now()
            )
            session.add(buyback)
            await session.commit()

            print(f"  Recorded simulated buyback:")
            print(f"    Signature: {fake_sig[:32]}...")
            print(f"    SOL:       {sol_amount}")
            print(f"    Tokens:    {estimated_tokens:,}")

    async def list_buybacks(self, limit: int = 10):
        """List recent buybacks."""
        print(f"\n=== Recent Buybacks ===\n")

        async with self.async_session() as session:
            result = await session.execute(
                select(Buyback)
                .order_by(Buyback.executed_at.desc())
                .limit(limit)
            )
            buybacks = result.scalars().all()

            if not buybacks:
                print("  No buybacks found")
                return

            print(f"  {'Time':<20} {'SOL':>12} {'Tokens':>15} {'Price':>15}")
            print(f"  {'-'*20} {'-'*12} {'-'*15} {'-'*15}")

            for b in buybacks:
                time_str = b.executed_at.strftime("%Y-%m-%d %H:%M")
                price = f"{float(b.price_per_token):.10f}" if b.price_per_token else "N/A"
                print(f"  {time_str:<20} {float(b.sol_amount):>12.4f} {b.copper_amount:>15,} {price:>15}")

    async def show_stats(self):
        """Show buyback statistics."""
        print(f"\n=== Buyback Statistics ===\n")

        async with self.async_session() as session:
            # Total buybacks
            result = await session.execute(
                select(
                    func.count(Buyback.id),
                    func.sum(Buyback.sol_amount),
                    func.sum(Buyback.copper_amount)
                )
            )
            row = result.one()
            count = row[0] or 0
            total_sol = float(row[1]) if row[1] else 0
            total_tokens = int(row[2]) if row[2] else 0

            print(f"  Total buybacks:  {count}")
            print(f"  Total SOL spent: {total_sol:.4f}")
            print(f"  Total tokens:    {total_tokens:,}")

            if count > 0:
                avg_sol = total_sol / count
                avg_tokens = total_tokens / count
                print(f"\n  Avg SOL/buyback: {avg_sol:.4f}")
                print(f"  Avg tokens/buyback: {avg_tokens:,.0f}")

            # Pending rewards
            result = await session.execute(
                select(func.sum(CreatorReward.amount_sol))
                .where(CreatorReward.processed == False)
            )
            pending = float(result.scalar_one_or_none() or 0)
            print(f"\n  Pending rewards: {pending:.4f} SOL")

    async def add_reward(self, amount: float):
        """Add a simulated creator reward."""
        print(f"\n=== Adding Creator Reward ===\n")

        import secrets
        fake_sig = base58.b58encode(secrets.token_bytes(64)).decode()

        async with self.async_session() as session:
            reward = CreatorReward(
                amount_sol=Decimal(str(amount)),
                source="devnet_test",
                tx_signature=fake_sig,
                received_at=utc_now()
            )
            session.add(reward)
            await session.commit()

            print(f"  Added reward: {amount} SOL")
            print(f"  Signature: {fake_sig[:32]}...")

    async def list_rewards(self):
        """List pending creator rewards."""
        print(f"\n=== Pending Creator Rewards ===\n")

        async with self.async_session() as session:
            result = await session.execute(
                select(CreatorReward)
                .where(CreatorReward.processed == False)
                .order_by(CreatorReward.received_at.desc())
            )
            rewards = result.scalars().all()

            if not rewards:
                print("  No pending rewards")
                return

            total = sum(float(r.amount_sol) for r in rewards)

            print(f"  {'Time':<20} {'Amount':>12} {'Source':<15}")
            print(f"  {'-'*20} {'-'*12} {'-'*15}")

            for r in rewards:
                time_str = r.received_at.strftime("%Y-%m-%d %H:%M")
                print(f"  {time_str:<20} {float(r.amount_sol):>12.4f} {r.source:<15}")

            print(f"\n  Total pending: {total:.4f} SOL")
            print(f"  Buyback (80%): {total * 0.8:.4f} SOL")
            print(f"  Team (20%):    {total * 0.2:.4f} SOL")

    async def process_rewards(self):
        """Process all pending rewards (full buyback flow)."""
        print(f"\n=== Processing Rewards ===\n")

        async with self.async_session() as session:
            # Get pending rewards
            result = await session.execute(
                select(CreatorReward)
                .where(CreatorReward.processed == False)
            )
            rewards = list(result.scalars().all())

            if not rewards:
                print("  No pending rewards to process")
                return

            total_sol = sum(float(r.amount_sol) for r in rewards)
            buyback_sol = total_sol * 0.8
            team_sol = total_sol * 0.2

            print(f"  Rewards: {len(rewards)}")
            print(f"  Total:   {total_sol:.4f} SOL")
            print(f"  Buyback: {buyback_sol:.4f} SOL (80%)")
            print(f"  Team:    {team_sol:.4f} SOL (20%)")

            # Execute buyback
            print(f"\n  Executing buyback...")
            signature = await self.execute_swap(buyback_sol)

            if signature:
                # Mark rewards as processed
                for r in rewards:
                    r.processed = True
                await session.commit()
                print(f"\n  Marked {len(rewards)} rewards as processed")
            else:
                print(f"\n  Buyback failed - rewards not marked as processed")


async def main():
    tester = BuybackTester()

    try:
        await tester.setup()

        if len(sys.argv) < 2:
            print(__doc__)
            return

        command = sys.argv[1].lower()

        if command == "quote":
            if len(sys.argv) < 3:
                print("Usage: test_buyback.py quote <sol_amount>")
                return
            await tester.get_quote(float(sys.argv[2]))

        elif command == "execute":
            if len(sys.argv) < 3:
                print("Usage: test_buyback.py execute <sol_amount>")
                return
            await tester.execute_swap(float(sys.argv[2]))

        elif command == "record":
            if len(sys.argv) < 3:
                print("Usage: test_buyback.py record <sol_amount>")
                return
            await tester.record_simulated(float(sys.argv[2]))

        elif command == "list":
            limit = int(sys.argv[2]) if len(sys.argv) > 2 else 10
            await tester.list_buybacks(limit)

        elif command == "stats":
            await tester.show_stats()

        elif command == "add-reward":
            if len(sys.argv) < 3:
                print("Usage: test_buyback.py add-reward <sol_amount>")
                return
            await tester.add_reward(float(sys.argv[2]))

        elif command == "rewards":
            await tester.list_rewards()

        elif command == "process":
            await tester.process_rewards()

        else:
            print(f"Unknown command: {command}")
            print(__doc__)

    finally:
        await tester.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
