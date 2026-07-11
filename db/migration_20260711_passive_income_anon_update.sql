-- S117 (2026-07-11): allow anon role to UPDATE passive_income
-- The /income page ("The experiment") reads all figures from this table,
-- but until now every change required a manual SQL query. A new
-- "Experiment data" editor at the bottom of admin.html lets Max edit the
-- rows directly; the page picks the new values up on next load.
--
-- Same pattern as trend_config (migration_20260419) and bot_config:
-- client gate on the private dashboard + anon UPDATE policy.
--
-- Scope: only UPDATE. SELECT is already open (public read policy from
-- s100a). INSERT and DELETE stay closed — the UI edits the fixed set of
-- rows (5 cost / 4 revenue / 2 traction), it never adds or drops sources.
-- New sources keep going through a migration.
--
-- Applied to cloud via Supabase MCP on 2026-07-11.

ALTER TABLE passive_income ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "passive_income anon update" ON passive_income;

CREATE POLICY "passive_income anon update"
  ON passive_income
  FOR UPDATE
  TO anon
  USING (true)
  WITH CHECK (true);

-- Rollback:
--   DROP POLICY IF EXISTS "passive_income anon update" ON passive_income;
