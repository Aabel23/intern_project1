-- ============================================================
-- ID RANGES: renumber drink, glass and category
--
--   ingredient   0001-0999   (unchanged -- 0001 IS 1, already in range)
--   drink        1001-1999   drink_id + 1000
--   glass        3001-3999   glass_id  + 3000
--   category     4001-4999   category_id + 4000
--
-- WHY A PLAIN OFFSET IS SAFE HERE
--   Every current id is far below its offset (drink tops out at 47,
--   glass at 6, category at 5), so id + offset cannot collide with an id
--   that has not been moved yet. No temporary table, no two-pass
--   renumber, and every old id is recoverable by subtracting.
--
-- WHY FOREIGN_KEY_CHECKS IS TURNED OFF
--   Only fk_drink_glass is ON UPDATE CASCADE. The other three are
--   NO ACTION, which REJECTS an update to a parent key that children
--   still point at -- so the parent and its children have to move
--   together, inside one transaction, with the checks stood down.
--   They are turned back on and the result is verified at the end.
--
--   With the checks off, CASCADE does not fire either, so
--   drink.glass_id is updated by hand below rather than left to it.
--
-- THE TWO TABLES WITH NO FOREIGN KEY
--   order_ticket.drink_id and error_log.drink_id reference a drink but
--   declare no constraint. Nothing would have warned about them; they
--   are the reason this file exists rather than three UPDATE statements
--   typed at a prompt.
--
-- BEFORE RUNNING
--   Take a backup. database/backup_before_id_ranges_*.sql is one.
-- ============================================================

-- Orphans that exist ALREADY. order_ticket and error_log keep rows for
-- drinks that were later purged from the bin -- test drinks, mostly -- and
-- those rows are meant to survive: order_ticket.drink_name holds the name
-- as sold precisely so a sale still reads after its drink is gone.
--
-- Counted first so the checks at the end can tell an orphan this migration
-- CREATED from one it merely carried forward. Without this the report says
-- "18 orphans" either way, and the number that matters -- did anything
-- break? -- cannot be read off it.
-- Session variables, not a temporary table: MySQL refuses to reference the
-- same TEMPORARY table twice in one query, and the check below needs each
-- baseline inside a UNION arm.
SET @tickets_orphaned_before = (
  SELECT COUNT(*) FROM order_ticket t
    LEFT JOIN drink d ON d.drink_id = t.drink_id WHERE d.drink_id IS NULL);

SET @errors_orphaned_before = (
  SELECT COUNT(*) FROM error_log e
    LEFT JOIN drink d ON d.drink_id = e.drink_id
    WHERE e.drink_id IS NOT NULL AND d.drink_id IS NULL);

SET FOREIGN_KEY_CHECKS = 0;

START TRANSACTION;

-- Labels already printed carry the OLD sku inside their payload, so they
-- can no longer be redeemed. Marked expired rather than left 'unused', so
-- a customer scanning one is told it has expired instead of meeting an
-- error about a drink that does not exist.
UPDATE order_ticket SET status = 'expired' WHERE status = 'unused';

-- ---- category: 1-5 -> 4001-4005 ----
UPDATE category               SET category_id = category_id + 4000;
UPDATE drink_category_mapping SET category_id = category_id + 4000;

-- ---- glass: 1-6 -> 3001-3006 ----
UPDATE glass SET glass_id = glass_id + 3000;
UPDATE drink SET glass_id = glass_id + 3000 WHERE glass_id IS NOT NULL;

-- ---- drink: 1-47 -> 1001-1047 ----
UPDATE drink                  SET drink_id = drink_id + 1000;
UPDATE recipe                 SET drink_id = drink_id + 1000;
UPDATE drink_category_mapping SET drink_id = drink_id + 1000;
UPDATE order_ticket           SET drink_id = drink_id + 1000;
UPDATE error_log              SET drink_id = drink_id + 1000
                              WHERE drink_id IS NOT NULL;

COMMIT;

SET FOREIGN_KEY_CHECKS = 1;

-- New rows must continue inside the range, not restart below it.
ALTER TABLE drink    AUTO_INCREMENT = 1048;
ALTER TABLE glass    AUTO_INCREMENT = 3007;
ALTER TABLE category AUTO_INCREMENT = 4006;

-- ============================================================
-- VERIFY. Every count below must be 0.
-- ============================================================
SELECT 'drink outside 1001-1999' AS check_name,
       COUNT(*) AS must_be_zero FROM drink
       WHERE drink_id NOT BETWEEN 1001 AND 1999
UNION ALL SELECT 'glass outside 3001-3999', COUNT(*) FROM glass
       WHERE glass_id NOT BETWEEN 3001 AND 3999
UNION ALL SELECT 'category outside 4001-4999', COUNT(*) FROM category
       WHERE category_id NOT BETWEEN 4001 AND 4999
UNION ALL SELECT 'ingredient outside 1-999', COUNT(*) FROM ingredient
       WHERE ingredient_id NOT BETWEEN 1 AND 999
-- Orphans: a child row pointing at a parent that is not there. This is
-- what the disabled checks could have let through.
UNION ALL SELECT 'orphan recipe.drink_id', COUNT(*) FROM recipe r
       LEFT JOIN drink d ON d.drink_id = r.drink_id WHERE d.drink_id IS NULL
UNION ALL SELECT 'orphan recipe.ingredient_id', COUNT(*) FROM recipe r
       LEFT JOIN ingredient i ON i.ingredient_id = r.ingredient_id
       WHERE i.ingredient_id IS NULL
UNION ALL SELECT 'orphan mapping.drink_id', COUNT(*) FROM drink_category_mapping m
       LEFT JOIN drink d ON d.drink_id = m.drink_id WHERE d.drink_id IS NULL
UNION ALL SELECT 'orphan mapping.category_id', COUNT(*) FROM drink_category_mapping m
       LEFT JOIN category c ON c.category_id = m.category_id WHERE c.category_id IS NULL
UNION ALL SELECT 'orphan drink.glass_id', COUNT(*) FROM drink d
       LEFT JOIN glass g ON g.glass_id = d.glass_id
       WHERE d.glass_id IS NOT NULL AND g.glass_id IS NULL
-- The two with no constraint of their own. Compared against the baseline
-- taken before the migration, so what is reported is orphans GAINED --
-- which must be 0 -- not orphans that were always there.
UNION ALL SELECT 'order_ticket orphans gained',
       (SELECT COUNT(*) FROM order_ticket t
          LEFT JOIN drink d ON d.drink_id = t.drink_id WHERE d.drink_id IS NULL)
       - @tickets_orphaned_before
UNION ALL SELECT 'error_log orphans gained',
       (SELECT COUNT(*) FROM error_log e
          LEFT JOIN drink d ON d.drink_id = e.drink_id
          WHERE e.drink_id IS NOT NULL AND d.drink_id IS NULL)
       - @errors_orphaned_before;

-- For the record, and so nobody hunts for a bug that is not there: rows
-- kept for drinks that were purged from the bin long before today.
SELECT @tickets_orphaned_before AS tickets_already_orphaned,
       @errors_orphaned_before  AS errors_already_orphaned;
