-- Session 39c: TF take-profit (fixed %)
-- See config/brief_39c_tf_take_profit.md for design rationale.
-- Symmetric counterpart to 39a stop-loss: same base calculation
-- (unrealized vs capital_allocation × pct), opposite sign. Default
-- 10 → R:R 1:1 with stop-loss at default.
-- Apply via Supabase SQL editor.

ALTER TABLE trend_config
  ADD COLUMN IF NOT EXISTS tf_take_profit_pct NUMERIC NOT NULL DEFAULT 10;

-- Column semantics:
--   tf_take_profit_pct : threshold (% of capital_allocation) of unrealized
--                        profit that triggers all-in liquidation on a TF
--                        bot. Applies only to TF-managed bots, never to
--                        manual. Set to 0 to disable take-profit.
