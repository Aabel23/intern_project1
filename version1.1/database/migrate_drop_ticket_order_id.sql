-- ============================================================
-- ONE COLUMN OUT OF order_ticket: order_id
--
-- WHAT IT WAS
--   CHAR(32) NULL, holding the uuid4 hex that process_runner mints for
--   each order. claim() wrote it when a label was scanned, release() and
--   release_stranded() cleared it, mark_failed() kept it. 225 of 349 rows
--   had one.
--
-- WHY IT GOES
--   Nothing ever looked a ticket up by it. Not one WHERE, not one JOIN,
--   and no index -- every lifecycle operation finds its row by
--   payload_hash. It was written and then only ever read back out again
--   as itself:
--
--     * admin_gui/serve.py:tickets_payload() shipped it to the browser
--       and no admin JS read it. That was the "order_from_ticket" link
--       parameter, which died with error_log.ticket_key on 2026-09-07.
--     * order_ticket.recent() SELECTed it and never printed it.
--     * only `--status <serial>` showed it, and that reads SELECT t.*.
--
--   The reason written into mark_failed() -- "clearing them would leave a
--   failure that cannot be tied back to its order in error_log" -- had
--   already stopped being true: error_log.order_id was dropped the same
--   day, by database/migrate_drop_error_columns.sql. The thing it pointed
--   at was gone.
--
-- WHAT STOPS WORKING
--   The exact key from a ticket row into order/flow.log, which logs
--   "Đơn <order_id> kết thúc". That link is now made by time instead:
--   the machine runs one order at a time under a single-instance lock,
--   and a ticket carries scanned_at and completed_at. A fault already
--   finds its ticket the other way, by the "[Vé #123]" tag in
--   error_log.message -- see database/error_log.py.
--
-- IRREVERSIBLE
--   Dropping a column drops its data. The rows as they stood are in
--   database/backup_before_drop_ticket_order_id_07092026_151933.sql.
--   NOTE: .gitignore excludes database/backup_*.sql, so that file lives
--   on this machine only -- copy it elsewhere if it matters.
--
-- SAFE TO RE-RUN
--   Guarded by information_schema, so a second run finds the column
--   already gone and does nothing. No index is on order_id, so nothing
--   else goes with it.
--
--   mysql -u root -p beveragepos < database/migrate_drop_ticket_order_id.sql
--   sudo systemctl restart flexmix-backend
-- ============================================================

SET @db := DATABASE();

SET @sql := (
  SELECT IF(COUNT(*) > 0,
            'ALTER TABLE order_ticket DROP COLUMN order_id',
            'DO 0')
    FROM information_schema.COLUMNS
   WHERE TABLE_SCHEMA = @db
     AND TABLE_NAME = 'order_ticket'
     AND COLUMN_NAME = 'order_id'
);
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;
