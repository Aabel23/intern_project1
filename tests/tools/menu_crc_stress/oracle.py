"""Oracle độc lập: tự tính CRC menu bằng hàm riêng để đối chiếu với máy.

Không import gì từ version1.1/machine hay server. CRC-32 viết tay bằng bảng,
không dùng zlib (zlib chỉ dùng để giải nén gói trong decode_packet).
"""

# Thư viện chuẩn
import base64
import json
import sqlite3
import zlib
from pathlib import Path

# Bản sao riêng thứ tự cột, phải khớp hợp đồng gói menu_sync
FIELDS = ("drink_id", "drink_name", "image", "price", "available", "in_stock",
          "glass_id", "drink_type_id", "garnish", "featured")
PACKET_TYPE = "menu_sync"
PACKET_VERSION = 1

_POLY = 0xEDB88320  # đa thức IEEE 0x04C11DB7 dạng đảo bit (reflected)


def _build_table():
    """Bảng 256 phần tử: CRC của từng byte 0..255 sau 8 lần dịch."""
    table = []
    for n in range(256):
        c = n
        for _ in range(8):
            # Bit thấp = 1 thì dịch phải rồi XOR đa thức, ngược lại chỉ dịch
            c = (c >> 1) ^ _POLY if c & 1 else c >> 1
        table.append(c)
    return tuple(table)


_TABLE = _build_table()


def crc32(data: bytes) -> int:
    """CRC-32/IEEE: init 0xFFFFFFFF, mỗi byte tra bảng, cuối XOR 0xFFFFFFFF."""
    crc = 0xFFFFFFFF
    for b in data:
        # Byte thấp của crc XOR byte vào làm chỉ số bảng, phần còn lại dịch 8 bit
        crc = _TABLE[(crc ^ b) & 0xFF] ^ (crc >> 8)
    return crc ^ 0xFFFFFFFF


def read_rows(db_path: Path) -> list[list]:
    """Đọc món chưa xóa mềm (chỉ đọc), sắp theo drink_id, mỗi món là list theo FIELDS."""
    uri = Path(db_path).resolve().as_uri() + "?mode=ro"
    conn = sqlite3.connect(uri, uri=True)
    try:
        cols = ", ".join(FIELDS)
        cur = conn.execute(f"SELECT {cols} FROM drink WHERE deleted_at IS NULL ORDER BY drink_id")
        return [list(row) for row in cur.fetchall()]
    finally:
        conn.close()


