-- Session 39g: allow NULL symbol in config_changes_log
-- See bug discovered via /tf UI: saving tf_stop_loss_pct or
-- tf_take_profit_pct tries to audit the change with symbol=NULL
-- (the change is on trend_config, a global table — no per-coin symbol).
-- The INSERT was failing with a 23502 NOT NULL constraint violation;
-- the upstream PATCH on trend_config had already succeeded but the
-- user saw "Saved (audit log failed)" and had no audit trail for the
-- change.
--
-- By making symbol nullable we align trend_config edits with the same
-- audit shape used by bot_config edits (symbol, parameter, old_value,
-- new_value, changed_by). Readers (x_poster.get_recent_config_changes)
-- already tolerate a NULL symbol — they just treat it as a global row.
--
-- Apply via Supabase SQL editor.

ALTER TABLE config_changes_log ALTER COLUMN symbol DROP NOT NULL;

-- Rollback:
--   ALTER TABLE config_changes_log ALTER COLUMN symbol SET NOT NULL;
--   -- (fails if any row has symbol=NULL; delete those first.)
