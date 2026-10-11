-- ============================================================
-- FLEXMIX DATABASE SCHEMA (bảng + trigger)
-- Dữ liệu mặc định nằm ở seed.sql. Chạy lặp lại được, không xóa tồn kho.
--
-- Bảng: glass, drink_type, drink, category, store_setting,
-- drink_category_mapping, ingredient, order_ticket, error_log, recipe,
-- recipe_action. GPIO nằm trong ingredient.
--
-- Không có migration: đổi schema thì sửa thẳng file này rồi dựng lại
-- bằng apply_database_sql(reset=True). Xem database/schema/apply.py.
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
    -- The recipe editor shows it beside each glass in the picker,
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
    -- here with an editor behind it -- the recipe editor writes it,
    -- so nothing that reseeds this table may overwrite it.
    detail VARCHAR(200) NULL,
    -- The order the glass picker lists these in: the order a bar thinks
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
    -- reference data. Set it in the recipe editor.
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

    -- Every menu query filters on deleted_at, so it is worth an index.
    KEY idx_drink_deleted (deleted_at),

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
--   truth the rebuild does not read, so the management app would write to
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

-- INSERT IGNORE, never ON DUPLICATE KEY UPDATE: re-running the seed
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
    -- would make "fill this bottle" mean "empty it"; NULL makes the stock
    -- screen fall back to its default and SAY on screen that the figure
    -- is a guess. So it stays nullable rather than NOT NULL DEFAULT 0.
    max_gram DECIMAL(10,2) NULL,
    -- Where this ingredient physically lives, and WHICH KIND of place:
    --   PUMP    'G26'  a BCM pin driving a pump
    --   MANUAL  'P01'  a position on the button panel
    -- It was a bare INT, and a 1 in it could be pin 1 or panel 1 with
    -- nothing in the value to say which. See database/core/helpers.gpio_number().
    gpio VARCHAR(8) NULL,
    in_stock BOOLEAN NOT NULL DEFAULT TRUE,

    UNIQUE KEY uq_ingredient_type_gpio (type, gpio),

    CONSTRAINT ck_ingredient_amount CHECK (amount >= 0),
    CONSTRAINT ck_ingredient_threshold CHECK (threshold_gram >= 0),
    CONSTRAINT ck_ingredient_max_gram
        CHECK (max_gram IS NULL OR max_gram > 0),
    -- A slot is a letter and digits, so this has to be a pattern: a
    -- numeric check would pass 'zzz', which MySQL coerces to 0.
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
    -- Protocol v1.4 payloads run up to 224 digits (12 instruction pairs).
    payload VARCHAR(255) NOT NULL,
    -- SHA-256 of payload, the claim lookup's key. qrproto payloads carry no
    -- serial, but every AES-GCM encryption draws a fresh nonce, so the
    -- payload is unique on its own. Unique, not just indexed: two rows must
    -- never be claimable by the same payload.
    payload_hash CHAR(64) NULL,
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

    UNIQUE KEY uq_order_ticket_payload_hash (payload_hash),
    KEY idx_order_ticket_status (status, created_at),
    -- Reports group by day over a date range.
    KEY idx_order_ticket_completed (status, completed_at),

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
--   database/services/error_log.py: recent(), get(), summary().
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
-- is lifted off the scale, recipe_export.py follows the action with a
-- detect step so the machine waits for it back before the next pour. A
-- final garnish leaves it on the scale and needs no such wait.
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

-- Bảng tài khoản của admin_gui cũ; quyền giờ do app + server quản lý.
DROP TABLE IF EXISTS admin_user, role_permission;

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
-- services/inventory.refresh_drink_instock() computes the same thing, but
-- only when the application is the one changing stock. An amount edited
-- straight in SQL -- phpMyAdmin, a manual UPDATE, a restored backup --
-- fired the ingredient trigger above and left every drink using it
-- claiming to be in stock. These triggers close that gap, so the derived
-- value cannot go stale no matter who writes.
--
-- Each body is a single statement on purpose: the SQL splitter in
-- schema/apply.py cuts on semicolons, so a BEGIN ... END block would be torn
-- in half.
--
-- NOTE: drink.available is deliberately NOT touched here. It is the
-- staff's own "we are offering this" switch, set from the management app, and
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
