-- S118 (K.1 Fase 1) — per-row venue for the Kraken cutover.
--
-- NOT NULL DEFAULT 'binance': existing testnet rows keep today's behaviour
-- exactly (invariant S112 — EXCHANGE=binance / venue='binance' = zero diff).
-- Kraken rows will be inserted in Fase 2 with venue='kraken' explicitly;
-- no code path inserts them in Fase 1.
--
-- Decision (Max, 2026-07-11, nodo 1): venue is PER-ROW, not a global process
-- flag. Each grid runner picks its ExchangeClient from its own bot_config row
-- (create_client(venue)); the EXCHANGE env flag remains only as fallback for
-- rows without the column (defensive) and for scripts.
--
-- Consumers updated in Fase 1: grid_runner (client selection), Sherpa
-- (_fetch_active_manual_bots skips kraken rows — BOARD_TABLE would zero the
-- fee-aware floor), TF allocator INSERT/UPDATE (explicit venue='binance'),
-- orchestrator select (telemetry only — spawn stays is_active-driven).
--
-- Applied to prod (project BagHolderAI) on 2026-07-11 via apply_migration.

ALTER TABLE public.bot_config
  ADD COLUMN IF NOT EXISTS venue text NOT NULL DEFAULT 'binance';

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint
    WHERE conname = 'bot_config_venue_check'
      AND conrelid = 'public.bot_config'::regclass
  ) THEN
    ALTER TABLE public.bot_config
      ADD CONSTRAINT bot_config_venue_check
      CHECK (venue IN ('binance', 'kraken'));
  END IF;
END $$;

COMMENT ON COLUMN public.bot_config.venue IS
  'Exchange venue for this row: binance (testnet, default) or kraken (live USD). Selects the ExchangeClient per grid runner (S118, K.1 Fase 1). Sherpa is hands-off on kraken rows until Board enables it post-collaudo.';
