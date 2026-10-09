-- ============================================================
-- DRINK TYPE: how a drink is built, and on what ice
--
-- Adds one reference table and two columns:
--
--   drink_type            cube / nugget / crushed / blend / none / hot,
--                         each carrying the build method that goes with
--                         it, its one-line description and its tools
--   drink.drink_type_id   which of those this drink uses (NULL = unset)
--   drink.garnish         free text, per drink
--
-- WHY A TABLE AND NOT AN ENUM ON drink
--   The same reasoning as `glass`, which this is modelled on. An ENUM
--   holds the word "cube" and nothing else; the bartender screen needs a
--   picture, a name, a method and a tool list beside it. Adding a
--   seventh ice kind is then one INSERT here instead of an ALTER on the
--   drink table plus a code change.
--
-- WHY THE ICE AND THE METHOD SHARE A ROW
--   They are never chosen apart in practice. Nobody blends over cubes,
--   and "nugget" already says the cup is filled before the machine
--   pours. Two tables would have produced a grid of combinations no bar
--   has ever served.
--
-- VIETNAMESE ONLY
--   This screen is read by staff standing at the machine, and they read
--   Vietnamese. An earlier draft carried type_name_en / method_en /
--   detail_en / tools_en; the DROPs at the end remove them from a
--   database that took that draft. The bartender screen's EN toggle
--   therefore shows these four facts in Vietnamese whatever language it
--   is set to -- which is the deliberate trade, not a bug.
--
-- SAFE TO RE-RUN
--   Every statement is IF NOT EXISTS, ON DUPLICATE KEY UPDATE, or
--   guarded by a lookup against information_schema. Nothing here reads
--   or changes an existing drink's data except to add the two NULL
--   columns, so a drink that is mid-pour is unaffected.
--
-- This is the same content database.sql now carries. Running either one
-- gets you there; this file exists so an installation can take the
-- change on its own, without re-running the seeds alongside it.
-- ============================================================

CREATE TABLE IF NOT EXISTS drink_type (
    drink_type_id INT AUTO_INCREMENT PRIMARY KEY,
    type_name VARCHAR(60) NOT NULL,
    -- The one machine key: names ice-<art>.png and, failing that, the
    -- built-in drawing. See database.sql for why it is not type_name.
    art VARCHAR(40) NOT NULL UNIQUE,
    method VARCHAR(60) NULL,
    detail VARCHAR(200) NULL,
    tools VARCHAR(120) NULL,
    sort_order INT NOT NULL DEFAULT 0
) ENGINE=InnoDB;

ALTER TABLE drink_type AUTO_INCREMENT = 5001;

-- This runs BEFORE the seed below, not after. On a database that took
-- the earlier draft, `code` is NOT NULL with no default, and an INSERT
-- that does not name it fails under strict mode even on the duplicate-key
-- path. Dropping first is what lets one file serve both a fresh install
-- and an upgrade.
-- ------------------------------------------------------------
-- Columns an earlier draft of this file created, removed from a database
-- that took that draft: the four English ones, and `code`, which held the
-- same string as `art` and did the same job. Guarded the same way as the
-- ADDs above, so this section is a no-op on a database that never had
-- them. `art` picks up the UNIQUE that `code` used to carry.
-- ------------------------------------------------------------
SET @sql := (
    SELECT IF(COUNT(*) = 0, 'DO 0',
              CONCAT('ALTER TABLE drink_type ',
                     GROUP_CONCAT(CONCAT('DROP COLUMN ', COLUMN_NAME))))
    FROM information_schema.COLUMNS
    WHERE TABLE_SCHEMA = DATABASE()
      AND TABLE_NAME = 'drink_type'
      AND COLUMN_NAME IN ('type_name_en', 'method_en', 'detail_en',
                          'tools_en', 'code'));
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

SET @has_art_unique := (
    SELECT COUNT(*) FROM information_schema.STATISTICS
    WHERE TABLE_SCHEMA = DATABASE()
      AND TABLE_NAME = 'drink_type'
      AND COLUMN_NAME = 'art'
      AND NON_UNIQUE = 0);

SET @sql := IF(@has_art_unique = 0,
    'ALTER TABLE drink_type ADD UNIQUE KEY uq_drink_type_art (art)',
    'DO 0');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

