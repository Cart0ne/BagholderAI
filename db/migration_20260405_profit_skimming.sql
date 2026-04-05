-- ============================================================
-- BagHolderAI - Migration: Profit Skimming (Session 20b)
-- Run this in the Supabase SQL Editor.
-- ============================================================

-- 1. Add skim_pct to bot_config
--    Default 0 = disabled. Activate per-bot from the admin dashboard.
ALTER TABLE bot_config
  ADD COLUMN IF NOT EXISTS skim_pct NUMERIC DEFAULT 0;

-- Set default value for all existing rows
UPDATE bot_config SET skim_pct = 0 WHERE skim_pct IS NULL;

-- 2. Create reserve_ledger table
CREATE TABLE IF NOT EXISTS reserve_ledger (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at    TIMESTAMPTZ      NOT NULL DEFAULT now(),
    symbol        TEXT             NOT NULL,
    amount        NUMERIC          NOT NULL,
    trade_id      UUID             REFERENCES trades(id),
    config_version TEXT            NOT NULL DEFAULT 'v3'
);

CREATE INDEX IF NOT EXISTS idx_reserve_symbol
    ON reserve_ledger (symbol, config_version);

-- 3. Convenience view: total reserve per symbol
CREATE OR REPLACE VIEW v_reserve_totals AS
SELECT
    symbol,
    config_version,
    SUM(amount) AS total_reserve,
    COUNT(*)    AS skim_count
FROM reserve_ledger
GROUP BY symbol, config_version;
