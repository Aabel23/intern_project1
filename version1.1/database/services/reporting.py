"""Aggregate completed QR ticket snapshots and current stock on the machine."""

from database.core.connection import close_database_resources, connect_database


def read_report_rows(start_local, end_local):
    """Return aggregate day rows and two current/all-time counters.

    Bounds are naive MySQL DATETIME values representing machine local time.
    No QR ticket rows, customer details, or live drink prices are fetched.
    """
    conn = None
    cursor = None
    try:
        conn = connect_database()
        conn.start_transaction(isolation_level="REPEATABLE READ", consistent_snapshot=True)
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            "SELECT DATE(completed_at) AS day, COUNT(*) AS completed_cups, "
            "COALESCE(SUM(price), 0) AS ticket_price_sum, "
            "CAST(SUM(price IS NULL) AS UNSIGNED) AS missing_price_count "
            "FROM order_ticket WHERE status = 'used' "
            "AND completed_at >= %s AND completed_at < %s "
            "GROUP BY DATE(completed_at) ORDER BY day",
            (start_local, end_local),
        )
        daily = list(cursor.fetchall())
        cursor.execute("SELECT COUNT(*) AS count FROM ingredient WHERE in_stock = FALSE")
        out_of_stock = cursor.fetchone()["count"]
        cursor.execute(
            "SELECT COUNT(*) AS count FROM order_ticket "
            "WHERE status = 'used' AND completed_at IS NULL"
        )
        undated_used = cursor.fetchone()["count"]
        conn.commit()
        return daily, int(out_of_stock), int(undated_used)
    except Exception:
        if conn is not None:
            conn.rollback()
        raise
    finally:
        close_database_resources(cursor, conn)
