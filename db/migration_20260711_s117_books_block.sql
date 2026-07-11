-- S117 (2026-07-11) — mirror of cloud migration s117_books_block_and_data_refresh.
-- Per-volume book views become DB rows (new 'books' block) so the /income
-- "Attention by book" donut is editable from the admin "Experiment data"
-- panel like everything else (no more hardcoded BOOK_VIEWS in income.ts).
-- Plus data refresh decided with Max 2026-07-11:
--   · payhip_views renamed "Store views" (272 = whole-store daily views,
--     cumulative) — the per-book number lives in the books rows (25+69+39);
--   · umami_visits display fixed to English thousands separator (~1,730).
-- When Volume 4 is published, add a book_views_vol4 row here (INSERT stays
-- closed to the anon key by design — new sources go through a migration).

ALTER TABLE passive_income DROP CONSTRAINT passive_income_block_check;
ALTER TABLE passive_income ADD CONSTRAINT passive_income_block_check
  CHECK (block IN ('revenue','traction','cost','books'));

INSERT INTO passive_income
  (block, source_key, label, value_num, value_display, detail, is_status, method, sort_order)
VALUES
  ('books', 'book_views_vol1', 'Vol 1', 25, '25', 'Payhip product views · cumulative', false, 'manual', 1),
  ('books', 'book_views_vol2', 'Vol 2', 69, '69', 'Payhip product views · cumulative', false, 'manual', 2),
  ('books', 'book_views_vol3', 'Vol 3', 39, '39', 'Payhip product views · cumulative', false, 'manual', 3)
ON CONFLICT (source_key) DO NOTHING;

UPDATE passive_income SET
  label = 'Store views',
  detail = 'Payhip store · daily views, cumulative'
WHERE source_key = 'payhip_views';

UPDATE passive_income SET value_display = '~1,730'
WHERE source_key = 'umami_visits';

-- Rollback:
--   DELETE FROM passive_income WHERE block = 'books';
--   ALTER TABLE passive_income DROP CONSTRAINT passive_income_block_check;
--   ALTER TABLE passive_income ADD CONSTRAINT passive_income_block_check
--     CHECK (block IN ('revenue','traction','cost'));
