-- Session 36g Phase 2: TF compounding policy parameters
-- All 4 values approved by CEO (see config/brief_36g_phase2_ceo_questions.md).
-- Applied to production DB on 2026-04-17.

ALTER TABLE trend_config
  ADD COLUMN IF NOT EXISTS tf_lots_per_coin INTEGER NOT NULL DEFAULT 4,
  ADD COLUMN IF NOT EXISTS tf_sanity_cap_usd NUMERIC NOT NULL DEFAULT 300,
  ADD COLUMN IF NOT EXISTS tf_resize_threshold_usd NUMERIC NOT NULL DEFAULT 10,
  ADD COLUMN IF NOT EXISTS tf_capital_per_trade_cap_usd NUMERIC NOT NULL DEFAULT 50;

-- Column semantics:
--   tf_lots_per_coin              : number of buy levels per active TF coin (4 = granular)
--   tf_sanity_cap_usd             : hard cap on effective TF budget (3x nominal, raise via DB when needed)
--   tf_resize_threshold_usd       : minimum |target − current| delta that triggers a resize UPDATE
--   tf_capital_per_trade_cap_usd  : absolute maximum USD per single buy (over-concentration guard)