def canonical_bytes(rows: list[list]) -> bytes:
    """JSON gọn, giữ Unicode, UTF-8 — đây chính là hợp đồng byte để tính CRC.

    Biểu diễn là hợp đồng: price NUMERIC lưu int ra "30000", lưu float ra "30000.0"
    → khác byte, khác CRC. Vì vậy giữ nguyên kiểu giá trị sqlite3 trả về, không
    ép kiểu, giống cách máy đọc. Dùng json chỉ để tuần tự hóa, không để tính CRC.
    """
    return json.dumps(rows, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


def expected_version(db_path: Path) -> int:
    return crc32(canonical_bytes(read_rows(db_path)))


def decode_packet(packet: str) -> dict:
    """base64 → giải nén zlib → JSON."""
    return json.loads(zlib.decompress(base64.b64decode(packet)).decode("utf-8"))


def _deleted_ids(db_path: Path) -> set:
    uri = Path(db_path).resolve().as_uri() + "?mode=ro"
    conn = sqlite3.connect(uri, uri=True)
    try:
        return {r[0] for r in conn.execute("SELECT drink_id FROM drink WHERE deleted_at IS NOT NULL")}
    finally:
        conn.close()


def check_packet(packet: str, db_path: Path) -> list[str]:
    """Đối chiếu gói của máy với DB; trả danh sách lỗi, rỗng = đạt."""
    try:
        data = decode_packet(packet)
    except Exception as exc:  # gói hỏng thì dừng luôn
        return [f"giải mã gói lỗi: {exc!r}"]
    if not isinstance(data, dict):
        return [f"gói không phải object: {type(data).__name__}"]

    errors = []
    if data.get("type") != PACKET_TYPE:
        errors.append(f"type sai: {data.get('type')!r}")
    if data.get("v") != PACKET_VERSION:
        errors.append(f"v sai: {data.get('v')!r}")
    if data.get("fields") != list(FIELDS):
        errors.append(f"fields sai: {data.get('fields')!r}")

    drinks = data.get("drinks")
    db_rows = read_rows(db_path)
    if drinks != db_rows:
        got = {r[0]: r for r in drinks or [] if isinstance(r, list) and r}
        want = {r[0]: r for r in db_rows}
        diff = sorted(i for i in set(got) | set(want) if got.get(i) != want.get(i))
        errors.append(f"drinks khác DB ở món {diff[:10]}" if diff else "drinks khác DB (thứ tự/kiểu)")

    version = data.get("menu_version")
    if isinstance(drinks, list):
        own = crc32(canonical_bytes(drinks))
        if version != own:
            errors.append(f"menu_version {version} != CRC tự tính của drinks trong gói {own}")
    expected = expected_version(db_path)
    if version != expected:
        errors.append(f"menu_version {version} != CRC tự tính từ DB {expected}")

    deleted = _deleted_ids(db_path)
    leaked = sorted({r[0] for r in drinks or [] if isinstance(r, list) and r} & deleted)
    if leaked:
        errors.append(f"gói chứa món đã xóa mềm: {leaked}")
    return errors


if __name__ == "__main__":
    import os
    import random
    import tempfile

    assert crc32(b"123456789") == 0xCBF43926
    assert crc32(b"RIFF") == 0x0697A25C
    assert crc32(b"") == 0
    print("OK vector chuẩn CRC-32")

    rnd = random.Random(1)
    for _ in range(1000):
        buf = bytes(rnd.randrange(256) for _ in range(rnd.randrange(300)))
        assert crc32(buf) == zlib.crc32(buf), buf  # zlib chỉ để đối chiếu
    print("OK khớp zlib.crc32 trên 1000 chuỗi ngẫu nhiên")

    with tempfile.TemporaryDirectory() as tmp:
        db = os.path.join(tmp, "menu.db")
        conn = sqlite3.connect(db)
        conn.execute("CREATE TABLE drink (drink_id INTEGER PRIMARY KEY, drink_name TEXT, image TEXT,"
                     " price NUMERIC, available INTEGER, in_stock INTEGER, deleted_at TEXT,"
                     " glass_id INTEGER, drink_type_id INTEGER, garnish TEXT, featured INTEGER)")
        conn.executemany("INSERT INTO drink VALUES (?, ?, NULL, ?, 1, 1, ?, NULL, NULL, NULL, 0)",
                         [(1001, "Cà phê", 20000, None), (1002, "Trà đào", 30000.5, None),
                          (1003, "Món đã xóa", 1, "2026-01-01")])
        conn.commit()
        conn.close()

        def pack(drinks, version=None):
            # Đóng gói giống machine_menu_pack, viết lại tại chỗ
            to_json = lambda d: json.dumps(d, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
            body = {"type": "menu_sync", "v": 1,
                    "menu_version": zlib.crc32(to_json(drinks)) if version is None else version,
                    "generated_at": "2026-10-09T00:00:00", "fields": list(FIELDS), "drinks": drinks}
            return base64.b64encode(zlib.compress(to_json(body), level=9)).decode("ascii")

        rows = read_rows(Path(db))
        assert [r[0] for r in rows] == [1001, 1002]
        assert check_packet(pack(rows), Path(db)) == [], check_packet(pack(rows), Path(db))
        print("OK gói đúng → không lỗi")

        bad = [list(r) for r in rows]
        bad[0][3] = 20001
        errs = check_packet(pack(bad), Path(db))
        assert errs and any("drinks khác DB" in e for e in errs), errs
        print("OK sửa giá 1 món → báo lỗi:", errs)

        errs = check_packet(pack(rows, version=123), Path(db))
        assert len(errs) == 2, errs
        print("OK menu_version sai → báo lỗi:", errs)

        leak = rows + [[1003, "Món đã xóa", None, 1, 1, 1, None, None, None, 0]]
        errs = check_packet(pack(leak), Path(db))
        assert any("xóa mềm" in e for e in errs), errs
        print("OK lọt món xóa mềm → báo lỗi")

        assert check_packet("không-phải-base64", Path(db))
        print("OK gói hỏng → báo lỗi")
    print("TẤT CẢ OK")
