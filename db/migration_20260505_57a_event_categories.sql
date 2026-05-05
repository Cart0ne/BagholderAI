-- 57a: extend bot_events_log.category whitelist
--
-- Brief 57a introduces two new event categories that the existing
-- CHECK constraint rejected at runtime:
--   - integrity   → fifo_drift_detected, health_check_run
--   - trade_audit → sell_fifo_detail (forensic per-sell audit trail)
--
-- The boot health check on 2026-05-05 12:37 UTC failed silently because
-- of this — log_event swallows the error by contract, so the bot kept
-- running, but events were not landing. Fix: drop and recreate the
-- constraint with the new values whitelisted.
--
-- Applied via Supabase MCP on 2026-05-05 ~12:42 UTC.

ALTER TABLE bot_events_log DROP CONSTRAINT IF EXISTS bot_events_log_category_check;
ALTER TABLE bot_events_log ADD CONSTRAINT bot_events_log_category_check
  CHECK (category = ANY (ARRAY[
    'lifecycle'::text,
    'trade'::text,
    'safety'::text,
    'tf'::text,
    'config'::text,
    'error'::text,
    'integrity'::text,
    'trade_audit'::text
  ]));
