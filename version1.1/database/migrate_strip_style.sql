-- ============================================================
-- HOW EACH STRIP IS LAID OUT
--
-- Adds two rows to store_setting:
--
--   featured_style     how the "Món nổi bật" strip arranges its drinks
--   bestseller_style   the same, for "Bán chạy nhất"
--
-- FOUR ARRANGEMENTS, AND WHERE THEY COME FROM
--
--   carousel   one row that scrolls sideways. What the strips already
--              do, and what a drinks kiosk normally does: it costs the
--              fold one card's height however many drinks are in it.
--
--   grid       every drink visible at once, wrapping. The "Portfolio
--              Grid" / "Feature-Rich Showcase" pattern -- visuals first,
--              nothing hidden behind a scroll. Right when the strip holds
--              three or four and scrolling to find the fourth is absurd.
--
--   spotlight  the first drink large, the rest small beside it. This is
--              the Bento Box Grid arrangement (Apple-style: modular
--              cards at varied spans, 16-24px radii, soft shadows). It
--              is the one arrangement that says which drink matters
--              MOST, so it suits a promotion or a #1 seller.
--
--   list       compact rows: rank, photo, name, price, cups sold. Not
--              from the design database -- there is no ranked-list
--              pattern in it -- but it is how every chart people already
--              read is built, and it is the only arrangement where the
--              NUMBERS fit beside the drinks rather than on top of them.
--
-- WHY A SETTING AND NOT A CHOICE MADE IN CODE
--   The right arrangement depends on how many drinks are in the strip
--   and how big the screen is, and both are the shop's to change. A
--   carousel of three drinks on a wide kiosk is a row with a hole in it;
--   a grid of eight is a second menu above the menu.
--
-- SAFE TO RE-RUN
--   INSERT IGNORE, so a second run cannot put a choice back to default.
--
-- BEFORE RUNNING
--   mysqldump -u root -p beveragepos > database/backup_before_style.sql
--   mysql -u root -p beveragepos < database/migrate_strip_style.sql
--
-- AFTER RUNNING
--   python3 -m store_gui.sync_menu
-- ============================================================

CREATE TABLE IF NOT EXISTS store_setting (
    setting_key VARCHAR(64) NOT NULL PRIMARY KEY,
    setting_value VARCHAR(255) NOT NULL,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
        ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB;

-- Both default to 'carousel' -- what the strips already do. A migration
-- that redesigned the shop floor on its own would be a surprise nobody
-- asked for; the other three are there to be chosen.
INSERT IGNORE INTO store_setting (setting_key, setting_value) VALUES
    ('featured_style',   'carousel'),
    ('bestseller_style', 'carousel');


-- ============================================================
-- VERIFY
-- ============================================================
SELECT setting_key, setting_value FROM store_setting ORDER BY setting_key;
