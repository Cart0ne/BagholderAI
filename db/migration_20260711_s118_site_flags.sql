-- S118 (K.3 prep) — site_flags: zero-deploy toggles for the public site.
--
-- Single-row table (id=1), same pattern as project_status (Brief 86a): the
-- Astro site reads it client-side with the anon key; flipping a flag is a
-- plain UPDATE, no build/deploy needed. Built for the collaudo windows
-- (COLLAUDO_COMMS_GUIDELINES_v1 Step 1/3): disclaimer_mode=true swaps the
-- homepage content for the disclaimer view; the toggle is reusable across
-- BTC -> SOL -> BONK (parametric disclaimer_text).
--
-- anon = read-only (no public writes: the homepage message must not be
-- defaceable). Writes happen via service key / SQL editor / Supabase MCP.
--
-- Fase 1 ships the toggle OFF (disclaimer_mode=false => zero observable
-- diff on the site). The flip is a Fase 2 runbook step.
--
-- Applied to prod (project BagHolderAI) on 2026-07-11 via apply_migration.

CREATE TABLE IF NOT EXISTS public.site_flags (
  id smallint PRIMARY KEY DEFAULT 1 CHECK (id = 1),
  disclaimer_mode boolean NOT NULL DEFAULT false,
  disclaimer_text text NOT NULL DEFAULT 'We are going live on Kraken to test our bots — stay tuned!',
  updated_at timestamptz NOT NULL DEFAULT now()
);

ALTER TABLE public.site_flags ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "anon read" ON public.site_flags;
CREATE POLICY "anon read" ON public.site_flags
  FOR SELECT TO anon USING (true);

INSERT INTO public.site_flags (id) VALUES (1)
ON CONFLICT (id) DO NOTHING;

COMMENT ON TABLE public.site_flags IS
  'Zero-deploy site toggles (S118, K.3 prep). disclaimer_mode=true swaps the homepage for the disclaimer page during cutover windows (COLLAUDO_COMMS_GUIDELINES_v1 Step 1/3). Reusable across the BTC->SOL->BONK collaudo.';
