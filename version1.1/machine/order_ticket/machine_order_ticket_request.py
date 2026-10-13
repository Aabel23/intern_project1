"""Relay instruction for a page of local QR ticket snapshots."""

from datetime import datetime
from decimal import Decimal

from database.services.order_ticket import VALID_STATUSES, recent_page


def _iso_local(value):
    if value is None:
        return None
    if not isinstance(value, datetime) or value.tzinfo is not None:
        raise RuntimeError("Invalid ticket timestamp in database")
    return value.isoformat(timespec="seconds")


def _price(value):
    if value is None:
        return None
    if not isinstance(value, Decimal):
        raise RuntimeError("Invalid ticket price in database")
    return format(value, "f")


def nhan_ve_qr(data):
    if not isinstance(data, dict) or set(data) - {"before_serial", "limit"}:
        raise ValueError("INVALID_DATA")
    before_serial = data.get("before_serial")
    limit = data.get("limit", 20)
    if before_serial is not None and (type(before_serial) is not int or before_serial <= 0):
        raise ValueError("INVALID_DATA")
    if type(limit) is not int or not 1 <= limit <= 20:
        raise ValueError("INVALID_DATA")

    rows = recent_page(before_serial, limit)
    has_more = len(rows) > limit
    tickets = []
    for row in rows[:limit]:
        if type(row["serial"]) is not int or row["serial"] <= 0:
            raise RuntimeError("Invalid ticket serial in database")
        if row["drink_name"] is not None and not isinstance(row["drink_name"], str):
            raise RuntimeError("Invalid ticket name in database")
        if row["status"] not in VALID_STATUSES:
            raise RuntimeError("Invalid ticket status in database")
        tickets.append({
            "serial": row["serial"],
            "drink_name": row["drink_name"],
            "price_vnd": _price(row["price"]),
            "status": row["status"],
            "created_at": _iso_local(row["created_at"]),
            "scanned_at": _iso_local(row["scanned_at"]),
            "completed_at": _iso_local(row["completed_at"]),
        })
    return {
        "tickets": tickets,
        "next_before_serial": tickets[-1]["serial"] if has_more else None,
    }


COMMANDS = {"nhan_ve_qr": nhan_ve_qr}
