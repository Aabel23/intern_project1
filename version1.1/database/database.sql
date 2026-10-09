-- ============================================================
-- BEVERAGEPOS DATABASE SCHEMA + DEFAULT DATA
-- File này là nguồn mô tả cấu trúc database.
-- Có thể chạy lặp lại bằng lệnh "update" mà không xóa tồn kho hiện tại.
--
-- Bảng: drink, category, drink_category_mapping, ingredient, recipe.
-- GPIO nằm trong ingredient, không còn bảng ingredient_gpio_mapping.
--
-- ------------------------------------------------------------
-- ĐỔI SCHEMA THÌ KHÔNG SỬA FILE NÀY — VIẾT MỘT MIGRATION
--
--     database/migrations/NNNN_ten.sql
--
-- File này giờ là MỐC GỐC: schema tại 0001, không phải schema hôm nay.
--
-- Vì sao: CREATE TABLE IF NOT EXISTS không đụng tới một bảng đã tồn tại.
-- Thêm một cột vào đây thì máy mới có nó, còn máy đang chạy thì không --
-- và đó đúng là lý do mười ba file migrate_*.sql chất đống trong
-- database/. Mỗi file trong số đó là nửa sau của một lần sửa mà nửa đầu
-- nằm ngay trong file này.
--
-- Một migration đánh số là cả hai nửa cùng lúc: chạy trên máy mới và trên
-- máy năm tháng tuổi, mỗi máy đúng một lần, và để lại một dòng nói là đã
-- chạy. Xem database/migrate.py.
-- ------------------------------------------------------------
-- ============================================================

-- ------------------------------------------------------------
-- ID RANGES
--
-- Ids are displayed four digits wide across every screen (0001, 1001,
-- 3001...), and the leading digit says what kind of thing an id names.
-- The point is being able to read an id out of a log, a label or a screen
-- and know what it refers to without being told.
--
--   ingredient   0001-0999
--   drink        1001-1999
--   glass        3001-3999
--   category     4001-4999
--   drink_type   5001-5999
--
-- WHY INGREDIENT IS THE ONE THAT STARTS AT ZERO
--   Because 0001 IS 1: the leading zeros are how the number is written,
--   not a different number. So ingredient ids need no renumbering at all
--   -- 1..13 already sit inside 0001-0999 -- and, crucially, the QR
--   protocol is untouched.
--
--   That matters because the protocol encodes an ingredient in a TWO
--   digit opcode field (qrproto/inner.py: f"{ingredient:02d}") with a
--   range check of 1-24. An ingredient numbered 2001 could not be
--   encoded at all: "2001" would overrun the field and eat the type code
--   after it. The ceiling here is 24, raisable to 99 by one constant
--   without changing the wire format; past 99 the protocol itself would
--   have to change, invalidating every label already printed.
--
--   drink ids are safe in 1001-1999 because the SKU field is four digits
--   (SKU_MIN..SKU_MAX = 0..9999). glass, category and drink_type never
--   enter a QR.
-- ------------------------------------------------------------

-- ------------------------------------------------------------
-- 1. TABLES
-- ------------------------------------------------------------

