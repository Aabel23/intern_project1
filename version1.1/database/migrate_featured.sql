-- ============================================================
-- FEATURED ITEMS: the drinks the shop wants pushed, and the strip
-- that shows them on the customer screen
--
-- Adds one column and one table:
--
--   drink.featured    the shop has picked this drink to be pushed
--   store_setting     key/value settings for the store screen; the
--                     featured strip's three are seeded here
--
-- WHY A COLUMN AND NOT A CATEGORY
--   The menu already has a hand-mapped "Bestseller" category, and that
--   is the thing this replaces the use of. A category is a way of
--   BROWSING -- it appears in the pill rail, it filters the grid, a
--   drink either belongs to it or does not. "Featured" is none of
--   those: it is a promotion, it must not add a pill, and it has to be
--   switchable from one screen without touching what the customer can
--   filter by. Modelled as a category it would have leaked into the
--   rail and into every count that walks drink_category_mapping.
--
-- WHY NOT A RANK COLUMN TOO
--   The strip is three to six cards on a kiosk, and the operator picks
--   them by hand. Ordering by drink_id keeps them in the same order as
--   the menu underneath, which is the order the operator is already
--   looking at in the admin table. A rank column is worth adding the
--   day somebody actually asks to reorder the strip -- and until then
--   it is a second field to keep correct for no visible effect.
--
-- WHY store_setting AND NOT A CONFIG FILE
--   The store screen is rebuilt from MySQL by store_gui/sync_menu.py.
--   A setting kept anywhere else would be a second source of truth
--   that the rebuild does not read, and the admin console would be
--   writing to one of them while the kiosk read the other. It is also
--   deliberately generic: the next screen setting goes in as a row,
--   not as another ALTER.
--
-- SAFE TO RE-RUN
--   The column is added only when information_schema says it is
--   missing, the table is IF NOT EXISTS, and the seeds are
--   INSERT IGNORE -- so a second run cannot reset a setting an
--   operator has already changed.
--
-- BEFORE RUNNING
--   Take a backup.
--
--   mysqldump -u root -p beveragepos > database/backup_before_featured.sql
--   mysql -u root -p beveragepos < database/migrate_featured.sql
--
-- AFTER RUNNING
--   python3 -m store_gui.sync_menu     # rebuild the customer screen
-- ============================================================

-- MySQL has no ADD COLUMN IF NOT EXISTS, so the column is asked for
-- only when it is not already there. Same guard as migrate_drink_type.
SET @has_featured := (
    SELECT COUNT(*) FROM information_schema.COLUMNS
    WHERE TABLE_SCHEMA = DATABASE()
      AND TABLE_NAME = 'drink'
      AND COLUMN_NAME = 'featured');

-- NOT NULL DEFAULT FALSE, not NULL-able: "not featured" is a real
-- answer and every existing row has it. A nullable flag would make
-- three states out of a switch that has two.
SET @sql := IF(@has_featured = 0,
    'ALTER TABLE drink ADD COLUMN featured BOOLEAN NOT NULL DEFAULT FALSE',
    'DO 0');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

-- The strip is read on every menu rebuild and the featured rows are a
-- handful out of the whole table, so it is worth not scanning it.
SET @has_index := (
    SELECT COUNT(*) FROM information_schema.STATISTICS
    WHERE TABLE_SCHEMA = DATABASE()
      AND TABLE_NAME = 'drink'
      AND INDEX_NAME = 'idx_drink_featured');

SET @sql := IF(@has_index = 0,
    'CREATE INDEX idx_drink_featured ON drink (featured)',
    'DO 0');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;


-- ============================================================
-- STORE SETTINGS
-- ============================================================
-- Everything the customer screen is told about itself that is not a
-- drink. Text values throughout -- the reader casts, and a settings
-- table that grows a column per type stops being a settings table.
CREATE TABLE IF NOT EXISTS store_setting (
    setting_key VARCHAR(64) NOT NULL PRIMARY KEY,
    setting_value VARCHAR(255) NOT NULL,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
        ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB;

-- INSERT IGNORE, never ON DUPLICATE KEY UPDATE: re-running this file
-- must not put an operator's choices back to the defaults.
--
--   featured_enabled   '1' / '0'      -- draw the strip at all
--   featured_position  'top'/'bottom' -- above the grid, or below it
--   featured_title     free text      -- the heading over the strip
INSERT IGNORE INTO store_setting (setting_key, setting_value) VALUES
    ('featured_enabled',  '1'),
    ('featured_position', 'top'),
    ('featured_title',    'Món nổi bật');


-- ============================================================
-- VERIFY
-- ============================================================
SELECT setting_key, setting_value FROM store_setting ORDER BY setting_key;

SELECT
    (SELECT COUNT(*) FROM drink
      WHERE featured = 1 AND deleted_at IS NULL)      AS featured_drinks,
    (SELECT COUNT(*) FROM drink
      WHERE featured = 1 AND deleted_at IS NULL
        AND available = 1 AND in_stock = 1)           AS featured_and_sellable;