SET @has_glass_en := (
    SELECT COUNT(*) FROM information_schema.COLUMNS
    WHERE TABLE_SCHEMA = DATABASE()
      AND TABLE_NAME = 'glass'
      AND COLUMN_NAME = 'glass_name_en');

SET @sql := IF(@has_glass_en = 1,
    'ALTER TABLE glass DROP COLUMN glass_name_en',
    'DO 0');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

-- sort_order is the order the admin picker lists these in -- the order a
-- bar thinks about ice, not the order the ids happen to run. Steps of 10
-- so a new kind can be slotted between two without renumbering the rest.
INSERT INTO drink_type (
    drink_type_id, type_name, art, method, detail, tools, sort_order
)
VALUES
    (5001, 'Đá viên', 'cube',
     'Dựng thẳng trong ly',
     'Topping xuống đáy, đá đầy 3/4 ly, rồi máy rót lên trên.',
     'Thìa bar · Muôi đá', 10),

    (5002, 'Đá nugget', 'nugget',
     'Dựng thẳng trong ly',
     'Đá nugget đầy ly — mềm, tan nhanh, nên rót ngay khi vừa lấy đá.',
     'Thìa bar · Muôi đá', 20),

    (5003, 'Đá bào', 'crushed',
     'Rót lên đá bào',
     'Đá bào vun cao trên miệng ly, rót chậm để đá không sụp.',
     'Muôi đá · Thìa bar', 30),

    (5004, 'Xay đá', 'blend',
     'Xay với đá',
     'Máy rót vào cối, thêm đá rồi xay đến khi mịn, đổ ra ly phục vụ.',
     'Máy xay · Cối xay', 40),

    (5005, 'Không đá', 'none',
     'Rót thẳng, không đá',
     'Không cho đá. Ly nên được làm lạnh trước nếu có.',
     'Thìa bar', 50),

    (5006, 'Đồ uống nóng', 'hot',
     'Phục vụ nóng',
     'Tráng ly bằng nước nóng trước khi rót để giữ nhiệt.',
     'Ca đồng · Thìa dài', 60)
ON DUPLICATE KEY UPDATE
    type_name = VALUES(type_name),
    art = VALUES(art),
    method = VALUES(method),
    -- detail is deliberately NOT refreshed: it is editable in the admin
    -- recipe editor, so re-running this file must not overwrite what
    -- somebody wrote there. The other columns are structural and have no
    -- editor behind them yet.
    tools = VALUES(tools),
    sort_order = VALUES(sort_order);

-- The two columns on drink. MySQL has no ADD COLUMN IF NOT EXISTS, so
-- each one is asked for only when information_schema says it is missing
-- -- which is what makes this file safe to run twice.
SET @has_type := (
    SELECT COUNT(*) FROM information_schema.COLUMNS
    WHERE TABLE_SCHEMA = DATABASE()
      AND TABLE_NAME = 'drink'
      AND COLUMN_NAME = 'drink_type_id');

SET @sql := IF(@has_type = 0,
    'ALTER TABLE drink ADD COLUMN drink_type_id INT NULL',
    'DO 0');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

SET @has_garnish := (
    SELECT COUNT(*) FROM information_schema.COLUMNS
    WHERE TABLE_SCHEMA = DATABASE()
      AND TABLE_NAME = 'drink'
      AND COLUMN_NAME = 'garnish');

SET @sql := IF(@has_garnish = 0,
    'ALTER TABLE drink ADD COLUMN garnish VARCHAR(120) NULL',
    'DO 0');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

SET @has_fk := (
    SELECT COUNT(*) FROM information_schema.TABLE_CONSTRAINTS
    WHERE CONSTRAINT_SCHEMA = DATABASE()
      AND TABLE_NAME = 'drink'
      AND CONSTRAINT_NAME = 'fk_drink_drink_type');

SET @sql := IF(@has_fk = 0,
    'ALTER TABLE drink ADD CONSTRAINT fk_drink_drink_type '
    'FOREIGN KEY (drink_type_id) REFERENCES drink_type (drink_type_id) '
    'ON DELETE SET NULL ON UPDATE CASCADE',
    'DO 0');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

-- What landed.
SELECT
    (SELECT COUNT(*) FROM drink_type)                        AS drink_types,
    (SELECT COUNT(*) FROM drink WHERE drink_type_id IS NULL
        AND deleted_at IS NULL)                              AS drinks_without_a_type;