-- The database's own logbook: which schema changes this machine has had.
--
-- WHY IT COMES FIRST
--   Every other table here describes the shop. This one describes the
--   other tables -- it is the only row anybody can read to answer "what
--   shape is machine 7 in?" without opening MySQL and looking at columns.
--
-- WHY IT WAS NEEDED
--   Schema changes reached a machine three different ways: this file
--   (re-run every update, with "already exists" errors swallowed -- see
--   IGNORED_SCHEMA_ERROR_CODES), four migrate_*() functions in
--   db_core.py, and thirteen migrate_*.sql files run by hand. All three
--   are idempotent, which is why none of them break. But safe to re-run
--   is not the same as recorded, and with one machine you remember while
--   with thirty you do not.
--
--   database/MIGRATIONS.md says what happened to those thirteen files.
--
-- HOW A ROW GETS HERE
--   database/migrate.py reads this table, finds the numbered files in
--   database/migrations/ that are not in it, applies them oldest first,
--   and writes one row each. Run twice, the second run does nothing --
--   and knows that it is doing nothing, rather than re-running and
--   ignoring the complaints.
--
-- checksum
--   sha256 of the file as it was applied. A migration edited after the
--   fact is a machine whose history says one thing and whose schema is
--   another; this is what turns that into a loud failure instead of a
--   silent divergence.
CREATE TABLE IF NOT EXISTS schema_migration (
    version    CHAR(4)     NOT NULL PRIMARY KEY,
    name       VARCHAR(80) NOT NULL,
    checksum   CHAR(64)    NOT NULL,
    applied_at DATETIME    NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;


-- What the drink is served in. A small, stable list: these are the shapes
-- a bar actually stocks, not a per-drink free-text field, so the bartender
-- screen can draw the right one and two drinks in "the tall glass" always
-- mean the same glass.
--
-- `art` is the filename stem the bartender screen looks for in
-- bartender_gui/images/guide/ (glass-<art>.png). Kept here rather than
-- derived from the name so renaming a glass for staff does not break its
-- picture.
CREATE TABLE IF NOT EXISTS glass (
    glass_id INT AUTO_INCREMENT PRIMARY KEY,
    glass_name VARCHAR(60) NOT NULL UNIQUE,
    art VARCHAR(40) NOT NULL,
    -- Rough capacity, for whoever is choosing a glass for a new drink.
    -- The admin recipe editor shows it beside each glass in the picker,
    -- and warns when the recipe's own grams add up to more than it holds
    -- -- at 1 g = 1 ml, which is stated on screen because it is an
    -- approximation: syrup is nearer 1.3 g/ml and there is no density
    -- column to do better with.
    --
    -- It stays advisory. Nothing on the machine reads it and no save is
    -- refused over it: the pumps pour what the recipe says, ice displaces
    -- liquid, and a bar knows its own glassware better than this column
    -- does.
    capacity_ml INT NULL,
    sort_order INT NOT NULL DEFAULT 0
) ENGINE=InnoDB;

-- HOW the drink is built, and on what ice. The sibling of `glass`: a small,
-- stable list of the shapes a bar actually works in, not free text typed
-- per drink -- so "đá viên" always means the same ice, and the bartender
-- screen can draw it.
--
-- One row is one build: an ice kind AND the method that goes with it,
-- because in practice they are never chosen separately. Nobody blends a
-- drink over cubes, and "nugget" already implies the cup is filled before
-- the machine pours. Splitting them into two tables would have produced a
-- grid of combinations no bar has ever served.
--
-- `art` is the filename stem the bartender screen looks for in
-- bartender_gui/images/guide/ (ice-<art>.png), and the key its built-in
-- drawing is chosen by when there is no file. Kept apart from the name
-- for the same reason as glass.art: renaming the ice for staff must not
-- break its picture.
--
-- Nothing on the machine reads any of this. It is reference data for the
-- person standing at it -- which is exactly why it lives in the database
-- and rides out on the recipe, instead of in somebody's head.
CREATE TABLE IF NOT EXISTS drink_type (
    drink_type_id INT AUTO_INCREMENT PRIMARY KEY,
    -- Staff-facing name of the ice. Vietnamese only, like glass_name: the
    -- people who read this screen are standing at the machine, and the
    -- bartender screen's EN toggle shows these facts in Vietnamese
    -- whatever it is set to. That is the trade, made on purpose.
    type_name VARCHAR(60) NOT NULL,
    -- The one machine-readable key on the row, exactly like glass.art:
    -- 'cube', 'nugget', 'crushed', 'blend', 'none', 'hot'. It names the
    -- picture the bartender screen looks for in
    -- bartender_gui/images/guide/ (ice-<art>.png) and, when there is no
    -- file, which built-in drawing to use instead.
    --
    -- Kept separate from type_name for the same reason as glass.art:
    -- renaming the ice for staff must not break its picture. There was
    -- briefly a second key called `code` holding the identical string --
    -- one column does both jobs, and two only meant two things to keep
    -- in step.
    art VARCHAR(40) NOT NULL UNIQUE,
    -- The build method, the headline on the prep card: "Dựng thẳng trong
    -- ly".
    method VARCHAR(60) NULL,
    -- One line saying what that method means in practice. The only column
    -- here with an editor behind it -- the admin recipe editor writes it,
    -- so nothing that reseeds this table may overwrite it.
    detail VARCHAR(200) NULL,
    -- The order the admin picker lists these in: the order a bar thinks
    -- about ice, not the order the ids happen to run. Steps of 10 so a new
    -- kind slots between two without renumbering the rest.
    sort_order INT NOT NULL DEFAULT 0
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS drink (
    drink_id INT AUTO_INCREMENT PRIMARY KEY,
    drink_name VARCHAR(100) NOT NULL UNIQUE,
    image VARCHAR(255) NULL,
    price DECIMAL(10,2) NOT NULL DEFAULT 0.00,
    available BOOLEAN NOT NULL DEFAULT TRUE,
    in_stock BOOLEAN NOT NULL DEFAULT TRUE,
    -- NULL for a drink on the menu; a timestamp for one in the bin.
    --
    -- Deleting is reversible on purpose. A recipe is somebody's work and
    -- a mis-click should not destroy it, so the row stays and every query
    -- that lists the menu skips it instead. Emptying the bin is the only
    -- thing that really removes it.
    --
    -- Note this keeps the drink's NAME reserved: drink_name is UNIQUE, so
    -- a binned drink still holds its name. That is deliberate -- without
    -- it, restoring a drink whose name had been reused would fail.
    deleted_at DATETIME NULL,

    -- Which glass this drink is served in. NULL means nobody has said yet,
    -- and that is a working state on purpose: the bartender screen simply
    -- skips its glass step rather than blocking a drink over missing
    -- reference data. Set it in the admin GUI's recipe editor.
    --
    -- ON DELETE SET NULL, not RESTRICT: retiring a glass shape should not
    -- be blocked by the drinks that used it, and a drink with no glass is
    -- a state the whole system already handles.
    glass_id INT NULL,

    -- How this drink is built, and on which ice. Same rules as glass_id
    -- throughout: NULL is a working state, and ON DELETE SET NULL so
    -- retiring a build method cannot block the drinks that used it.
    drink_type_id INT NULL,

    -- The garnish, per drink. The one prep fact that is genuinely about
    -- THIS drink rather than about its build method -- a mojito gets mint
    -- and a peach tea gets a fat straw, though both are built in glass --
    -- so it is a column here instead of a row in drink_type.
    --
    -- Free text on purpose. A bar invents garnishes faster than anyone
    -- maintains a lookup table, and nothing reads this but a human.
    garnish VARCHAR(120) NULL,

    -- The shop has picked this drink to be pushed. It feeds the featured
    -- strip on the customer screen and nothing else -- it does not change
    -- what can be ordered, what a drink costs, or where it sits in the
    -- menu underneath.
    --
    -- Not a category, though the menu already has a hand-mapped
    -- "Bestseller" one. A category is a way of BROWSING: it earns a pill
    -- in the rail and it filters the grid. This is a promotion, it must
    -- add no pill, and it has to be switchable without touching what the
    -- customer can filter by.
    --
    -- NOT NULL with a default because "not featured" is a real answer
    -- that every row already has; a nullable flag would make three
    -- states out of a switch with two.
    featured BOOLEAN NOT NULL DEFAULT FALSE,

    CONSTRAINT fk_drink_glass
        FOREIGN KEY (glass_id)
        REFERENCES glass (glass_id)
        ON DELETE SET NULL
        ON UPDATE CASCADE,

    CONSTRAINT fk_drink_drink_type
        FOREIGN KEY (drink_type_id)
        REFERENCES drink_type (drink_type_id)
        ON DELETE SET NULL
        ON UPDATE CASCADE
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS category (
    category_id INT AUTO_INCREMENT PRIMARY KEY,
    category_name VARCHAR(255) NOT NULL UNIQUE,
    description TEXT NULL
) ENGINE=InnoDB;

-- Everything the customer screen is told about itself that is not a
-- drink. Right now that is the three rows the featured strip needs, but
-- it is deliberately generic: the next screen setting goes in as a row,
-- not as another ALTER on a table it does not belong to.
--
-- WHY IT IS IN MYSQL AND NOT A CONFIG FILE
--   store_gui/sync_menu.py rebuilds the customer screen from this
--   database. A setting kept anywhere else would be a second source of
--   truth the rebuild does not read, so the admin console would write to
--   one place while the kiosk read another.
--
-- Values are text and the reader casts. A settings table that grows a
-- column per type has stopped being a settings table.
CREATE TABLE IF NOT EXISTS store_setting (
    setting_key VARCHAR(64) NOT NULL PRIMARY KEY,
    setting_value VARCHAR(255) NOT NULL,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
        ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB;

-- INSERT IGNORE, never ON DUPLICATE KEY UPDATE: re-running database.sql
-- must not put an operator's choices back to the defaults.
--
-- THE FEATURED STRIP -- drinks the shop has PICKED to push (drink.featured)
--   featured_enabled       '1' / '0'   -- draw the strip at all
--   featured_title         free text   -- the heading over it
--
-- THE BESTSELLER STRIP -- drinks that actually sold, counted from
-- order_ticket on every menu rebuild, so it cannot drift out of date
--   bestseller_enabled     '1' / '0'
--   bestseller_title       free text
--   bestseller_window_days how far back "bán chạy" looks
--   bestseller_count       how many drinks it shows
--
--   Note this is NOT the "Bestseller" category. That one is hand-mapped
--   in drink_category_mapping like any other category and nothing keeps
--   it true; this is a query.
--
-- THE PAGE ITSELF
--   layout_order  the order the store screen stacks its blocks, as a
--                 comma-separated list. 'grid' is the menu and is always
--                 in it -- movable, never removable. A list rather than a
--                 position per module because two modules both saying
--                 "top" answers nothing, and because this is the row a
--                 drag-to-reorder builder edits.
INSERT IGNORE INTO store_setting (setting_key, setting_value) VALUES
    ('featured_enabled',       '1'),
    ('featured_title',         'Món nổi bật'),
    ('bestseller_enabled',     '1'),
    ('bestseller_title',       'Bán chạy nhất'),
    ('bestseller_window_days', '30'),
    ('bestseller_count',       '6'),
    ('layout_order',           'featured,bestseller,grid'),
    -- How each strip arranges its drinks: carousel (one scrolling row),
    -- grid (all visible, wrapping), spotlight (first one large, the rest
    -- beside it), or list (compact numbered rows). See
    -- database/migrate_strip_style.sql for what each is for.
    ('featured_style',         'carousel'),
    ('bestseller_style',       'carousel'),
    -- How many columns the STACKED arrangements (board, chart) run in.
    -- Meaningless for the three that scroll sideways, and simply not
    -- applied there. See database/migrate_strip_columns.sql.
    ('featured_columns',       '1'),
    ('bestseller_columns',     '1');

CREATE TABLE IF NOT EXISTS drink_category_mapping (
    drink_id INT NOT NULL,
    category_id INT NOT NULL,

    PRIMARY KEY (
        drink_id,
        category_id
    ),

    CONSTRAINT fk_drink_category_drink
        FOREIGN KEY (drink_id)
        REFERENCES drink(drink_id)
        ON DELETE CASCADE,

    CONSTRAINT fk_drink_category_category
        FOREIGN KEY (category_id)
        REFERENCES category(category_id)
        ON DELETE CASCADE
) ENGINE=InnoDB;

-- type      : PUMP   = máy tự bơm qua chân GPIO của Raspberry Pi.
--             MANUAL = nhân viên tự cho vào, xác nhận bằng nút trên panel.
-- data_type : cách khách chọn nguyên liệu này khi đặt món
--             boolean / percentage / weight.
-- gpio      : PUMP   = chân GPIO (BCM) của bơm, ví dụ 26.
--             MANUAL = vị trí panel 0-15 trên hai board PCF8575.
--                      panel_control/panel.py tự đổi vị trí này thành
--                      chân LED (0x21) và chân nút (0x20) tương ứng.
--             Hai loại dùng chung một cột nên khóa duy nhất phải gồm
--             cả type: bơm GPIO 12 và panel 12 là hai thứ khác nhau.
-- data_type decides what control the CUSTOMER gets over this ingredient:
--
--   'weight'      no control. Poured exactly as recipe.target_gram says.
--   'percentage'  a dial. recipe.target_gram IS the 100% amount, and the
--                 customer picks a share of it, so 100 means "as the
--                 recipe says" and 50 means half. Add a second dial by
--                 setting another ingredient to 'percentage' -- nothing
--                 in the code names Sugar, so no code has to change.
--   'boolean'     a tick box, and it starts ticked. Being in the recipe
--                 IS the statement that it belongs in the drink;
--                 unticking is what takes it out.
--
-- There are no option_* columns. They existed briefly and every row held
-- the same value, because each one restated something the recipe already
-- said: a topping in the recipe starts ticked, a dial starts at 100%.
-- The one thing they could have expressed -- an ingredient present in the
-- recipe but OFF until the customer opts in -- is a pricing decision
-- nothing has needed yet.
CREATE TABLE IF NOT EXISTS ingredient (
    ingredient_id INT AUTO_INCREMENT PRIMARY KEY,
    ingredient_name VARCHAR(100) NOT NULL UNIQUE,
    type VARCHAR(16) NOT NULL DEFAULT 'PUMP',
    data_type VARCHAR(16) NOT NULL DEFAULT 'weight',
    amount DECIMAL(10,2) NOT NULL DEFAULT 0,
    threshold_gram DECIMAL(10,2) NOT NULL DEFAULT 0,
    -- How much this container holds when it is full: the level a refill
    -- fills it to, and the denominator of the % bar on the stock screen.
    --
    -- NULL means nobody has declared it yet, and that is a different
    -- statement from zero. Zero would divide by zero on the screen and
    -- would make "fill this bottle" mean "empty it"; NULL makes the admin
    -- console fall back to its default and SAY on screen that the figure
    -- is a guess. So it stays nullable rather than NOT NULL DEFAULT 0.
    max_gram DECIMAL(10,2) NULL,
    -- Where this ingredient physically lives, and WHICH KIND of place:
    --   PUMP    'G26'  a BCM pin driving a pump
    --   MANUAL  'P01'  a position on the button panel
    -- It was a bare INT, and a 1 in it could be pin 1 or panel 1 with
    -- nothing in the value to say which. See database/db_core.gpio_number().
    gpio VARCHAR(8) NULL,
    in_stock BOOLEAN NOT NULL DEFAULT TRUE,

    UNIQUE KEY uq_ingredient_type_gpio (type, gpio),

    CONSTRAINT ck_ingredient_amount CHECK (amount >= 0),
    CONSTRAINT ck_ingredient_threshold CHECK (threshold_gram >= 0),
    CONSTRAINT ck_ingredient_max_gram
        CHECK (max_gram IS NULL OR max_gram > 0),
    -- A slot is a letter and digits, so this has to be a pattern. It read
    -- "gpio >= 0" while the column was an INT, and that line survived the
    -- move to VARCHAR looking harmless: MySQL coerces 'G26' to 0 for the
    -- comparison, so it passed -- and so did 'zzz'. A fresh install got a
    -- constraint that constrained nothing while an upgraded one got the
    -- pattern below from ensure_ingredient_checks() in db_core.py. Same
    -- constraint name, two different rules, depending on how old the
    -- machine was.
    CONSTRAINT ck_ingredient_gpio
        CHECK (gpio IS NULL OR gpio REGEXP '^[GP][0-9]+$'),
    CONSTRAINT ck_ingredient_type
        CHECK (type IN ('PUMP', 'MANUAL')),
    CONSTRAINT ck_ingredient_data_type
        CHECK (data_type IN ('boolean', 'percentage', 'weight'))
) ENGINE=InnoDB;

-- One row per QR label the store screen issues.
--
-- WHY THIS TABLE EXISTS
--   A printed QR is passive: the paper cannot know it has already been
--   used. The code carries a serial; this table carries the state that
--   makes the serial mean something. The machine is standalone -- this
--   table is the whole authority on which labels are still good.
--
-- SINGLE USE
--   status moves unused -> in_progress -> used. The claim is one atomic
--   UPDATE ... WHERE status='unused', so two scans arriving together
--   cannot both win: the second gets rowcount 0 and is refused. A drink
--   that FAILS releases the ticket back to 'unused', so a hardware fault
--   does not cost the customer the order they paid for.
--
--   The scanned payload is checked against the stored one, not just the
--   serial, so a label whose digits were retyped or damaged into a
--   different order cannot claim a ticket that was issued for something
--   else.
--
-- SERIAL RANGE
--   6 digits, 000001-999999, handed out by AUTO_INCREMENT. At a hundred
--   drinks a day that is about 27 years. If it ever does run out the fix
--   is to widen the field -- to 7 or 9 digits, NOT 8: the payload length
--   rule would then collide with protocol v1.3's own 11+8n lengths and
--   old and new labels would stop being distinguishable.
--
-- EXPIRY
--   Checked when a code is scanned, against created_at -- not by a
--   nightly job, so it stays correct even if the machine was switched
--   off. A label carries amounts computed from the recipe as it was at
--   print time, which is the real reason old labels must not be honoured.
CREATE TABLE IF NOT EXISTS order_ticket (
    serial INT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
    drink_id INT NOT NULL,
    -- What the drink cost WHEN IT WAS SOLD. Not a copy of drink.price for
    -- convenience: the report reads it, and a report that recalculates
    -- last month's takings from this month's prices is not a record of
    -- anything. NULL on rows issued before this column existed, which the
    -- report falls back on and says so.
    price DECIMAL(10,2) NULL,
    -- The drink's NAME as sold, beside its price. Kept so a sale can be
    -- read back after the drink has been taken off the menu entirely:
    -- a sales record that stops making sense when somebody edits the
    -- menu is not a record. It is also what lets a drink be deleted.
    drink_name VARCHAR(100) NULL,
    payload VARCHAR(120) NOT NULL,
    -- What the customer typed in "Special Notes". It cannot travel in the
    -- QR -- that payload is digits only -- but it does not need to: the QR
    -- carries the serial, and the serial is this row. The machine reads it
    -- here when the code is scanned and shows it to whoever is standing at
    -- the machine.
    note VARCHAR(200) NULL,
    status VARCHAR(16) NOT NULL DEFAULT 'unused',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    scanned_at DATETIME NULL,
    completed_at DATETIME NULL,

    KEY idx_order_ticket_status (status, created_at),

    -- noqr_err: started from the store screen's "run without scanning"
    -- button and did not finish. It is a dead end on purpose -- there is no
    -- label to scan again, so 'unused' would leave a row that looks
    -- redeemable and never is.
    CONSTRAINT ck_order_ticket_status
        CHECK (status IN ('unused', 'in_progress', 'used', 'expired',
                          'noqr_err'))
) ENGINE=InnoDB;

-- Every fault the machine has, kept where it can be looked at later.
--
-- WHY A TABLE AND NOT JUST THE LOG FILE
--   The terminal scrolls away and closes with the session. order/flow.log
--   survives but is one line per event with no structure, so "how often
--   does pump 4 come up short" cannot be asked of it. This can be queried:
--   by drink, by step, by ingredient, by day.
--
--   It does not replace flow.log. That is written even when MySQL is
--   unreachable -- which is itself one of the faults worth recording.
--
-- NO FOREIGN KEYS, ON PURPOSE
--   drink_id is a plain int and drink_name is stored beside it. A log is
--   evidence: it has to survive the thing it describes being deleted or
--   renamed, and it must never be the reason a write is refused. A
--   constraint here could block the recording of a fault, or delete the
--   history of a drink taken off the menu.
--
-- WHAT A FAULT SAYS IS IN message
--   Five columns stood here and were dropped on 2026-09-07. source,
--   order_id and detail went because nothing read them; category and
--   ticket_key went because the shop asked for a leaner table. What each
--   one carried is written down in the two migrations --
--   database/migrate_drop_error_columns.sql and
--   database/migrate_drop_category_ticket.sql.
--
--   The consequence worth knowing: NOTHING joins a fault to a ticket or
--   an order any more. This table is a timestamped list of sentences,
--   each with a severity, read on one screen by whoever is standing at
--   the machine. Anything a person must know goes in `message`.
--
-- READING IT
--   python3 -m database.error_log --recent 20
CREATE TABLE IF NOT EXISTS error_log (
    error_id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,

    -- Millisecond precision: a failing step can write several entries in
    -- the same second, and their order is what tells the story.
    created_at DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),

    -- How loud the entry should read. The only column left to group or
    -- filter by: 'category' stood above this and was dropped 2026-09-07.
    severity VARCHAR(16) NOT NULL DEFAULT 'error',

    drink_id INT NULL,
    drink_name VARCHAR(100) NULL,
    step_label VARCHAR(16) NULL,
    step_type VARCHAR(16) NULL,

    -- The sentence a person reads -- and, since 2026-09-07, the only
    -- thing tying a fault to the order that caused it. Rows written by
    -- an order that had a ticket begin with a "[Vé #123]" tag naming
    -- its serial; database/error_log.py writes it and reads it back,
    -- and the fault screen links both ways on it. It lives in the text
    -- so that the link needed no column and no index: see HOW A FAULT
    -- STILL NAMES ITS TICKET there.
    message TEXT NOT NULL,

    KEY idx_error_log_time (created_at),

    CONSTRAINT ck_error_log_severity
        CHECK (severity IN ('info', 'warning', 'error'))
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS recipe (
    drink_id INT NOT NULL,
    ingredient_id INT NOT NULL,
    step_no INT NOT NULL,
    target_gram DECIMAL(10,2) NOT NULL,

    PRIMARY KEY (
        drink_id,
        step_no,
        ingredient_id
    ),

    CHECK (step_no > 0),
    CHECK (target_gram > 0),

    CONSTRAINT fk_recipe_drink
        FOREIGN KEY (drink_id)
        REFERENCES drink(drink_id)
        ON DELETE CASCADE,

    CONSTRAINT fk_recipe_ingredient
        FOREIGN KEY (ingredient_id)
        REFERENCES ingredient(ingredient_id)
        ON DELETE RESTRICT
) ENGINE=InnoDB;


-- The steps of a recipe that pour nothing: shake, stir, torch a peel,
-- garnish.
--
-- The recipe table above holds one row per POURED ingredient, so it has
-- no way to describe a step a person performs. Those live here, keyed by
-- the same (drink_id, step_no) the pump rows use, so the two interleave
-- on one numbering and a drink can pour, then act, then pour again.
--
-- cup_returns is what makes an action usable mid-recipe: when the glass
-- is lifted off the scale, export_data.py follows the action with a
-- detect step so the machine waits for it back before the next pour. A
-- final garnish leaves it on the scale and needs no such wait.
--
-- WHY IT IS HERE AND NOT IN db_core.py
--   It was created by migrate_action_step_schema() in Python and had no
--   CREATE TABLE in this file at all, which made this file an incomplete
--   description of the schema -- twelve tables out of thirteen. That is
--   fine until something pins a checksum of it as the definition of a
--   schema version, which is exactly what the fleet testbed is designed
--   to do. A half-truth is a bad thing to pin.
CREATE TABLE IF NOT EXISTS recipe_action (
    drink_id    INT NOT NULL,
    step_no     INT NOT NULL,
    media_src   VARCHAR(255) NOT NULL,
    title_vi    VARCHAR(120) NOT NULL,
    title_en    VARCHAR(120) NOT NULL DEFAULT '',
    detail_vi   VARCHAR(400) NOT NULL DEFAULT '',
    detail_en   VARCHAR(400) NOT NULL DEFAULT '',
    confirm_vi  VARCHAR(40)  NOT NULL DEFAULT '',
    confirm_en  VARCHAR(40)  NOT NULL DEFAULT '',
    cup_returns TINYINT(1)   NOT NULL DEFAULT 1,

    PRIMARY KEY (drink_id, step_no),

    CONSTRAINT fk_recipe_action_drink
        FOREIGN KEY (drink_id) REFERENCES drink (drink_id)
        ON DELETE CASCADE,
    CONSTRAINT recipe_action_chk_1 CHECK (step_no > 0)
) ENGINE=InnoDB
  DEFAULT CHARSET=utf8mb4
  COLLATE=utf8mb4_unicode_ci;

-- ============================================================
-- ADMIN_USER: who may sign in to the console, and what they may do
--
-- WHY A TABLE AND NOT THE JSON FILE
--   There used to be exactly one account, in configuration/
--   admin_account.json. One account cannot answer "who changed this
--   price", cannot be taken away from somebody who has left, and gives
--   the person who refills the syrup the same reach as the owner --
--   including deleting drinks and rewriting recipes. A shop with three
--   people sharing one password has no access control, it has a shared
--   secret.
--
--   The signing secret STAYS in that file. It is a property of the
--   machine, not of a person: it is what proves a token came from this
--   server, and putting it in a row would mean a database read on every
--   request just to check a signature.
--
-- WHAT IS STORED, AND WHAT IS NOT
--   A PBKDF2-HMAC-SHA256 digest and its per-account salt. Never the
--   password, and never a bare SHA-256 -- a plain digest of a short
--   password is a lookup away from being reversed, which is the whole
--   reason for a slow KDF with a salt. kdf_rounds travels WITH the row
--   rather than being a constant in the code, so raising the cost for
--   new passwords does not lock out everyone whose hash was made at the
--   old cost.
--
-- sessions_valid_from
--   A session token is signed, not stored, so it cannot be deleted --
--   which is fine until you need to actually remove somebody. Every
--   token records when it was issued, and one older than this column is
--   refused. Changing a password or switching an account off moves this
--   forward, so "you are locked out" means now rather than whenever the
--   token happened to expire.
--
-- NO FOREIGN KEY ANYWHERE TO THIS TABLE
--   Nothing else references a user. An account has to be deletable
--   without taking any record of what the shop sold with it.
-- ============================================================

CREATE TABLE IF NOT EXISTS admin_user (
    user_id INT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
    -- Lower-cased on the way in, so 'Manager' and 'manager' cannot be two
    -- accounts. The UNIQUE key below is what actually guarantees it.
    username VARCHAR(32) NOT NULL,
    -- What to call them on screen. Optional: an account with none shows
    -- its username, which is always something.
    display_name VARCHAR(64) NULL,
    password_hash VARCHAR(64) NOT NULL,
    password_salt VARCHAR(32) NOT NULL,
    kdf_rounds INT UNSIGNED NOT NULL DEFAULT 240000,
    role VARCHAR(16) NOT NULL DEFAULT 'staff',
    -- Switched off rather than deleted, for somebody who has left but
    -- whose name still explains a change made last month.
    active TINYINT(1) NOT NULL DEFAULT 1,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
        ON UPDATE CURRENT_TIMESTAMP,
    last_login_at DATETIME NULL,
    sessions_valid_from DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,

    UNIQUE KEY uq_admin_user_username (username),

    -- owner    everything, and the only role that may manage accounts
    -- manager  everything operational; cannot reach this table
    -- staff    the day-to-day screens only -- refill, tickets, mode,
    --          faults, and reports read-only
    CONSTRAINT ck_admin_user_role
        CHECK (role IN ('owner', 'manager', 'staff'))
) ENGINE=InnoDB;

-- ============================================================
-- ROLE_PERMISSION: what each role may reach, when it is not the default
--
-- WHY A TABLE WHEN THE DEFAULTS ARE IN CODE
--   Permissions in code are reviewable, versioned and rolled back with a
--   git revert. That is genuinely better, and it is still where the
--   DEFAULTS live -- admin_gui/permissions.py. This table exists because
--   a shop should not need a developer to decide that the person who
--   refills the syrup may also fix a price.
--
-- AN ABSENT ROW IS NOT AN EMPTY ONE
--   No row for a role means "nobody has changed this" and the code
--   default applies. A row with an empty `areas` means somebody
--   deliberately took everything away. The two must not collapse into
--   each other, which is why this is one row per role with a list rather
--   than one row per granted area -- with the latter, "took everything
--   away" is indistinguishable from "never configured", and a database
--   restored from a partial backup would silently hand out the defaults.
--
-- WHAT CANNOT BE STORED HERE
--   'shell' is never written and never read back: it is what lets a
--   signed-in page paint itself at all, and a role without it could not
--   render the screen it would be told it may not use. It is granted in
--   code, to everyone, always.
--
--   And the owner role always keeps 'users', enforced in
--   admin_gui/permissions.py rather than by a constraint here, because
--   the rule is "the console must never become uneditable" and SQL
--   cannot say that. Every other combination is allowed to be wrong: it
--   is recoverable from this screen. That one is not.
--
-- RECOVERY
--   python3 -m admin_gui.auth --reset-permissions
--   empties this table, and every role is back to the code defaults.
-- ============================================================

CREATE TABLE IF NOT EXISTS role_permission (
    role VARCHAR(16) NOT NULL PRIMARY KEY,
    -- Comma-separated area ids, in no particular order. Validated against
    -- admin_gui/permissions.AREAS before it is written, so an id that no
    -- longer exists cannot be stored -- but one that stops existing after
    -- an upgrade is ignored on read rather than fatal.
    areas VARCHAR(255) NOT NULL DEFAULT '',
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
        ON UPDATE CURRENT_TIMESTAMP,
    -- Who last changed it. A permission change is the one edit where
    -- "who" is worth as much as "what".
    updated_by VARCHAR(32) NULL,

    CONSTRAINT ck_role_permission_role
        CHECK (role IN ('owner', 'manager', 'staff'))
) ENGINE=InnoDB;

-- Support upgrading older databases that do not have these columns.
-- db_core.py ignores duplicate-column errors when a column already exists.
ALTER TABLE drink
ADD COLUMN image VARCHAR(255) NULL
AFTER drink_name;

ALTER TABLE drink
ADD COLUMN price DECIMAL(10,2) NOT NULL DEFAULT 0.00
AFTER image;

-- The glass a drink is served in. Two statements, because the column and
-- its foreign key fail independently: on a database that already has the
-- column the ADD COLUMN is a duplicate-column error db_core.py ignores,
-- while the constraint may still be missing.
ALTER TABLE drink
ADD COLUMN glass_id INT NULL;

ALTER TABLE drink
ADD CONSTRAINT fk_drink_glass
FOREIGN KEY (glass_id) REFERENCES glass (glass_id)
ON DELETE SET NULL ON UPDATE CASCADE;

-- The build method and its ice, for a database that predates them. Two
-- statements for the same reason as glass_id above: on an install that
-- already has the column the ADD COLUMN is a duplicate-column error
-- db_core.py ignores, while the constraint may still be missing.
--
-- The table itself is created by the CREATE TABLE IF NOT EXISTS above, so
-- the foreign key always has something to point at.
ALTER TABLE drink
ADD COLUMN drink_type_id INT NULL;

ALTER TABLE drink
ADD CONSTRAINT fk_drink_drink_type
FOREIGN KEY (drink_type_id) REFERENCES drink_type (drink_type_id)
ON DELETE SET NULL ON UPDATE CASCADE;

-- Garnish is free text with no constraint, so one statement is enough.
-- It arrives NULL, which reads as "nobody has said yet" -- the bartender
-- screen leaves the fact out rather than showing an empty one.
ALTER TABLE drink
ADD COLUMN garnish VARCHAR(120) NULL;

ALTER TABLE ingredient
ADD COLUMN type VARCHAR(16) NOT NULL DEFAULT 'PUMP'
AFTER ingredient_name;

ALTER TABLE ingredient
ADD COLUMN data_type VARCHAR(16) NOT NULL DEFAULT 'weight'
AFTER type;

-- The default moved with the 'number' -> 'weight' rename. CREATE TABLE IF
-- NOT EXISTS cannot change it on an installation that already has the
-- column, and a stale 'number' default would now fail the CHECK
-- constraint the moment a row was inserted without a data_type.
ALTER TABLE ingredient
ALTER COLUMN data_type SET DEFAULT 'weight';

-- Remove the option_* columns from an installation that has them. Their
-- CHECK constraints read those columns, and MySQL refuses to drop a column
-- a constraint still references, so the constraints go first.
ALTER TABLE ingredient DROP CHECK ck_ingredient_option_range;

ALTER TABLE ingredient DROP CHECK ck_ingredient_option_step;

ALTER TABLE ingredient DROP CHECK ck_ingredient_option_default;

ALTER TABLE ingredient DROP COLUMN option_default;

ALTER TABLE ingredient DROP COLUMN option_min;

ALTER TABLE ingredient DROP COLUMN option_max;

ALTER TABLE ingredient DROP COLUMN option_step;

ALTER TABLE ingredient DROP COLUMN option_order;

-- The full level of each container, for an installation that predates the
-- column. It arrives NULL for every existing row, which reads as "not
-- declared yet" -- exactly what was true a moment before the ALTER ran.
--
-- Nothing is back-filled here on purpose. A number invented by a migration
-- would be indistinguishable from one somebody measured, and the whole
-- point of the NULL is that the screen can tell those two apart. The admin
-- console carries over any figures the old configuration/
-- ingredient_capacity.json holds; see adopt_capacity_file() in
-- admin_gui/serve.py.
--
-- ck_ingredient_max_gram is NOT added here. Named CHECK constraints go on
-- an existing table through ensure_ingredient_checks() in db_core.py,
-- which knows to skip a constraint whose column has not landed yet and to
-- come back for it after this file has run.
ALTER TABLE ingredient
ADD COLUMN max_gram DECIMAL(10,2) NULL
AFTER threshold_gram;

-- Adds the column to an installation that predates it. VARCHAR, matching
-- the CREATE TABLE above: an install that gets the column from here must
-- end up with the same type as one that got it from there.
ALTER TABLE ingredient
ADD COLUMN gpio VARCHAR(8) NULL
AFTER threshold_gram;

-- And widens it on an installation that already has the old INT. Run
-- database/migrate_gpio_slots.sql to convert the VALUES; this only makes
-- the column able to hold them.
ALTER TABLE ingredient
MODIFY COLUMN gpio VARCHAR(8) NULL;

-- Carry the customer's note on tickets for an installation that predates it.
ALTER TABLE order_ticket
ADD COLUMN note VARCHAR(200) NULL
AFTER payload;

-- The recycle bin, for an installation created before it existed.
ALTER TABLE drink
ADD COLUMN deleted_at DATETIME NULL;

-- Every menu query filters on this, so it is worth an index.
CREATE INDEX idx_drink_deleted ON drink (deleted_at);

-- Capture the drink name on tickets for an installation that predates it,
-- and fill it in for the rows already there while their drinks still exist.
ALTER TABLE order_ticket
ADD COLUMN drink_name VARCHAR(100) NULL
AFTER price;

UPDATE order_ticket t
JOIN drink d ON d.drink_id = t.drink_id
SET t.drink_name = d.drink_name
WHERE t.drink_name IS NULL;

-- A sale must survive the drink being deleted, so the ticket no longer
-- points at the menu with a foreign key. The same reasoning as error_log:
-- a record of what happened cannot be held hostage by the thing it
-- describes. Reports read order_ticket.drink_name and fall back to the
-- drink table only for rows written before that column existed.
ALTER TABLE order_ticket DROP FOREIGN KEY fk_order_ticket_drink;

-- Capture the price on tickets for an installation that predates it.
ALTER TABLE order_ticket
ADD COLUMN price DECIMAL(10,2) NULL
AFTER drink_id;

-- Reports group by day over a date range, so the range is what the index
-- has to serve.
CREATE INDEX idx_order_ticket_completed
ON order_ticket (status, completed_at);

-- Widen the ticket status list on an installation created before the
-- store screen could start an order without a scan. CREATE TABLE IF NOT
-- EXISTS cannot alter a CHECK that is already there, so it is dropped and
-- rebuilt; on a fresh database this simply replaces the identical one the
-- CREATE above just made. db_core.py ignores 3821 when there is none.
ALTER TABLE order_ticket DROP CHECK ck_order_ticket_status;

ALTER TABLE order_ticket
ADD CONSTRAINT ck_order_ticket_status
CHECK (status IN ('unused', 'in_progress', 'used', 'expired', 'noqr_err'));

-- Remove the obsolete SKU index and column from older installations.
ALTER TABLE drink
DROP INDEX uq_all_drink_sku;

ALTER TABLE drink
DROP COLUMN sku;

-- Inventory completion events are kept in the filesystem outbox.
-- Remove the old database ledger when upgrading an existing installation.
DROP TABLE IF EXISTS inventory_consumption_log;

-- GPIO moved into ingredient, so the mapping table is no longer used.
DROP TABLE IF EXISTS ingredient_gpio_mapping;

-- Protocol v1.4 payloads run up to 224 digits (12 instruction pairs),
-- against v1.3's 113 -- widen the column before anything longer than
-- 120 characters is ever inserted. 255 leaves headroom without jumping
-- to a TEXT type this column never needs.
ALTER TABLE order_ticket
MODIFY COLUMN payload VARCHAR(255) NOT NULL;

-- qrproto (protocol v1.4) payloads carry no serial: the printed QR is
-- SKU + instructions + timestamp + machine ID only, encrypted, with no
-- room left for a value the database hands out. Two identical orders
-- still produce two different payload strings, because every AES-GCM
-- encryption draws a fresh random nonce -- so the payload itself is
-- already unique and can serve as the ticket's key without the serial's
-- help. `serial` stays as the table's own AUTO_INCREMENT primary key,
-- for internal reporting only; it is no longer printed on any label.
ALTER TABLE order_ticket
ADD COLUMN payload_hash CHAR(64) NULL
AFTER payload;

-- Backfill for rows written before this column existed, so every row's
-- hash matches its own payload. Harmless for old v1.3 tickets too: the
-- hash is of whatever string is already in `payload`, whatever protocol
-- version produced it.
UPDATE order_ticket
SET payload_hash = SHA2(payload, 256)
WHERE payload_hash IS NULL AND payload <> '';

-- The claim lookup's actual key going forward. Unique, not just indexed:
-- two rows must never be claimable by the same payload, the same
-- guarantee `serial` used to give as a primary key.
CREATE UNIQUE INDEX uq_order_ticket_payload_hash
ON order_ticket (payload_hash);

-- error_log.ticket_serial named an order_ticket row by the old protocol's
-- serial; qrproto payloads have none, so ticket_key -- a payload hash,
-- order/qr_to_recipe.py's document["ticket_key"] -- replaced it.
--
-- No AFTER clause: the column it used to sit after is gone, and naming a
-- missing column is a hard error rather than one db_core.py forgives.
ALTER TABLE error_log
ADD COLUMN ticket_key VARCHAR(64) NULL;

-- Dropped 2026-08-27. It was never backfilled -- there is no payload on
-- hand for an old error_log row to hash -- so it held values only for rows
-- written before ticket_key existed, and by then nothing wrote to it and
-- nothing had ever read it. An installation upgrading past this line loses
-- those old serials; they named tickets under a protocol the machine no
-- longer speaks.
ALTER TABLE error_log
DROP COLUMN ticket_serial;

-- Kept for installations upgrading through this point in history: the
-- column and this index are both dropped a few statements below.
CREATE INDEX idx_error_log_ticket_key ON error_log (ticket_key);

-- Dropped 2026-09-07. Three columns nothing read.
--
--   source    'runner' or 'flow' in practice -- which FILE noticed the
--             fault, not what broke. The person reading the log is
--             standing at the machine and already knows.
--   order_id  a 32-hex id the screen showed eight characters of, and
--             nothing could be reached with. The ticket -> faults link
--             runs on ticket_key, which stays.
--   detail    a JSON blob folded behind a disclosure triangle. What a
--             person needs from a fault is now written into `message`.
--
-- Existing values go with the columns. The rows as they stood are in
-- database/backup_before_drop_error_columns_07092026_133906.sql.
--
-- idx_error_log_order was on order_id alone, so MySQL drops it here too.
-- Re-running is safe: error 1091 (column already absent) is in
-- IGNORED_SCHEMA_ERROR_CODES, the same way the ticket_serial drop above
-- is.
ALTER TABLE error_log
DROP COLUMN source;

ALTER TABLE error_log
DROP COLUMN order_id;

ALTER TABLE error_log
DROP COLUMN detail;

-- Dropped 2026-09-07, right after the three above. Unlike those, these
-- two were in use; the shop asked for them gone anyway, so what they did
-- is recorded rather than lost.
--
--   category    'cancelled', 'weight_mismatch', 'ticket', 'hardware' --
--               every row had one. It drew the LOẠI column, filled the
--               "Loại lỗi" dropdown, was one of the two things the purge
--               button could narrow by, and backed --category/--summary.
--   ticket_key  the SHA-256 of a QR payload, the same value as
--               order_ticket.payload_hash. It was the whole "N sự cố ›"
--               link from the Vé QR screen; 46 of 142 rows had one.
--
-- That link is back, and this table did not change to get it: the
-- ticket's serial rides in the head of `message` as a "[Vé #123]" tag,
-- written and read by database/error_log.py. Nothing below needs undoing
-- and no migration follows -- the point of doing it that way was that
-- the schema stays exactly as these statements leave it.
--
-- idx_error_log_ticket_key was on (ticket_key) alone and goes with the
-- column. idx_error_log_category was on (category, created_at): MySQL
-- drops only the dead half and leaves a live index on (created_at) that
-- exactly duplicates idx_error_log_time, so it is dropped by name below.
ALTER TABLE error_log
DROP COLUMN category;

ALTER TABLE error_log
DROP COLUMN ticket_key;

ALTER TABLE error_log
DROP INDEX idx_error_log_category;

-- Dropped 2026-09-07. CHAR(32), the runner's uuid for the order that
-- claimed this ticket. Nothing ever looked a ticket up by it -- no WHERE,
-- no JOIN, no index; every lifecycle operation finds its row by
-- payload_hash. It was shipped to the admin page for a link that died
-- with error_log.ticket_key, SELECTed by recent() and never printed, and
-- kept by mark_failed() to tie a failure to error_log.order_id, which had
-- been dropped hours earlier.
--
-- What it cost: the exact key from a ticket into order/flow.log. That is
-- made by time now -- one order runs at a time, and the row has
-- scanned_at and completed_at. See
-- database/migrate_drop_ticket_order_id.sql.
ALTER TABLE order_ticket
DROP COLUMN order_id;

-- ------------------------------------------------------------
-- 2. TRIGGERS
-- Tự đồng bộ in_stock sau mọi INSERT/UPDATE amount hoặc threshold.
-- amount bằng threshold_gram vẫn được tính là còn hàng.
-- ------------------------------------------------------------

DROP TRIGGER IF EXISTS trg_all_ingredient_before_insert;

DROP TRIGGER IF EXISTS trg_all_ingredient_before_update;

DROP TRIGGER IF EXISTS trg_ingredient_before_insert;

CREATE TRIGGER trg_ingredient_before_insert
BEFORE INSERT ON ingredient
FOR EACH ROW
SET NEW.in_stock = IF(
    NEW.amount >= NEW.threshold_gram,
    TRUE,
    FALSE
);

DROP TRIGGER IF EXISTS trg_ingredient_before_update;

CREATE TRIGGER trg_ingredient_before_update
BEFORE UPDATE ON ingredient
FOR EACH ROW
SET NEW.in_stock = IF(
    NEW.amount >= NEW.threshold_gram,
    TRUE,
    FALSE
);

-- ------------------------------------------------------------
-- 2b. DRINK STOCK FOLLOWS INGREDIENT STOCK
--
-- drink.in_stock is derived: a drink is in stock only when it has a
-- recipe and every ingredient in that recipe is in stock.
--
-- inventory_service.refresh_drink_instock() computes the same thing, but
-- only when the application is the one changing stock. An amount edited
-- straight in SQL -- phpMyAdmin, a manual UPDATE, a restored backup --
-- fired the ingredient trigger above and left every drink using it
-- claiming to be in stock. These triggers close that gap, so the derived
-- value cannot go stale no matter who writes.
--
-- Each body is a single statement on purpose: the SQL splitter in
-- db_core.py cuts on semicolons, so a BEGIN ... END block would be torn
-- in half.
--
-- NOTE: drink.available is deliberately NOT touched here. It is the
-- staff's own "we are offering this" switch, set from the admin GUI, and
-- must stay independent of whether the ingredients happen to be present.
-- ------------------------------------------------------------

DROP TRIGGER IF EXISTS trg_ingredient_after_update;

CREATE TRIGGER trg_ingredient_after_update
AFTER UPDATE ON ingredient
FOR EACH ROW
UPDATE drink
SET drink.in_stock = (
    SELECT IF(
        COUNT(*) > 0 AND MIN(ing.in_stock) = 1,
        TRUE,
        FALSE
    )
    FROM recipe AS rec
    JOIN ingredient AS ing
        ON ing.ingredient_id = rec.ingredient_id
    WHERE rec.drink_id = drink.drink_id
)
WHERE drink.drink_id IN (
    SELECT rec2.drink_id
    FROM recipe AS rec2
    WHERE rec2.ingredient_id = NEW.ingredient_id
);

-- A recipe change alters which ingredients a drink depends on, so the
-- same derived value has to be recomputed for the affected drink.

DROP TRIGGER IF EXISTS trg_recipe_after_insert;

CREATE TRIGGER trg_recipe_after_insert
AFTER INSERT ON recipe
FOR EACH ROW
UPDATE drink
SET drink.in_stock = (
    SELECT IF(
        COUNT(*) > 0 AND MIN(ing.in_stock) = 1,
        TRUE,
        FALSE
    )
    FROM recipe AS rec
    JOIN ingredient AS ing
        ON ing.ingredient_id = rec.ingredient_id
    WHERE rec.drink_id = drink.drink_id
)
WHERE drink.drink_id = NEW.drink_id;

DROP TRIGGER IF EXISTS trg_recipe_after_update;

-- Both drinks are refreshed, because a moved row leaves one recipe and
-- joins another.
CREATE TRIGGER trg_recipe_after_update
AFTER UPDATE ON recipe
FOR EACH ROW
UPDATE drink
SET drink.in_stock = (
    SELECT IF(
        COUNT(*) > 0 AND MIN(ing.in_stock) = 1,
        TRUE,
        FALSE
    )
    FROM recipe AS rec
    JOIN ingredient AS ing
        ON ing.ingredient_id = rec.ingredient_id
    WHERE rec.drink_id = drink.drink_id
)
WHERE drink.drink_id IN (OLD.drink_id, NEW.drink_id);

DROP TRIGGER IF EXISTS trg_recipe_after_delete;

CREATE TRIGGER trg_recipe_after_delete
AFTER DELETE ON recipe
FOR EACH ROW
UPDATE drink
SET drink.in_stock = (
    SELECT IF(
        COUNT(*) > 0 AND MIN(ing.in_stock) = 1,
        TRUE,
        FALSE
    )
    FROM recipe AS rec
    JOIN ingredient AS ing
        ON ing.ingredient_id = rec.ingredient_id
    WHERE rec.drink_id = drink.drink_id
)
WHERE drink.drink_id = OLD.drink_id;

-- ------------------------------------------------------------
-- 3. DEFAULT INGREDIENT DATA
-- Khi update, không ghi đè amount đang vận hành.
-- ------------------------------------------------------------

-- Free unique names before assigning the new physical pump layout.
DROP TEMPORARY TABLE IF EXISTS ingredient_inventory_snapshot;

CREATE TEMPORARY TABLE ingredient_inventory_snapshot AS
SELECT
    ingredient_name,
    amount
FROM ingredient;

UPDATE ingredient
SET ingredient_name = CONCAT('__ingredient_', ingredient_id)
WHERE ingredient_id BETWEEN 1 AND 10;

INSERT INTO ingredient (
    ingredient_id,
    ingredient_name,
    type,
    data_type,
    amount,
    gpio
)
VALUES
    -- gpio is a SLOT, not a bare number: 'G26' is BCM pin 26 driving a
    -- pump, 'P01' is position 1 on the manual panel. These were plain
    -- integers until the slot migration, and ON DUPLICATE KEY UPDATE
    -- below writes gpio on every re-run -- so a bare 26 here did not
    -- merely look stale, it overwrote 'G26' with a value
    -- ck_ingredient_gpio refuses, and every re-run of this file stopped
    -- right here. See gpio_slot() in database/db_core.py.
    (1,  'Water',            'PUMP',   'weight',      7825, 'G26'),
    (2,  'Tea',              'PUMP',   'weight',      4360, 'G15'),
    (3,  'Coffee',           'PUMP',   'weight',      1870, 'G21'),
    (4,  'Peach Syrup',      'PUMP',   'weight',      2415, 'G20'),
    (5,  'Strawberry Syrup', 'PUMP',   'weight',      2130, 'G16'),
    (6,  'Soda Water',       'PUMP',   'weight',      6140, 'G12'),
    -- MANUAL gpio is the panel position, not a Raspberry Pi pin.
    -- Panel 8 and panel 13 are not wired, so nothing is placed there.
    (7,  'Sugar',            'PUMP',   'percentage',  3580, 'G13'),
    (8,  'Milk',             'MANUAL', 'boolean',     2945, 'P01'),
    (9,  'Cream',            'MANUAL', 'boolean',     1260, 'P02'),
    (10, 'Chocolate',        'MANUAL', 'boolean',     1685, 'P03'),
    (11, 'Strawberry',       'MANUAL', 'boolean',     1000, 'P04'),
    (12, 'Ice',              'MANUAL', 'boolean',     5000, 'P05'),
    (13, 'Pearls',           'MANUAL', 'boolean',     1500, 'P06')
ON DUPLICATE KEY UPDATE
    ingredient_name = VALUES(ingredient_name),
    type = VALUES(type),
    data_type = VALUES(data_type),
    gpio = VALUES(gpio);

-- Preserve stock by ingredient name while ingredients move to new IDs.
UPDATE ingredient AS target
JOIN ingredient_inventory_snapshot AS snapshot
    ON snapshot.ingredient_name = target.ingredient_name
SET target.amount = snapshot.amount;

DROP TEMPORARY TABLE ingredient_inventory_snapshot;

-- ------------------------------------------------------------
-- 3b. DEFAULT GLASS DATA
-- Glass IDs are fixed because drink.glass_id references them, and because
-- `art` is the filename the bartender screen looks for -- changing an id
-- would silently repoint every drink that used it.
-- ------------------------------------------------------------

INSERT INTO glass (
    glass_id,
    glass_name,
    art,
    capacity_ml,
    sort_order
)
VALUES
    (3001, 'Ly cao',        'highball',  350, 10),
    (3002, 'Ly lùn',        'rocks',     300, 20),
    (3003, 'Ly hurricane',  'hurricane', 440, 30),
    (3004, 'Ly martini',    'martini',   210, 40),
    (3005, 'Ly coupe',      'coupe',     240, 50),
    (3006, 'Ca đồng',       'mug',       450, 60)
ON DUPLICATE KEY UPDATE
    glass_name = VALUES(glass_name),
    art = VALUES(art),
    capacity_ml = VALUES(capacity_ml),
    sort_order = VALUES(sort_order);

-- ------------------------------------------------------------
-- 3c. DEFAULT DRINK TYPE DATA
-- Fixed ids for the same reason as glass: drink.drink_type_id references
-- them, and `art` is the filename the bartender screen looks for.
--
-- Six rows because six is what a shop actually serves. Anything past this
-- is a new row here, not a code change: nothing in the GUI names an ice
-- kind, it draws whatever `art` it is given and falls back to a generic
-- ice cube for one it has no drawing for.
-- ------------------------------------------------------------

INSERT INTO drink_type (
    drink_type_id,
    type_name,
    art,
    method,
    detail,
    sort_order
)
VALUES
    (5001, 'Đá viên', 'cube',
     'Dựng thẳng trong ly',
     'Topping xuống đáy, đá đầy 3/4 ly, rồi máy rót lên trên.',
     10),

    (5002, 'Đá nugget', 'nugget',
     'Dựng thẳng trong ly',
     'Đá nugget đầy ly — mềm, tan nhanh, nên rót ngay khi vừa lấy đá.',
     20),

    (5003, 'Đá bào', 'crushed',
     'Rót lên đá bào',
     'Đá bào vun cao trên miệng ly, rót chậm để đá không sụp.',
     30),

    (5004, 'Xay đá', 'blend',
     'Xay với đá',
     'Máy rót vào cối, thêm đá rồi xay đến khi mịn, đổ ra ly phục vụ.',
     40),

    (5005, 'Không đá', 'none',
     'Rót thẳng, không đá',
     'Không cho đá. Ly nên được làm lạnh trước nếu có.',
     50),

    (5006, 'Đồ uống nóng', 'hot',
     'Phục vụ nóng',
     'Tráng ly bằng nước nóng trước khi rót để giữ nhiệt.',
     60)
ON DUPLICATE KEY UPDATE
    type_name = VALUES(type_name),
    art = VALUES(art),
    method = VALUES(method),
    -- detail is deliberately absent from this list. It is the one column
    -- here with an editor behind it -- the admin recipe editor writes it
    -- -- and re-running database.sql must not throw away what somebody
    -- typed there. The rest are structural and have no editor yet.
    sort_order = VALUES(sort_order);

-- Removes the column from an installation that has it. It listed the
-- bar tools a method calls for ("Thìa bar · Muôi đá"), and it was dropped
-- because nobody on the floor reads it off the screen: the person making
-- the drink already knows what a built drink needs, and the prep card is
-- worth more with one fact fewer on it.
ALTER TABLE drink_type DROP COLUMN tools;

-- ------------------------------------------------------------
-- 4. DEFAULT DRINK DATA
-- ------------------------------------------------------------

-- glass_id, drink_type_id and garnish are seeded here so a FRESH install
-- shows the prep card fully filled in. They are deliberately absent from
-- the ON DUPLICATE KEY UPDATE list below: on an existing database these
-- are somebody's choices, and re-running database.sql must never reset
-- them the way it refreshes a name or an image.
INSERT INTO drink (
    drink_id,
    drink_name,
    image,
    in_stock,
    glass_id,
    drink_type_id,
    garnish
)
VALUES
    (1001, 'Peach Tea',       'recipe/image/Peach Tea.webp',       TRUE,
     3001, 5001, 'Ống hút to, lát đào'),
    (1002, 'Milk Tea',        'recipe/image/Milk Tea.webp',        TRUE,
     3001, 5001, 'Ống hút to, nắp dập'),
    (1003, 'Milk Coffee',     'recipe/image/Milk Coffee.webp',     TRUE,
     3002, 5001, 'Ống hút nhỏ'),
    (1004, 'Strawberry Soda', 'recipe/image/Strawberry Soda.webp', TRUE,
     3003, 5003, 'Lát chanh, lá bạc hà'),
    (1005, 'Chocolate Milk',  'recipe/image/Chocolate Milk.webp',  TRUE,
     3001, 5004, 'Kem tươi, bột cacao')
ON DUPLICATE KEY UPDATE
    drink_name = VALUES(drink_name),
    image = VALUES(image);

-- ------------------------------------------------------------
-- 5. DEFAULT CATEGORY DATA
-- Category IDs are fixed because drink_category_mapping references them.
-- ------------------------------------------------------------

INSERT INTO category (
    category_id,
    category_name,
    description
)
VALUES
    (4001, 'Summer',     'Đồ uống giải nhiệt mùa hè'),
    (4002, 'Soda',       'Các loại đồ uống có ga'),
    (4003, 'Tea',        'Các loại trà thanh mát'),
    (4004, 'Coffee',     'Cà phê các loại'),
    (4005, 'Bestseller', 'Danh sách đồ uống bán chạy nhất')
ON DUPLICATE KEY UPDATE
    category_name = VALUES(category_name),
    description = VALUES(description);

-- Floors for the id ranges.
--
-- Seeding explicit ids already pushes AUTO_INCREMENT past them, so on a
-- normal install these are redundant. They are here for the install where
-- they are not: a table created but never seeded starts its counter at 1,
-- and the first drink added by hand would land on id 1 -- outside its
-- range, and colliding with the seed the moment anyone ran it.
--
-- Harmless to re-run: MySQL ignores an AUTO_INCREMENT lower than the
-- highest id present, so this can never pull a live counter backwards.
ALTER TABLE drink    AUTO_INCREMENT = 1001;
ALTER TABLE glass    AUTO_INCREMENT = 3001;
ALTER TABLE category AUTO_INCREMENT = 4001;
ALTER TABLE drink_type AUTO_INCREMENT = 5001;

INSERT INTO drink_category_mapping (
    drink_id,
    category_id
)
VALUES
    (1001, 4003),
    (1001, 4001),
    (1002, 4003),
    (1002, 4005),
    (1003, 4004),
    (1004, 4002),
    (1004, 4001),
    (1005, 4005)
ON DUPLICATE KEY UPDATE
    category_id = VALUES(category_id);

-- ------------------------------------------------------------
-- 6. RECIPE
-- recipe is the direct drink -> ingredient mapping.
-- Các dòng trùng khóa sẽ được cập nhật target_gram.
-- ------------------------------------------------------------

INSERT IGNORE INTO recipe (
    drink_id,
    step_no,
    ingredient_id,
    target_gram
)
VALUES
    -- Peach Tea
    (1, 1, 1, 120),
    (1, 1, 2, 80),
    (1, 2, 4, 30),

    -- Milk Tea
    (2, 1, 2, 100),
    (2, 1, 1, 50),

    -- Milk Coffee
    (3, 1, 3, 60),
    (3, 1, 1, 30),

    -- Strawberry Soda
    (4, 1, 5, 30),
    (4, 1, 6, 150),

    -- Chocolate Milk
    (5, 1, 1, 50);

-- ------------------------------------------------------------
-- 7. CALCULATE THRESHOLD
-- threshold = lượng lớn nhất của nguyên liệu trong một recipe * 110%
-- Nếu cùng nguyên liệu xuất hiện nhiều bước trong một recipe, tổng các bước
-- được tính trước khi lấy giá trị lớn nhất.
-- ------------------------------------------------------------

UPDATE ingredient AS target
LEFT JOIN (
    SELECT
        ingredient_id,
        ROUND(MAX(recipe_total_gram) * 1.10, 2) AS threshold_gram
    FROM (
        SELECT
            drink_id,
            ingredient_id,
            SUM(target_gram) AS recipe_total_gram
        FROM recipe
        GROUP BY
            drink_id,
            ingredient_id
    ) AS recipe_usage
    GROUP BY ingredient_id
) AS calculated
    ON calculated.ingredient_id = target.ingredient_id
SET target.threshold_gram = COALESCE(
    calculated.threshold_gram,
    0
);

-- ------------------------------------------------------------
-- 8. CALCULATE DRINK STOCK
-- Món chỉ còn hàng khi có recipe và mọi nguyên liệu đều in_stock.
-- ------------------------------------------------------------

UPDATE drink AS target
LEFT JOIN (
    SELECT
        recipe.drink_id,
        COUNT(recipe.ingredient_id) AS ingredient_count,
        MIN(
            CASE
                WHEN ingredient.in_stock = TRUE THEN 1
                ELSE 0
            END
        ) AS every_ingredient_instock
    FROM recipe AS recipe
    LEFT JOIN ingredient AS ingredient
        ON ingredient.ingredient_id = recipe.ingredient_id
    GROUP BY recipe.drink_id
) AS stock
    ON stock.drink_id = target.drink_id
SET target.in_stock = IF(
    COALESCE(stock.ingredient_count, 0) > 0
    AND COALESCE(stock.every_ingredient_instock, 0) = 1,
    TRUE,
    FALSE
);
