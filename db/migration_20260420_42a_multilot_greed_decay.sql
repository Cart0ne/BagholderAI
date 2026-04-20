-- Session 42a: Multi-lot entry + Greed decay take-profit
-- See config/brief_42a_multilot_greed_decay.md for design rationale.
-- Applied ahead of code changes (brief 39j hot-reload needs greed_decay_tiers
-- in the SELECT, so the column must exist before the reader polls it).
-- Apply via Supabase SQL editor.

-- 1. Multi-lot entry
ALTER TABLE trend_config
  ADD COLUMN IF NOT EXISTS tf_initial_lots INTEGER NOT NULL DEFAULT 3;

ALTER TABLE bot_config
  ADD COLUMN IF NOT EXISTS initial_lots INTEGER NOT NULL DEFAULT 0;

-- 2. Greed decay take-profit
ALTER TABLE trend_config
  ADD COLUMN IF NOT EXISTS greed_decay_tiers JSONB NOT NULL DEFAULT '[
    {"minutes": 15, "tp_pct": 12},
    {"minutes": 60, "tp_pct": 8},
    {"minutes": 180, "tp_pct": 5},
    {"minutes": 480, "tp_pct": 3},
    {"minutes": 999999, "tp_pct": 1.5}
  ]'::jsonb;

ALTER TABLE bot_config
  ADD COLUMN IF NOT EXISTS allocated_at TIMESTAMPTZ;

-- Column semantics:
--   trend_config.tf_initial_lots   : number of market-buy lots fired on the
--                                    first cycle after a TF ALLOCATE. Written
--                                    by the allocator into bot_config.initial_lots.
--   bot_config.initial_lots        : lots to market-buy on the next cycle.
--                                    Grid bot resets to 0 after firing. Manual
--                                    bots stay at 0 (unaffected).
--   trend_config.greed_decay_tiers : JSON array sorted ascending by minutes.
--                                    Each {minutes, tp_pct} means "after this
--                                    many minutes since allocated_at, use this
--                                    tp_pct as effective take-profit". Last
--                                    entry is the forever fallback.
--   bot_config.allocated_at        : timestamp of the TF ALLOCATE that created
--                                    this row. NULL for manual bots → falls
--                                    back to static profit_target_pct.
