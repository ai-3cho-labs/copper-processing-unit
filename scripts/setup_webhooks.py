#!/usr/bin/env python3
"""
$COPPER Webhook Setup

Manage Helius webhooks for transaction monitoring.

Usage:
    python setup_webhooks.py list
    python setup_webhooks.py create https://api.example.com/webhook/helius
    python setup_webhooks.py delete <webhook_id>
    python setup_webhooks.py delete-all
"""

import argparse
import asyncio
import sys
from typing import Optional

# Add backend to path for imports
sys.path.insert(0, '../backend')

import httpx


def get_helius_api_key() -> Optional[str]:
    """Get Helius API key from environment."""
    try:
        from app.config import get_settings
        settings = get_settings()
        return settings.helius_api_key
    except Exception:
        import os
        return os.environ.get("HELIUS_API_KEY")


def get_copper_token_mint() -> Optional[str]:
    """Get COPPER token mint from environment."""
    try:
        from app.config import get_settings
        settings = get_settings()
        return settings.copper_token_mint
    except Exception:
        import os
        return os.environ.get("COPPER_TOKEN_MINT")


async def list_webhooks():
    """List all registered webhooks."""
    api_key = get_helius_api_key()
    if not api_key:
        print("Error: No Helius API key configured")
        print("Set HELIUS_API_KEY environment variable or configure in .env")
        sys.exit(1)

    url = f"https://api.helius.xyz/v0/webhooks?api-key={api_key}"

    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.get(url)

        if response.status_code != 200:
            print(f"Error: API returned {response.status_code}")
            print(response.text)
            sys.exit(1)

        webhooks = response.json()

    if not webhooks:
        print("No webhooks registered.")
        return

    print(f"\nRegistered Webhooks ({len(webhooks)}):")
    print("=" * 80)

    for webhook in webhooks:
        webhook_id = webhook.get("webhookID", "unknown")
        webhook_url = webhook.get("webhookURL", "unknown")
        webhook_type = webhook.get("webhookType", "unknown")
        tx_types = webhook.get("transactionTypes", [])
        account_addresses = webhook.get("accountAddresses", [])

        print(f"\nID: {webhook_id}")
        print(f"  URL: {webhook_url}")
        print(f"  Type: {webhook_type}")
        print(f"  Transaction Types: {', '.join(tx_types) if tx_types else 'all'}")
        print(f"  Accounts: {len(account_addresses)} address(es)")

        if account_addresses:
            for addr in account_addresses[:3]:  # Show first 3
                print(f"    - {addr}")
            if len(account_addresses) > 3:
                print(f"    ... and {len(account_addresses) - 3} more")

    print("\n" + "=" * 80)


async def create_webhook(webhook_url: str):
    """Create a new webhook."""
    api_key = get_helius_api_key()
    if not api_key:
        print("Error: No Helius API key configured")
        sys.exit(1)

    token_mint = get_copper_token_mint()
    if not token_mint:
        print("Error: No COPPER_TOKEN_MINT configured")
        sys.exit(1)

    # Validate URL
    if not webhook_url.startswith("https://"):
        print("Error: Webhook URL must use HTTPS")
        sys.exit(1)

    url = f"https://api.helius.xyz/v0/webhooks?api-key={api_key}"

    # Create webhook for TRANSFER events on the COPPER token
    payload = {
        "webhookURL": webhook_url,
        "webhookType": "enhanced",
        "transactionTypes": ["TRANSFER"],
        "accountAddresses": [token_mint],
    }

    print(f"Creating webhook...")
    print(f"  URL: {webhook_url}")
    print(f"  Token: {token_mint}")

    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(url, json=payload)

        if response.status_code not in (200, 201):
            print(f"\nError: API returned {response.status_code}")
            print(response.text)
            sys.exit(1)

        result = response.json()

    webhook_id = result.get("webhookID", "unknown")
    print(f"\nWebhook created successfully!")
    print(f"  ID: {webhook_id}")


async def delete_webhook(webhook_id: str):
    """Delete a specific webhook."""
    api_key = get_helius_api_key()
    if not api_key:
        print("Error: No Helius API key configured")
        sys.exit(1)

    url = f"https://api.helius.xyz/v0/webhooks/{webhook_id}?api-key={api_key}"

    print(f"Deleting webhook: {webhook_id}")

    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.delete(url)

        if response.status_code == 404:
            print(f"Error: Webhook not found: {webhook_id}")
            sys.exit(1)

        if response.status_code not in (200, 204):
            print(f"Error: API returned {response.status_code}")
            print(response.text)
            sys.exit(1)

    print("Webhook deleted successfully!")


async def delete_all_webhooks():
    """Delete all webhooks after confirmation."""
    api_key = get_helius_api_key()
    if not api_key:
        print("Error: No Helius API key configured")
        sys.exit(1)

    # First, list all webhooks
    list_url = f"https://api.helius.xyz/v0/webhooks?api-key={api_key}"

    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.get(list_url)

        if response.status_code != 200:
            print(f"Error: API returned {response.status_code}")
            sys.exit(1)

        webhooks = response.json()

    if not webhooks:
        print("No webhooks to delete.")
        return

    print(f"\nFound {len(webhooks)} webhook(s):")
    for webhook in webhooks:
        print(f"  - {webhook.get('webhookID')}: {webhook.get('webhookURL')}")

    # Confirm deletion
    confirm = input(f"\nAre you sure you want to delete ALL {len(webhooks)} webhook(s)? [y/N] ")
    if confirm.lower() != 'y':
        print("Cancelled.")
        return

    # Delete each webhook
    async with httpx.AsyncClient(timeout=30) as client:
        for webhook in webhooks:
            webhook_id = webhook.get("webhookID")
            delete_url = f"https://api.helius.xyz/v0/webhooks/{webhook_id}?api-key={api_key}"

            response = await client.delete(delete_url)
            if response.status_code in (200, 204):
                print(f"  Deleted: {webhook_id}")
            else:
                print(f"  Failed to delete: {webhook_id}")

    print("\nAll webhooks deleted!")


async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="$COPPER Webhook Setup - Manage Helius webhooks"
    )
    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # list command
    subparsers.add_parser("list", help="List all registered webhooks")

    # create command
    create_parser = subparsers.add_parser("create", help="Create a new webhook")
    create_parser.add_argument("url", help="Webhook URL (must be HTTPS)")

    # delete command
    delete_parser = subparsers.add_parser("delete", help="Delete a webhook")
    delete_parser.add_argument("webhook_id", help="Webhook ID to delete")

    # delete-all command
    subparsers.add_parser("delete-all", help="Delete all webhooks")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    if args.command == "list":
        await list_webhooks()
    elif args.command == "create":
        await create_webhook(args.url)
    elif args.command == "delete":
        await delete_webhook(args.webhook_id)
    elif args.command == "delete-all":
        await delete_all_webhooks()


if __name__ == "__main__":
    asyncio.run(main())
