-- ============================================================
-- THREE COLUMNS OUT OF error_log: source, order_id, detail
--
-- The fault log is read on one screen, by one kind of person: whoever is
-- standing at the machine asking what just went wrong. These three
-- columns were written for a different reader -- someone joining the log
-- to other tables afterwards -- and on the screen they were noise:
--
--   source     two values in practice, 'runner' and 'flow', which is a
--              statement about which FILE noticed the fault, not about
--              what broke. The person reading already knows they are
--              looking at the machine.
--   order_id   a 32-hex id shown eight characters wide. Nothing on the
--              page can be reached with it -- the link from a QR ticket
--              to its faults runs on ticket_key, which stays.
--   detail     a JSON blob folded behind "Chi tiết". The numbers in it
--              (pumps, grams, ingredient_id) are already in the message
--              for the cases anybody opened it for.
--
-- WHAT IS NOT TOUCHED
--   ticket_key stays, and with it the Vé QR → faults link.
--   category, severity, step_label, step_type, drink_name and message
--   are what the screen actually reads, and all stay.
--
-- IRREVERSIBLE
--   Dropping a column drops its data. The rows as they stood before this
--   ran are in database/backup_before_drop_error_columns_07092026_133906.sql
--   -- restore from there if any of it is ever wanted back.
--
-- SAFE TO RE-RUN
--   Each DROP is guarded by information_schema, so a second run finds the
--   column already gone and does nothing. idx_error_log_order is on
--   order_id alone, so MySQL drops the index with the column.
--
--   mysql -u root -p beveragepos < database/migrate_drop_error_columns.sql
--   sudo systemctl restart flexmix-backend
-- ============================================================

SET @db := DATABASE();

-- source ------------------------------------------------------------
SET @sql := (
  SELECT IF(COUNT(*) > 0,
            'ALTER TABLE error_log DROP COLUMN source',
            'DO 0')
    FROM information_schema.COLUMNS
   WHERE TABLE_SCHEMA = @db
     AND TABLE_NAME = 'error_log'
     AND COLUMN_NAME = 'source'
);
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

-- order_id (takes idx_error_log_order with it) -----------------------
SET @sql := (
  SELECT IF(COUNT(*) > 0,
            'ALTER TABLE error_log DROP COLUMN order_id',
            'DO 0')
    FROM information_schema.COLUMNS
   WHERE TABLE_SCHEMA = @db
     AND TABLE_NAME = 'error_log'
     AND COLUMN_NAME = 'order_id'
);
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

-- detail -------------------------------------------------------------
SET @sql := (
  SELECT IF(COUNT(*) > 0,
            'ALTER TABLE error_log DROP COLUMN detail',
            'DO 0')
    FROM information_schema.COLUMNS
   WHERE TABLE_SCHEMA = @db
     AND TABLE_NAME = 'error_log'
     AND COLUMN_NAME = 'detail'
);
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;
