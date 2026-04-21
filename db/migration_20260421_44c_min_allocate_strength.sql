-- Session 44c: TF minimum signal_strength threshold
-- See config/brief_44_nightly_incident.md for the incident context.
-- Observed 2026-04-21 night: 币安人生/USDT was ALLOCATE-d with strength 8.94
-- because the bullish pool was weak and the allocator filled slots
-- indiscriminately. This column gates ALLOCATE on a minimum strength
-- (default 15.0 = typical floor for healthy historical ALLOCATE).
-- Apply via Supabase SQL editor.

ALTER TABLE trend_config
  ADD COLUMN IF NOT EXISTS min_allocate_strength NUMERIC NOT NULL DEFAULT 15.0;

-- Column semantics:
--   min_allocate_strength : below this signal_strength, the TF allocator
--                           SKIPs the candidate with reason
--                           "signal_strength X below min_allocate_strength Y".
--                           Default 15.0 reflects the lower bound of healthy
--                           ALLOCATE decisions observed on 2026-04-20. Set 0
--                           to disable (allocator accepts any bullish).
