-- Session 39b: Manual bots stop-buy on drawdown
-- See config/brief_39b_manual_stop_buy.md for design rationale
-- (symmetric counterpart to 39a stop-loss: blocks NEW buys when total
-- unrealized loss exceeds threshold; existing lots unaffected; resets
-- event-based on first profitable sell).
-- Apply via Supabase SQL editor.

ALTER TABLE bot_config
  ADD COLUMN IF NOT EXISTS stop_buy_drawdown_pct NUMERIC NOT NULL DEFAULT 15;

-- Backfill is redundant with DEFAULT 15, kept explicit for clarity.
UPDATE bot_config SET stop_buy_drawdown_pct = 15 WHERE stop_buy_drawdown_pct IS NULL;

-- Column semantics:
--   stop_buy_drawdown_pct : threshold (% of capital_allocation) of total
--                           unrealized loss that blocks new buys on manual
--                           bots. Ignored by TF-managed bots (they have
--                           tf_stop_loss_pct). Set to 0 to disable.
