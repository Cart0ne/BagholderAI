-- S96a: testnet clean slate via `cycle` tagging (NON-destructive)
--
-- The Binance testnet performs a monthly balance reset that wiped the
-- grid wallets (BONK 21.6M -> 18,446, etc.). Instead of rebasing the DB
-- down to the reset wallet (which deletes a month of accumulation) or
-- rebuilding the position, the Board+CEO chose a clean slate (Opzione C):
-- tag the closed cycle as `testnet_1` and start fresh as `testnet_2`,
-- WITHOUT deleting a single historical row. Old data stays queryable
-- (filter `cycle = 'testnet_1'`); the bot replay, reserve accounting and
-- the public dashboards read only the current cycle.
--
-- Source of truth for "current cycle" = bot_config.cycle (per grid row,
-- all three uniform). Read by the bot via get_current_cycle() and by the
-- dashboards directly. Next monthly reset = a single UPDATE here, no code.
--
-- Brief:  config/2026-06-04_S96a_brief_clean-slate-testnet.md
-- Report: report_for_CEO/2026-06-04_s96_bonk-testnet-reset-decision_report_for_ceo.md
-- Scope extended to reserve_ledger / daily_pnl / bot_state_snapshots
-- (beyond the brief's `trades`-only) after CC objection — CEO approved
-- 2026-06-04: trades-only would leave stale reserve in cash + pre-reset
-- numbers on the dashboards.
--
-- Applied via Supabase MCP on 2026-06-04 (project pxdhtmqfwjwjhtcoacsn).

-- 1. Add the cycle label. NOT NULL DEFAULT backfills every existing row
--    to 'testnet_1' atomically. Idempotent (IF NOT EXISTS).
ALTER TABLE trades              ADD COLUMN IF NOT EXISTS cycle TEXT NOT NULL DEFAULT 'testnet_1';
ALTER TABLE daily_pnl           ADD COLUMN IF NOT EXISTS cycle TEXT NOT NULL DEFAULT 'testnet_1';
ALTER TABLE bot_state_snapshots ADD COLUMN IF NOT EXISTS cycle TEXT NOT NULL DEFAULT 'testnet_1';
ALTER TABLE reserve_ledger      ADD COLUMN IF NOT EXISTS cycle TEXT NOT NULL DEFAULT 'testnet_1';
ALTER TABLE bot_config          ADD COLUMN IF NOT EXISTS cycle TEXT NOT NULL DEFAULT 'testnet_1';

-- 2. Open the new cycle for the 3 grid bots. Their pre-reset trades,
--    snapshots, daily_pnl rows and reserve entries stay tagged testnet_1
--    and drop out of every current-cycle query automatically.
UPDATE bot_config SET cycle = 'testnet_2' WHERE managed_by = 'grid';

-- 3. Indexes for the new filter (hot path: boot replay + dashboards).
CREATE INDEX IF NOT EXISTS idx_trades_cycle              ON trades (cycle);
CREATE INDEX IF NOT EXISTS idx_bot_state_snapshots_cycle ON bot_state_snapshots (cycle);
CREATE INDEX IF NOT EXISTS idx_reserve_ledger_cycle      ON reserve_ledger (cycle);
