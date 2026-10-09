-- ============================================================
-- NEW ARRANGEMENTS FOR THE TWO STRIPS
--
-- No schema change. This retires three style values and brings in four,
-- and moves any shop already on a retired one onto its nearest
-- replacement so no kiosk is left holding a value the screen cannot draw.
--
-- WHY THE OLD THREE WENT
--   grid, spotlight and list were all the same object rearranged: a
--   bordered card with a photo and a white caption bar under it. Three
--   ways of stacking one thing is not three designs, and on the shop
--   floor they read as the menu drawn twice.
--
-- WHAT REPLACES THEM  (all four are cost:low -- this runs on a Pi)
--   cinematic  full-bleed photo, name and price ON it behind a scrim.
--              No border, no caption bar. The photo gets the whole tile
--              instead of sharing it, which is the point.
--   chart      the rank at 56-92px as the ground, the drink over it.
--              Exaggerated Minimalism. BESTSELLER ONLY -- the featured
--              strip is six drinks in no order, and numbering them would
--              invent a ranking the shop never made.
--   board      no cards at all: name, dot leaders, price. A wall menu.
--              Editorial Grid + Exaggerated Minimalism.
--   bubble     round photos, soft double shadows, caption underneath.
--              Claymorphism -- which the design database names as a
--              secondary style for food service.
--
-- carousel is unchanged and stays the default.
--
-- SAFE TO RE-RUN
--   The UPDATEs only match the retired values, so a second run finds
--   nothing to move.
--
--   mysql -u root -p beveragepos < database/migrate_strip_style_v2.sql
--   python3 -m store_gui.sync_menu
-- ============================================================

-- grid and spotlight were both "photo tiles in rows"; cinematic is that
-- without the card around it, so it is the honest landing spot.
UPDATE store_setting
   SET setting_value = 'cinematic'
 WHERE setting_key IN ('featured_style', 'bestseller_style')
   AND setting_value IN ('grid', 'spotlight');

-- list was a ranked row. On the bestseller strip that is chart; on the
-- featured strip there is no ranking, so it becomes the board.
UPDATE store_setting SET setting_value = 'chart'
 WHERE setting_key = 'bestseller_style' AND setting_value = 'list';

UPDATE store_setting SET setting_value = 'board'
 WHERE setting_key = 'featured_style' AND setting_value = 'list';

-- Belt and braces for a hand-edited row: anything the screen cannot draw
-- goes back to the default rather than leaving a blank strip.
UPDATE store_setting
   SET setting_value = 'carousel'
 WHERE setting_key IN ('featured_style', 'bestseller_style')
   AND setting_value NOT IN ('carousel', 'cinematic', 'chart', 'board', 'bubble');

-- The featured strip cannot be a chart: it has nothing to rank.
UPDATE store_setting SET setting_value = 'board'
 WHERE setting_key = 'featured_style' AND setting_value = 'chart';

SELECT setting_key, setting_value FROM store_setting
 WHERE setting_key LIKE '%_style';
