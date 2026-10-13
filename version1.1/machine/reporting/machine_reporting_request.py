"""Build a bounded local-calendar report from aggregate SQL results."""

from datetime import date, datetime, time, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

from database.services.reporting import read_report_rows

MACHINE_ZONE = ZoneInfo("Asia/Ho_Chi_Minh")


def _decimal(value):
    if not isinstance(value, Decimal):
        raise RuntimeError("Invalid aggregate price from database")
    return value


def nhan_bao_cao(data, *, now=None):
    if not isinstance(data, dict) or set(data) - {"days"}:
        raise ValueError("INVALID_DATA")
    count = data.get("days", 7)
    if type(count) is not int or not 1 <= count <= 31:
        raise ValueError("INVALID_DATA")

    if now is not None and (not isinstance(now, datetime) or now.tzinfo is None or now.utcoffset() is None):
        raise ValueError("INVALID_DATA")
    machine_time = datetime.now(MACHINE_ZONE) if now is None else now.astimezone(MACHINE_ZONE)
    first_day = machine_time.date() - timedelta(days=count - 1)
    after_day = machine_time.date() + timedelta(days=1)
    start = datetime.combine(first_day, time.min, MACHINE_ZONE)
    end = datetime.combine(after_day, time.min, MACHINE_ZONE)
    daily, out_of_stock, undated_used = read_report_rows(
        start.replace(tzinfo=None), end.replace(tzinfo=None)
    )

    by_day = {}
    for row in daily:
        day = row["day"]
        if not isinstance(day, date) or isinstance(day, datetime) or not first_day <= day < after_day:
            raise RuntimeError("Invalid report day from database")
        cups = row["completed_cups"]
        missing = row["missing_price_count"]
        if type(cups) is not int or type(missing) is not int or cups < 0 or not 0 <= missing <= cups:
            raise RuntimeError("Invalid report counts from database")
        by_day[day] = (cups, _decimal(row["ticket_price_sum"]), missing)

    days = []
    total_cups = 0
    total_price = Decimal("0.00")
    total_missing = 0
    for offset in range(count):
        day = first_day + timedelta(days=offset)
        cups, price, missing = by_day.get(day, (0, Decimal("0.00"), 0))
        days.append({
            "date": day.isoformat(),
            "completed_cups": cups,
            "ticket_price_sum_vnd": format(price, "f"),
            "missing_price_count": missing,
        })
        total_cups += cups
        total_price += price
        total_missing += missing

    return {
        "machine_time": machine_time.isoformat(timespec="seconds"),
        "period": {
            "from": start.isoformat(timespec="seconds"),
            "to": end.isoformat(timespec="seconds"),
        },
        "completed_cups": total_cups,
        "ticket_price_sum_vnd": format(total_price, "f"),
        "missing_price_count": total_missing,
        "days": days,
        "current_out_of_stock_ingredients": out_of_stock,
        "undated_used_count": undated_used,
    }


COMMANDS = {"nhan_bao_cao": nhan_bao_cao}
