-- S132 (brief S131a zona-morta-regola, Board S131 2026-09-28)
-- dead_zone_hours = 0 now means "dead zone off" (grid_bot DEAD ZONE block skips
-- when <= 0). Sherpa writes 0 in neutral / greed / extreme_greed.
-- The old CHECK (> 0) rejected that value. Only the lower bound changes.
-- Rollback: put back "dead_zone_hours > 0" (first set any 0 back to 2).

ALTER TABLE public.bot_config DROP CONSTRAINT bot_config_dead_zone_hours_check;
ALTER TABLE public.bot_config ADD CONSTRAINT bot_config_dead_zone_hours_check
  CHECK (dead_zone_hours >= 0 AND dead_zone_hours <= 168);
