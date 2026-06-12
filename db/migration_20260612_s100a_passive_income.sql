-- S100a / S104 (2026-06-12) — passive_income table for the public /income page.
-- Mirror of the migrations applied to the cloud via Supabase MCP
-- (s100a_passive_income + s100a_passive_income_add_cost_block). Final state.
-- One row per source; blocks: revenue / traction / cost. Filled manually via
-- SQL at launch (pattern project_status); a Mac Mini job can later UPDATE rows
-- by source_key (method='auto') without the frontend changing. value_num is
-- normalized to EUR for revenue/cost.

create table if not exists public.passive_income (
  id            bigint generated always as identity primary key,
  block         text not null check (block in ('revenue','traction','cost')),
  source_key    text not null unique,
  label         text not null,
  value_num     numeric,
  value_display text not null,
  detail        text,
  is_status     boolean not null default false,
  method        text not null default 'manual' check (method in ('auto','manual')),
  sort_order    int not null default 0,
  updated_at    timestamptz not null default now()
);

alter table public.passive_income enable row level security;

drop policy if exists "passive_income public read" on public.passive_income;
create policy "passive_income public read"
  on public.passive_income
  for select
  using (true);

comment on table public.passive_income is
  'S100a — public /income page. One row per revenue/traction/cost source. method=manual rows edited via SQL; method=auto rows updated by Mac Mini job (umami/payhip/bmc). value_num normalized to EUR.';

-- Seed (launch state, 2026-06-12). EUR values; $ shown frontend-side @ ~1.11.
insert into public.passive_income
  (block, source_key, label, value_num, value_display, detail, is_status, method, sort_order)
values
  ('revenue', 'payhip_books', 'Books (Payhip)',        0,   '€0', '0 sales',                     false, 'manual', 1),
  ('revenue', 'bmc_tips',     'Tips (Buy Me a Coffee)', 0,   '€0', '0 supporters',                false, 'manual', 2),
  ('revenue', 'aads',         'Ads (A-ADS)',            0,   '€0', '0% fill',                      false, 'manual', 3),
  ('revenue', 'trading',      'Trading',                null,'waiting to go live', 'still on testnet', true, 'manual', 4),
  ('traction','umami_visits', 'Site visits',            575, '~575', 'Umami · last 30d',          false, 'manual', 1),
  ('traction','payhip_views', 'Book views',             150, '150',  'Payhip dashboard · 6 months', false, 'manual', 2),
  ('cost',    'claude_max',   'Claude Max',             270, '€270', '$100/mo · 3 months',        false, 'manual', 1),
  ('cost',    'haiku_api',    'Haiku API',              1.60,'€1.60','NewsKeeper + commentary',    false, 'manual', 2),
  ('cost',    'grok_api',     'Grok API',               1.00,'€1.00','experiments',               false, 'manual', 3),
  ('cost',    'domain',       'Domain',                 1.40,'€1.40','Porkbun · bagholderai.lol',  false, 'manual', 4),
  ('cost',    'infra',        'Infra',                  0,   '€0',   'Supabase · Vercel · Umami — free tier', false, 'manual', 5)
on conflict (source_key) do nothing;
