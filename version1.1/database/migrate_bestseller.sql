-- ============================================================
-- BESTSELLERS, AND A LAYOUT THAT CAN HOLD MORE THAN ONE MODULE
--
-- Adds no columns. Everything here is rows in store_setting:
--
--   bestseller_enabled      draw the bán-chạy strip at all
--   bestseller_title        the heading over it
--   bestseller_window_days  how far back "bán chạy" looks
--   bestseller_count        how many drinks it shows
--   layout_order            the order the store screen stacks its blocks
--
-- WHY A REAL QUERY AND NOT THE "Bestseller" CATEGORY
--   That category is category_id 4005 with the description "Danh sách
--   đồ uống bán chạy nhất", and its four drinks are hand-mapped in
--   drink_category_mapping exactly like Summer or Tea. Nothing keeps it
--   true. Checked against order_ticket on 2026-08-31 it held Mint Julep,
--   which has never been sold once, while the two best sellers in the
--   shop -- SO1 at 49 cups and Peach Tea at 24 -- were not in it at all.
--
--   The strip this seeds is computed from order_ticket every time the
--   menu is rebuilt, so it cannot drift. The category is left alone:
--   deleting one is the shop's decision, not a migration's.
--
-- WHY layout_order REPLACES featured_position
--   featured_position was 'top' or 'bottom', meaning "above or below the
--   menu". That is only an answer while there is ONE module. With two,
--   both can say 'top' and nothing decides which of them comes first.
--
--   An ordered list of block names answers it for any number of modules,
--   and it is the shape a drag-to-reorder builder edits directly -- the
--   builder becomes a way of writing this row, not a new model.
--
--   'grid' is the menu itself and is always in the list: it can be moved
--   but never removed, because a drinks machine with no drinks on screen
--   is not a state worth being able to configure.
--
-- SAFE TO RE-RUN
--   Every seed is INSERT IGNORE, so a second run cannot put an
--   operator's choices back to the defaults.
--
-- BEFORE RUNNING
--   mysqldump -u root -p beveragepos > database/backup_before_bestseller.sql
--   mysql -u root -p beveragepos < database/migrate_bestseller.sql
--
-- AFTER RUNNING
--   python3 -m store_gui.sync_menu
-- ============================================================

-- store_setting is created by migrate_featured.sql / database.sql. Repeated
-- here so this file can be run on its own, in either order.
CREATE TABLE IF NOT EXISTS store_setting (
    setting_key VARCHAR(64) NOT NULL PRIMARY KEY,
    setting_value VARCHAR(255) NOT NULL,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
        ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB;

-- 30 days, not all-time: all-time freezes whatever was popular in the
-- first weeks and never lets go of it, which stops being a "bán chạy"
-- list and becomes a hall of fame. Not 7 either -- at this shop's volume
-- a week is a handful of cups and the ranking would be noise.
--
-- 6 drinks, matching the featured strip's ceiling and for the same
-- reason: past about six the strip stops being a recommendation and
-- becomes a second menu to read before reaching the first one.
INSERT IGNORE INTO store_setting (setting_key, setting_value) VALUES
    ('bestseller_enabled',     '1'),
    ('bestseller_title',       'Bán chạy nhất'),
    ('bestseller_window_days', '30'),
    ('bestseller_count',       '6');

-- Carried over rather than defaulted, so a shop that had deliberately put
-- the featured strip UNDER the menu still finds it there afterwards.
SET @pos := (SELECT setting_value FROM store_setting
              WHERE setting_key = 'featured_position');

INSERT IGNORE INTO store_setting (setting_key, setting_value) VALUES
    ('layout_order', IF(@pos = 'bottom',
                        'grid,featured,bestseller',
                        'featured,bestseller,grid'));

-- Superseded by layout_order above, and removed rather than left sitting
-- there: two rows that both claim to say where the featured strip goes is
-- the kind of pair somebody edits the wrong half of a year from now.
DELETE FROM store_setting WHERE setting_key = 'featured_position';


-- ============================================================
-- VERIFY
-- ============================================================
SELECT setting_key, setting_value FROM store_setting ORDER BY setting_key;

-- What the strip will actually hold, with the seeded window and count.
SELECT COALESCE(t.drink_name, d.drink_name) AS ten,
       COUNT(*) AS da_ban
  FROM order_ticket t
  JOIN drink d ON d.drink_id = t.drink_id
 WHERE t.status = 'used'
   AND t.completed_at >= NOW() - INTERVAL 30 DAY
   AND d.deleted_at IS NULL AND d.available = 1 AND d.in_stock = 1
 GROUP BY t.drink_id, ten
 ORDER BY da_ban DESC, MAX(t.completed_at) DESC
 LIMIT 6;
