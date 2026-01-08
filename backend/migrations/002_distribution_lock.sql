-- ===========================================
-- $COPPER Distribution Lock Table
-- Version: 002
--
-- Fixes Critical Issue #2: Race Condition Double Distribution
-- Adds concurrency control to prevent multiple Celery workers
-- from executing the same distribution simultaneously.
-- ===========================================

-- ===========================================
-- Distribution lock table
-- Single-row table for SELECT FOR UPDATE NOWAIT locking
-- ===========================================
CREATE TABLE IF NOT EXISTS distribution_lock (
    id          INTEGER PRIMARY KEY DEFAULT 1,
    locked_at   TIMESTAMPTZ,
    locked_by   VARCHAR(100),
    updated_at  TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT distribution_lock_single_row CHECK (id = 1)
);

-- Insert initial lock row (required for FOR UPDATE to work)
INSERT INTO distribution_lock (id) VALUES (1) ON CONFLICT DO NOTHING;

COMMENT ON TABLE distribution_lock IS 'Concurrency control for distribution execution (single row, use SELECT FOR UPDATE NOWAIT)';
