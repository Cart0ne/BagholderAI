-- Session 39i: allow anon role to UPDATE trend_config
-- See bug discovered on /tf: Save on "⚠️ TF Safety parameters" showed
-- status "Saved ✓" but the DB value never changed. Root cause: the
-- anon key (used by all web UIs) has SELECT on trend_config but not
-- UPDATE. PostgREST silently returns 200 with an empty array when the
-- row matches the filter but RLS blocks the mutation — no HTTP error,
-- the UI thinks it saved.
--
-- bot_config already allows anon UPDATE (that is how admin.html edits
-- BTC/SOL/BONK params). This migration brings trend_config in line.
--
-- Scope: only UPDATE. SELECT is already open. INSERT and DELETE stay
-- closed — we never add or drop trend_config rows from the UI (it is
-- a singleton row).
--
-- Apply via Supabase SQL editor.

-- Ensure RLS is enabled (should already be the case for any
-- Supabase-managed table; harmless if so).
ALTER TABLE trend_config ENABLE ROW LEVEL SECURITY;

-- Drop any pre-existing policy with the same name to stay idempotent.
DROP POLICY IF EXISTS "trend_config anon update" ON trend_config;

CREATE POLICY "trend_config anon update"
  ON trend_config
  FOR UPDATE
  TO anon
  USING (true)
  WITH CHECK (true);

-- Rollback:
--   DROP POLICY IF EXISTS "trend_config anon update" ON trend_config;
