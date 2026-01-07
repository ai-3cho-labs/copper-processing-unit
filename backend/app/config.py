"""
$COPPER Backend Configuration

Loads settings from environment variables with sensible defaults.
"""

from functools import lru_cache
from typing import List
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Environment
    environment: str = "development"
    debug: bool = False

    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    cors_origins: str = "http://localhost:3000"

    # Database (Neon PostgreSQL)
    database_url: str = ""

    # Redis (Upstash)
    redis_url: str = ""
    upstash_redis_rest_url: str = ""
    upstash_redis_rest_token: str = ""

    # Helius API
    helius_api_key: str = ""
    helius_webhook_secret: str = ""

    # Solana RPC
    solana_rpc_url: str = ""

    # Wallet Private Keys (Base58 encoded)
    creator_wallet_private_key: str = ""
    buyback_wallet_private_key: str = ""
    airdrop_pool_private_key: str = ""
    team_wallet_public_key: str = ""

    # Token
    copper_token_mint: str = ""

    # Celery
    celery_broker_url: str = ""
    celery_result_backend: str = ""

    # Distribution Settings
    distribution_threshold_usd: float = 250.0
    distribution_max_hours: int = 24
    min_balance_usd: float = 50.0

    # Snapshot Settings
    snapshot_probability: float = 0.4  # 40% chance per hour

    # Monitoring
    sentry_dsn: str = ""

    @property
    def cors_origins_list(self) -> List[str]:
        """Parse CORS origins from comma-separated string."""
        return [origin.strip() for origin in self.cors_origins.split(",")]

    @property
    def is_production(self) -> bool:
        """Check if running in production."""
        return self.environment == "production"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


# Tier configuration
TIER_CONFIG = {
    1: {"name": "Ore", "emoji": "\U0001FAA8", "multiplier": 1.0, "min_hours": 0},
    2: {"name": "Raw Copper", "emoji": "\U0001F536", "multiplier": 1.25, "min_hours": 6},
    3: {"name": "Refined", "emoji": "\u26A1", "multiplier": 1.5, "min_hours": 12},
    4: {"name": "Industrial", "emoji": "\U0001F3ED", "multiplier": 2.5, "min_hours": 72},  # 3 days
    5: {"name": "Master Miner", "emoji": "\U0001F451", "multiplier": 3.5, "min_hours": 168},  # 7 days
    6: {"name": "Diamond Hands", "emoji": "\U0001F48E", "multiplier": 5.0, "min_hours": 720},  # 30 days
}

# Tier thresholds in hours
TIER_THRESHOLDS = {
    1: 0,      # 0 hours
    2: 6,      # 6 hours
    3: 12,     # 12 hours
    4: 72,     # 3 days
    5: 168,    # 7 days
    6: 720,    # 30 days
}

# Solana constants
SOL_MINT = "So11111111111111111111111111111111111111112"
USDC_MINT = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"
LAMPORTS_PER_SOL = 1_000_000_000

# Token decimals (standard SPL token)
COPPER_DECIMALS = 6
TOKEN_MULTIPLIER = 10 ** COPPER_DECIMALS
