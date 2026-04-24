-- Session 45f: TF Profit Lock Exit
-- See config/brief_45f_profit_lock_exit.md for design rationale.
-- Proactive exit when net PnL (realized + unrealized) exceeds threshold,
-- so the TF crystallises gains before the market takes them back.
--
-- Implemented inside grid_bot (not the TF loop) as a sibling of stop-loss
-- (39a) and take-profit (39c): same managed_by=='trend_follower' gate,
-- live current_price, same pending_liquidation → grid_runner cleanup path.
-- Apply via Supabase SQL editor.

ALTER TABLE trend_config
  ADD COLUMN IF NOT EXISTS tf_profit_lock_enabled BOOLEAN NOT NULL DEFAULT false,
  ADD COLUMN IF NOT EXISTS tf_profit_lock_pct NUMERIC NOT NULL DEFAULT 5;

-- Column semantics:
--   tf_profit_lock_enabled : opt-in master switch. When false, the check is
--                            skipped regardless of pct. Default false so the
--                            feature does not activate on deploy.
--   tf_profit_lock_pct     : threshold (% of capital_allocation) of NET PnL
--                            (realized_pnl + unrealized_pnl) that triggers
--                            all-in liquidation on a TF bot. Applies only to
--                            TF-managed bots, never to manual.
--                            Default 5 — conservative, tune from dashboard.
