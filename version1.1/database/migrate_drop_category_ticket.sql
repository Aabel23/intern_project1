-- ============================================================
-- TWO MORE COLUMNS OUT OF error_log: category, ticket_key
--
-- Follows database/migrate_drop_error_columns.sql, which took source,
-- order_id and detail on the same day. Those three were genuinely dead.
-- These two were not, and the shop asked for them anyway -- so what they
-- were doing is written down here rather than lost:
--
--   category    'cancelled', 'weight_mismatch', 'ticket', 'hardware'.
--               Every row had one. It drew the LOẠI column, filled the
--               "Loại lỗi" dropdown, was one of the two things the
--               "Xoá theo bộ lọc" button could narrow by, and backed
--               --category and --summary on the CLI.
--   ticket_key  the SHA-256 of a QR payload, the same value as
--               order_ticket.payload_hash. 46 of 142 rows had one, and
--               it was the entire "N sự cố ›" link from the Vé QR screen
--               to that ticket's own faults.
--
-- WHAT IS LEFT
--   error_id, created_at, severity, drink_id, drink_name, step_label,
--   step_type, message. A fault is now told apart by its severity and
--   read from its sentence.
--
-- WHAT STOPS WORKING
--   * the Vé QR screen no longer counts or links a ticket's faults --
--     nothing joins the two tables any more.
--   * the fault screen loses the LOẠI column and its filter.
--   * "Xoá theo bộ lọc" narrows by date and severity only.
--   * --category and --summary lose their grouping.
--
-- WHAT CAME BACK, LATER THE SAME DAY, WITHOUT THE COLUMN
--   The first of those was the one the shop actually missed, so the link
--   was rebuilt on top of what was left: the ticket's SERIAL is written
--   into the head of error_log.message as a tag -- "[Vé #123] ..." --
--   and read back off it. message is TEXT and was always free-form, so
--   the table is exactly as this migration left it and no further
--   migration exists. See HOW A FAULT STILL NAMES ITS TICKET in
--   database/error_log.py for the format and the three functions that
--   own it.
--
--   It is not retroactive, and cannot be: the 46 rows that had a
--   ticket_key lost it here. Faults recorded from that point on carry a
--   tag; the ones above it show no ticket, which is the truth about them.
--
-- IRREVERSIBLE
--   The rows as they stood are in
--   database/backup_before_drop_category_ticket_07092026_140427.sql.
--   NOTE: .gitignore excludes database/backup_*.sql, so that file lives
--   on this machine only -- copy it elsewhere if it matters.
--
-- THE COMPOSITE INDEX NEEDS DROPPING BY HAND
--   idx_error_log_ticket_key is on (ticket_key) alone, so MySQL drops it
--   with the column. idx_error_log_category is on (category, created_at)
--   -- MySQL drops only the dead half and leaves a live index on
--   (created_at), which is an exact duplicate of idx_error_log_time.
--   Two identical indexes is two b-trees maintained on every insert for
--   one lookup, so the leftover is dropped explicitly below.
--
-- SAFE TO RE-RUN
--   Every step is guarded by information_schema, so a second run finds
--   the columns and the index already gone and does nothing.
--
--   mysql -u root -p beveragepos < database/migrate_drop_category_ticket.sql
--   sudo systemctl restart flexmix-backend
-- ============================================================

SET @db := DATABASE();

-- category (takes idx_error_log_category with it) ---------------------
SET @sql := (
  SELECT IF(COUNT(*) > 0,
            'ALTER TABLE error_log DROP COLUMN category',
            'DO 0')
    FROM information_schema.COLUMNS
   WHERE TABLE_SCHEMA = @db
     AND TABLE_NAME = 'error_log'
     AND COLUMN_NAME = 'category'
);
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

-- ticket_key (takes idx_error_log_ticket_key with it) -----------------
SET @sql := (
  SELECT IF(COUNT(*) > 0,
            'ALTER TABLE error_log DROP COLUMN ticket_key',
            'DO 0')
    FROM information_schema.COLUMNS
   WHERE TABLE_SCHEMA = @db
     AND TABLE_NAME = 'error_log'
     AND COLUMN_NAME = 'ticket_key'
);
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

-- the half-index left behind by dropping category -------------------
-- Named rather than assumed: after the DROP COLUMN above this index is
-- (created_at), the same as idx_error_log_time.
SET @sql := (
  SELECT IF(COUNT(*) > 0,
            'ALTER TABLE error_log DROP INDEX idx_error_log_category',
            'DO 0')
    FROM information_schema.STATISTICS
   WHERE TABLE_SCHEMA = @db
     AND TABLE_NAME = 'error_log'
     AND INDEX_NAME = 'idx_error_log_category'
);
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;
