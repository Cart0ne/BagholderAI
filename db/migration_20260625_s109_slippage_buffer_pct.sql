-- S109 (MASTER 1.5) — per-coin slippage buffer infrastructure.
--
-- Makes the SWEEP / LAST_SHOT buy-cost slippage buffer (brief 78b) tunable
-- per coin instead of the global HardcodedRules.SLIPPAGE_BUFFER_PCT constant.
--
-- UNIT: FRACTION, not percent points (0.03 = 3%), matching the constant and
-- the existing `cost = cash * (1 - slippage_buffer_pct)` math in buy_pipeline.
-- This differs on purpose from the other *_pct columns (buy_pct, sell_pct,
-- stop_buy_drawdown_pct) which are percent points divided by 100 in code.
--
-- Nullable, no default: NULL means "use the grid_bot default" (the constant),
-- so existing rows keep today's behaviour exactly. Board-only static param
-- (microstructure) — NOT in Sherpa's writable whitelist.
--
-- Applied to prod (project BagHolderAI) on 2026-06-25 via apply_migration.
-- Activates only on the next bot restart, when grid_runner reads the new
-- column into _CONFIG_FIELDS; the running process is unaffected.

ALTER TABLE public.bot_config
  ADD COLUMN IF NOT EXISTS slippage_buffer_pct numeric;

COMMENT ON COLUMN public.bot_config.slippage_buffer_pct IS
  'Per-coin slippage buffer as a FRACTION (0.03 = 3%), applied on the SWEEP / LAST SHOT buy cost (brief 78b). NULL => bot falls back to HardcodedRules.SLIPPAGE_BUFFER_PCT (0.03). Board-only static param (microstructure, NOT Sherpa-managed). Added S109 (MASTER 1.5 infra).';
