-- ===========================================
-- $COPPER Initial Database Schema
-- Version: 001
-- ===========================================

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ===========================================
-- Snapshots table
-- Stores metadata for each balance snapshot
-- ===========================================
CREATE TABLE snapshots (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    timestamp     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    total_holders INTEGER NOT NULL,
    total_supply  BIGINT NOT NULL,
    created_at    TIMESTAMPTZ DEFAULT NOW()
);

-- ===========================================
-- Balances table
-- Stores wallet balances per snapshot (includes compounded airdrops)
-- ===========================================
CREATE TABLE balances (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    snapshot_id UUID REFERENCES snapshots(id) ON DELETE CASCADE,
    wallet      VARCHAR(44) NOT NULL,
    balance     BIGINT NOT NULL,
    CONSTRAINT non_negative_balance CHECK (balance >= 0),
    UNIQUE(snapshot_id, wallet)
);

-- ===========================================
-- Hold streaks table
-- Tracks wallet holding streaks and tiers
-- ===========================================
CREATE TABLE hold_streaks (
    wallet        VARCHAR(44) PRIMARY KEY,
    streak_start  TIMESTAMPTZ NOT NULL,
    current_tier  INTEGER NOT NULL DEFAULT 1,
    last_sell_at  TIMESTAMPTZ,
    updated_at    TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT valid_tier CHECK (current_tier >= 1 AND current_tier <= 6)
);

-- ===========================================
-- Creator rewards tracking
-- Tracks incoming Pump.fun creator rewards
-- ===========================================
CREATE TABLE creator_rewards (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    amount_sol    DECIMAL(18, 9) NOT NULL,
    source        VARCHAR(20) NOT NULL,
    tx_signature  VARCHAR(88),
    received_at   TIMESTAMPTZ NOT NULL,
    processed     BOOLEAN DEFAULT FALSE,
    created_at    TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT positive_amount CHECK (amount_sol > 0),
    CONSTRAINT valid_source CHECK (source IN ('pumpfun', 'pumpswap'))
);

-- ===========================================
-- Buybacks table
-- Records all buyback transactions
-- ===========================================
CREATE TABLE buybacks (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tx_signature  VARCHAR(88) NOT NULL UNIQUE,
    sol_amount    DECIMAL(18, 9) NOT NULL,
    copper_amount BIGINT NOT NULL,
    price_per_token DECIMAL(18, 12),
    executed_at   TIMESTAMPTZ NOT NULL,
    created_at    TIMESTAMPTZ DEFAULT NOW()
);

-- ===========================================
-- Distributions table
-- Records distribution cycles
-- ===========================================
CREATE TABLE distributions (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    pool_amount     BIGINT NOT NULL,
    pool_value_usd  DECIMAL(18, 2),
    total_hashpower DECIMAL(24, 2) NOT NULL,
    recipient_count INTEGER NOT NULL,
    trigger_type    VARCHAR(20) NOT NULL,
    executed_at     TIMESTAMPTZ NOT NULL,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT positive_pool CHECK (pool_amount > 0),
    CONSTRAINT positive_hashpower CHECK (total_hashpower > 0),
    CONSTRAINT positive_recipients CHECK (recipient_count > 0),
    CONSTRAINT valid_trigger CHECK (trigger_type IN ('threshold', 'time'))
);

-- ===========================================
-- Distribution recipients table
-- Records per-wallet distribution details
-- ===========================================
CREATE TABLE distribution_recipients (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    distribution_id UUID REFERENCES distributions(id) ON DELETE CASCADE,
    wallet          VARCHAR(44) NOT NULL,
    twab            BIGINT NOT NULL,
    multiplier      DECIMAL(4, 2) NOT NULL,
    hash_power      DECIMAL(24, 2) NOT NULL,
    amount_received BIGINT NOT NULL,
    tx_signature    VARCHAR(88),
    UNIQUE(distribution_id, wallet)
);

-- ===========================================
-- Excluded wallets table
-- Wallets excluded from distributions (pools, CEX, team, etc.)
-- ===========================================
CREATE TABLE excluded_wallets (
    wallet      VARCHAR(44) PRIMARY KEY,
    reason      VARCHAR(100) NOT NULL,
    added_at    TIMESTAMPTZ DEFAULT NOW()
);

