-- ============================================================
-- HOW MANY COLUMNS THE STACKED ARRANGEMENTS RUN IN
--
-- Adds two rows to store_setting:
--
--   featured_columns     1-3
--   bestseller_columns   1-3
--
-- WHY
--   board and chart stack their items down the tray, one per line, and a
--   line is as wide as the tray. On a kiosk that is a name at one end, a
--   price at the other and a hand's width of nothing between them -- and
--   six of those is most of the fold spent on white space. Two columns
--   halves the height and closes the gap.
--
--   It has no meaning for carousel, cinematic or bubble: those run
--   sideways and scroll, so "columns" is not a question they answer. The
--   setting is stored anyway and simply not applied, which is what lets
--   an operator switch a strip to board, set two columns, switch back to
--   look at something else, and find their two columns still there.
--
-- 1 IS THE DEFAULT
--   Same rule as every other setting added here: a migration must not
--   redesign the shop floor on its own.
--
-- SAFE TO RE-RUN -- INSERT IGNORE.
--
--   mysql -u root -p beveragepos < database/migrate_strip_columns.sql
--   python3 -m store_gui.sync_menu
-- ============================================================

CREATE TABLE IF NOT EXISTS store_setting (
    setting_key VARCHAR(64) NOT NULL PRIMARY KEY,
    setting_value VARCHAR(255) NOT NULL,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
        ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB;

INSERT IGNORE INTO store_setting (setting_key, setting_value) VALUES
    ('featured_columns',   '1'),
    ('bestseller_columns', '1');

SELECT setting_key, setting_value FROM store_setting
 WHERE setting_key LIKE '%_columns' OR setting_key LIKE '%_style';
