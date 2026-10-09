-- ============================================================
-- HARDWARE SLOTS: ingredient.gpio becomes a prefixed label
--
--   PUMP    a BCM pin driving a pump       26 -> 'G26'
--   MANUAL  a position on the panel         1 -> 'P01'
--
-- WHY
--   The column held two different things and the value never said which.
--   A 1 in it was pin 1 or panel position 1 depending on the row's type,
--   so nothing could be read without fetching the type to interpret it.
--   The prefix makes a slot self-describing: in a log, in a query, on the
--   admin screen.
--
--   The NUMBER is unchanged. G26 is still pin 26; nothing about the wiring
--   moves, and database/db_core.gpio_number() reads the digits back out.
--
-- SAFE TO RE-RUN
--   Rows already carrying a prefix are left alone by the WHERE clauses.
--
-- BEFORE RUNNING
--   Take a backup.
-- ============================================================

-- The CHECK reads the column as a number ("gpio >= 0") and would refuse
-- every value below. Dropped before the type changes, re-made after in
-- terms the new format can satisfy.
ALTER TABLE ingredient DROP CHECK ck_ingredient_gpio;

ALTER TABLE ingredient MODIFY COLUMN gpio VARCHAR(8) NULL;

START TRANSACTION;

-- LPAD to two digits, matching the panel labels already in use.
UPDATE ingredient
   SET gpio = CONCAT('G', LPAD(gpio, 2, '0'))
 WHERE type = 'PUMP'
   AND gpio IS NOT NULL
   AND gpio REGEXP '^[0-9]+$';

UPDATE ingredient
   SET gpio = CONCAT('P', LPAD(gpio, 2, '0'))
 WHERE type = 'MANUAL'
   AND gpio IS NOT NULL
   AND gpio REGEXP '^[0-9]+$';

COMMIT;

-- A slot is a letter and at least one digit, or nothing at all. This is
-- what stops a bare number creeping back in and being ambiguous again.
ALTER TABLE ingredient
  ADD CONSTRAINT ck_ingredient_gpio
  CHECK (gpio IS NULL OR gpio REGEXP '^[GP][0-9]+$');

-- ============================================================
-- VERIFY
-- ============================================================
SELECT ingredient_id, ingredient_name, type, gpio
  FROM ingredient ORDER BY type DESC, ingredient_id;

SELECT 'rows still bare (must be 0)' AS check_name,
       COUNT(*) AS must_be_zero
  FROM ingredient WHERE gpio REGEXP '^[0-9]+$'
UNION ALL
SELECT 'PUMP not prefixed G', COUNT(*) FROM ingredient
 WHERE type = 'PUMP' AND gpio IS NOT NULL AND gpio NOT LIKE 'G%'
UNION ALL
SELECT 'MANUAL not prefixed P', COUNT(*) FROM ingredient
 WHERE type = 'MANUAL' AND gpio IS NOT NULL AND gpio NOT LIKE 'P%';