-- ===========================================
-- System stats table
-- Caches computed global statistics
-- ===========================================
CREATE TABLE system_stats (
    id                  INTEGER PRIMARY KEY DEFAULT 1,
    total_holders       INTEGER DEFAULT 0,
    total_volume_24h    DECIMAL(18, 2) DEFAULT 0,
    total_buybacks      DECIMAL(18, 9) DEFAULT 0,
    total_distributed   BIGINT DEFAULT 0,
    last_snapshot_at    TIMESTAMPTZ,
    last_distribution_at TIMESTAMPTZ,
    updated_at          TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT single_row CHECK (id = 1)
);

-- Insert initial stats row
INSERT INTO system_stats (id) VALUES (1) ON CONFLICT DO NOTHING;

-- ===========================================
-- Indexes for performance
-- ===========================================

-- Balances indexes (critical for TWAB queries)
CREATE INDEX idx_balances_wallet ON balances(wallet);
CREATE INDEX idx_balances_snapshot ON balances(snapshot_id);
-- Composite index for TWAB range queries: get all balances for a wallet in time range
CREATE INDEX idx_balances_wallet_snapshot ON balances(wallet, snapshot_id);

-- Snapshot indexes
CREATE INDEX idx_snapshots_timestamp ON snapshots(timestamp DESC);

-- Hold streaks indexes
CREATE INDEX idx_hold_streaks_tier ON hold_streaks(current_tier);
CREATE INDEX idx_hold_streaks_updated ON hold_streaks(updated_at DESC);

-- Buybacks indexes
CREATE INDEX idx_buybacks_executed ON buybacks(executed_at DESC);

-- Creator rewards indexes
CREATE INDEX idx_creator_rewards_processed ON creator_rewards(processed) WHERE processed = FALSE;
CREATE INDEX idx_creator_rewards_received ON creator_rewards(received_at DESC);

-- Distribution indexes
CREATE INDEX idx_distributions_executed ON distributions(executed_at DESC);
CREATE INDEX idx_distribution_recipients_wallet ON distribution_recipients(wallet);
CREATE INDEX idx_distribution_recipients_dist ON distribution_recipients(distribution_id);

-- ===========================================
-- Comments
-- ===========================================
COMMENT ON TABLE snapshots IS 'Balance snapshots taken randomly ~3-6 times per day';
COMMENT ON TABLE balances IS 'Wallet balances at each snapshot point';
COMMENT ON TABLE hold_streaks IS 'Tracks consecutive holding time and tier multipliers';
COMMENT ON TABLE creator_rewards IS 'Incoming Pump.fun creator rewards in SOL';
COMMENT ON TABLE buybacks IS 'Jupiter swap transactions converting SOL to COPPER';
COMMENT ON TABLE distributions IS 'Airdrop distribution cycles';
COMMENT ON TABLE distribution_recipients IS 'Per-wallet distribution records';
COMMENT ON TABLE excluded_wallets IS 'Wallets excluded from distributions (pools, CEX, etc.)';
COMMENT ON TABLE system_stats IS 'Cached global statistics (single row)';

-- ===========================================
-- Data Retention Function
-- Archives old snapshots and balances (run periodically)
-- ===========================================
CREATE OR REPLACE FUNCTION archive_old_snapshots(retention_days INTEGER DEFAULT 90)
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    -- Delete snapshots older than retention period
    -- CASCADE will delete associated balances
    DELETE FROM snapshots
    WHERE timestamp < NOW() - (retention_days || ' days')::INTERVAL;

    GET DIAGNOSTICS deleted_count = ROW_COUNT;

    -- Update system stats
    UPDATE system_stats SET updated_at = NOW() WHERE id = 1;

    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION archive_old_snapshots IS 'Archives snapshots older than specified days (default 90)';

-- ===========================================
-- SCALABILITY NOTES
-- ===========================================
-- For high-volume deployments, consider:
--
-- 1. Table Partitioning (PostgreSQL 12+):
--    Convert snapshots and balances to partitioned tables by month
--
-- 2. Read Replicas:
--    Route read queries to replicas for leaderboard/stats endpoints
--
-- 3. Materialized Views:
--    CREATE MATERIALIZED VIEW mv_leaderboard AS
--    SELECT wallet, SUM(balance) as total, ... FROM balances GROUP BY wallet;
--
-- 4. Connection Pooling:
--    Use PgBouncer or Neon's built-in pooler for high concurrency
-- ==========================================
