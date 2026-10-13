import os
import sys
import unittest
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "version1.1"))
os.environ.setdefault("BEVERAGE_DB_PASSWORD", "test-only-password")

from database.services import order_ticket
from machine.main import _business_commands
from machine.order_ticket.machine_order_ticket_request import nhan_ve_qr


class TicketListTests(unittest.TestCase):
    def test_command_is_registered_without_changing_existing_commands(self):
        commands = _business_commands()
        self.assertIs(commands["nhan_ve_qr"], nhan_ve_qr)
        self.assertIn("nhan_menu", commands)
        self.assertIn("nhan_kho", commands)

    def _row(self, serial, status="used"):
        return {
            "serial": serial,
            "drink_name": "Trà đào lúc bán",
            "price": Decimal("35000.25"),
            "status": status,
            "created_at": datetime(2026, 10, 13, 10, 42),
            "scanned_at": None,
            "completed_at": None,
            # A database fetch must not select or expose these fields.
        }

    def test_keyset_pages_use_snapshot_and_never_return_qr_secrets(self):
        rows = [self._row(i) for i in range(25, 0, -1)]
        with patch(
            "machine.order_ticket.machine_order_ticket_request.recent_page",
            side_effect=lambda before, limit: [
                r for r in rows if before is None or r["serial"] < before
            ][: limit + 1],
        ):
            first = nhan_ve_qr({"before_serial": None, "limit": 20})
            second = nhan_ve_qr({"before_serial": first["next_before_serial"], "limit": 20})

        self.assertEqual([t["serial"] for t in first["tickets"]], list(range(25, 5, -1)))
        self.assertEqual(first["next_before_serial"], 6)
        self.assertEqual([t["serial"] for t in second["tickets"]], [5, 4, 3, 2, 1])
        self.assertIsNone(second["next_before_serial"])
        self.assertEqual(first["tickets"][0]["drink_name"], "Trà đào lúc bán")
        self.assertEqual(first["tickets"][0]["price_vnd"], "35000.25")
        self.assertEqual(first["tickets"][0]["created_at"], "2026-10-13T10:42:00")
        self.assertIsNone(first["tickets"][0]["scanned_at"])
        self.assertEqual(
            set(first["tickets"][0]),
            {"serial", "drink_name", "price_vnd", "status", "created_at", "scanned_at", "completed_at"},
        )

    def test_snapshot_null_and_every_database_status(self):
        rows = [self._row(i, status) for i, status in enumerate(order_ticket.VALID_STATUSES, 1)]
        rows[0]["drink_name"] = None
        rows[0]["price"] = None
        with patch("machine.order_ticket.machine_order_ticket_request.recent_page", return_value=rows):
            result = nhan_ve_qr({})
        self.assertEqual([t["status"] for t in result["tickets"]], list(order_ticket.VALID_STATUSES))
        self.assertIsNone(result["tickets"][0]["drink_name"])
        self.assertIsNone(result["tickets"][0]["price_vnd"])
        self.assertIsNone(result["next_before_serial"])

    def test_request_validation(self):
        bad = [
            {"before_serial": 0}, {"before_serial": -1}, {"before_serial": True},
            {"before_serial": "2"}, {"limit": 0}, {"limit": 21},
            {"limit": False}, {"limit": "20"}, {"filter": "used"},
        ]
        with patch("machine.order_ticket.machine_order_ticket_request.recent_page") as query:
            for data in bad:
                with self.subTest(data=data), self.assertRaisesRegex(ValueError, "INVALID_DATA"):
                    nhan_ve_qr(data)
            query.assert_not_called()

    def test_query_selects_only_safe_snapshots_with_limit_plus_one(self):
        cursor = MagicMock()
        cursor.fetchall.return_value = [self._row(3)]
        conn = MagicMock()
        conn.cursor.return_value = cursor
        with patch.object(order_ticket, "connect_database", return_value=conn), patch.object(
            order_ticket, "close_database_resources"
        ):
            self.assertEqual(len(order_ticket.recent_page(None, 20)), 1)
            self.assertEqual(len(order_ticket.recent_page(3, 2)), 1)
        first_sql, first_params = cursor.execute.call_args_list[0].args
        second_sql, second_params = cursor.execute.call_args_list[1].args
        self.assertEqual(first_params, (21,))
        self.assertEqual(second_params, (3, 3))
        self.assertIn("ORDER BY serial DESC", first_sql)
        self.assertIn("WHERE serial < %s", second_sql)
        for sql in (first_sql, second_sql):
            self.assertIn("drink_name, price, status", sql)
            self.assertNotIn("payload", sql)
            self.assertNotIn("note", sql)
            self.assertNotIn("JOIN", sql)


if __name__ == "__main__":
    unittest.main()
