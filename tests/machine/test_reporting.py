import os
import sys
import unittest
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "version1.1"))
os.environ.setdefault("BEVERAGE_DB_PASSWORD", "test-only-password")

from database.services import reporting
from machine.main import _business_commands
from machine.reporting.machine_reporting_request import nhan_bao_cao


class ReportingTests(unittest.TestCase):
    def test_calendar_bounds_exact_decimal_and_zero_days(self):
        rows = [
            {"day": date(2026, 1, 1), "completed_cups": 2,
             "ticket_price_sum": Decimal("35000.25"), "missing_price_count": 1},
            {"day": date(2026, 1, 3), "completed_cups": 1,
             "ticket_price_sum": Decimal("20000.00"), "missing_price_count": 0},
        ]
        with patch(
            "machine.reporting.machine_reporting_request.read_report_rows",
            return_value=(rows, 4, 2),
        ) as read:
            result = nhan_bao_cao(
                {"days": 4}, now=datetime(2026, 1, 3, 14, 30, tzinfo=timezone.utc)
            )
        start, end = read.call_args.args
        self.assertEqual(start, datetime(2025, 12, 31))
        self.assertEqual(end, datetime(2026, 1, 4))
        self.assertEqual(result["machine_time"], "2026-01-03T21:30:00+07:00")
        self.assertEqual(result["period"], {
            "from": "2025-12-31T00:00:00+07:00",
            "to": "2026-01-04T00:00:00+07:00",
        })
        self.assertEqual(result["completed_cups"], 3)
        self.assertEqual(result["ticket_price_sum_vnd"], "55000.25")
        self.assertEqual(result["missing_price_count"], 1)
        self.assertEqual(result["current_out_of_stock_ingredients"], 4)
        self.assertEqual(result["undated_used_count"], 2)
        self.assertEqual(len(result["days"]), 4)
        self.assertEqual(result["days"][0]["date"], "2025-12-31")
        self.assertEqual(result["days"][0]["completed_cups"], 0)
        self.assertEqual(result["days"][1]["ticket_price_sum_vnd"], "35000.25")

    def test_default_seven_days_and_invalid_requests(self):
        with patch("machine.reporting.machine_reporting_request.read_report_rows", return_value=([], 0, 0)) as read:
            result = nhan_bao_cao({}, now=datetime(2026, 10, 13, tzinfo=timezone.utc))
            self.assertEqual(len(result["days"]), 7)
            self.assertEqual(result["completed_cups"], 0)
            self.assertEqual(result["ticket_price_sum_vnd"], "0.00")
            read.reset_mock()
            for data in ({"days": 0}, {"days": 32}, {"days": True},
                         {"days": 7.0}, {"days": "7"}, {"status": "used"}):
                with self.subTest(data=data), self.assertRaisesRegex(ValueError, "INVALID_DATA"):
                    nhan_bao_cao(data, now=datetime(2026, 10, 13, tzinfo=timezone.utc))
            read.assert_not_called()

    def test_database_aggregates_with_no_ticket_rows_and_one_snapshot(self):
        cursor = MagicMock()
        cursor.fetchall.return_value = [{
            "day": date(2026, 10, 13), "completed_cups": 2,
            "ticket_price_sum": Decimal("65000.50"), "missing_price_count": 1,
        }]
        cursor.fetchone.side_effect = [{"count": 3}, {"count": 1}]
        conn = MagicMock()
        conn.cursor.return_value = cursor
        start, end = datetime(2026, 10, 13), datetime(2026, 10, 14)
        with patch.object(reporting, "connect_database", return_value=conn), patch.object(
            reporting, "close_database_resources"
        ):
            daily, stock, undated = reporting.read_report_rows(start, end)
        self.assertEqual((len(daily), stock, undated), (1, 3, 1))
        conn.start_transaction.assert_called_once_with(
            isolation_level="REPEATABLE READ", consistent_snapshot=True
        )
        conn.commit.assert_called_once()
        self.assertEqual(cursor.execute.call_count, 3)
        daily_sql, params = cursor.execute.call_args_list[0].args
        self.assertEqual(params, (start, end))
        self.assertIn("status = 'used'", daily_sql)
        self.assertIn("completed_at >= %s AND completed_at < %s", daily_sql)
        self.assertIn("SUM(price)", daily_sql)
        self.assertIn("SUM(price IS NULL)", daily_sql)
        for sql in (call.args[0] for call in cursor.execute.call_args_list):
            for private_column in ("payload", "payload_hash", "note", "drink_name"):
                self.assertNotIn(private_column, sql)
        self.assertIn("in_stock = FALSE", cursor.execute.call_args_list[1].args[0])
        self.assertIn("completed_at IS NULL", cursor.execute.call_args_list[2].args[0])

    def test_command_registered(self):
        commands = _business_commands()
        self.assertIs(commands["nhan_bao_cao"], nhan_bao_cao)
        self.assertIn("nhan_ve_qr", commands)


if __name__ == "__main__":
    unittest.main()
