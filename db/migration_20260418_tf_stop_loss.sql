-- Session 39a: TF stop-loss + faster scan cadence
-- See config/brief_39a_tf_stop_loss.md for design rationale (MOVR zombie trap).
-- Apply via Supabase SQL editor.

ALTER TABLE trend_config
  ADD COLUMN IF NOT EXISTS tf_stop_loss_pct NUMERIC NOT NULL DEFAULT 10;

-- Drop scan cadence from 4h to 1h so BEARISH classification + stop-loss
-- reactions happen faster. Telegram report frequency inherits (4× more
-- reports/day — acceptable per CEO until proven noisy).
UPDATE trend_config SET scan_interval_hours = 1;

-- Column semantics:
--   tf_stop_loss_pct : max unrealized loss (% of capital_allocation) a TF
--                      bot can sit on before liquidating all lots. Default 10.
--                      Set to 0 to disable stop-loss entirely.
