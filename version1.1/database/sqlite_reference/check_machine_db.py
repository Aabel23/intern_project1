"""Kiểm bản SQLite tham chiếu mà không ghi vào file DB.

VÌ SAO CÓ FILE NÀY
    Schema SQLite được chuyển từ repo server mẹ vào cạnh database của máy.
    Runtime version1.1 vẫn dùng MySQL; phép kiểm này chỉ chứng minh bản
    tham chiếu rỗng, nhất quán và tương thích với các truy vấn đọc hiện có.

CÁCH CHẠY
    python3 database/sqlite_reference/check_machine_db.py
"""

import ast
from pathlib import Path
import sqlite3

FOLDER = Path(__file__).resolve().parent
SOURCE = FOLDER.parents[1]
path = FOLDER / "machine.db"
assert path.read_bytes()[:16] == b"SQLite format 3\x00"

with sqlite3.connect(path.as_uri() + "?mode=ro", uri=True) as artifact:
    assert artifact.execute("PRAGMA integrity_check").fetchone() == ("ok",)
    assert artifact.execute("PRAGMA foreign_key_check").fetchall() == []
    objects = artifact.execute(
        "SELECT type,name,sql FROM sqlite_master WHERE name NOT LIKE 'sqlite_%' ORDER BY type,name"
    ).fetchall()
    tables = [name for kind, name, _ in objects if kind == "table"]
    assert not set(tables) & {"admin_user", "role_permission"}
    for table in tables:
        assert artifact.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone() == (0,)
    db = sqlite3.connect(":memory:")
    artifact.backup(db)

try:
    with sqlite3.connect(":memory:") as rebuilt:
        rebuilt.executescript((FOLDER / "machine.sql").read_text(encoding="utf-8"))
        assert rebuilt.execute(
            "SELECT type,name,sql FROM sqlite_master WHERE name NOT LIKE 'sqlite_%' ORDER BY type,name"
        ).fetchall() == objects
    db.execute("PRAGMA foreign_keys=ON")
    db.execute("PRAGMA recursive_triggers=ON")
    readers = 0
    for relative, names in (
        ("store_gui/sync_menu.py", {"DRINK_QUERY", "SETTING_QUERY", "BESTSELLER_QUERY",
                                   "CATEGORY_QUERY", "MAPPING_QUERY", "RECIPE_QUERY"}),
        ("database/export_data.py", {"MENU_QUERY", "ACTION_QUERY", "RECIPE_QUERY"}),
        ("scan/generate_drink_qr.py", {"DRINK_QUERY", "INGREDIENT_QUERY", "RECIPE_QUERY"}),
    ):
        tree = ast.parse((SOURCE / relative).read_text(encoding="utf-8-sig"))
        queries = {
            target.id: ast.literal_eval(node.value)
            for node in tree.body if isinstance(node, ast.Assign)
            for target in node.targets if isinstance(target, ast.Name) and target.id in names
        }
        assert queries.keys() == names
        for name, sql in queries.items():
            # Chỉ đổi cú pháp ngày/tham số; runtime version1.1 vẫn dùng MySQL.
            sql = sql.replace("NOW() - INTERVAL %s DAY", "datetime('now','-' || ? || ' days')")
            db.execute(sql.replace("%s", "?"),
                       (30, 6) if name == "BESTSELLER_QUERY" else ()).fetchall()
            readers += 1

    db.execute("INSERT INTO drink (drink_id,drink_name,price) VALUES (1001,'Test',30000)")
    db.execute("INSERT INTO drink (drink_id,drink_name) VALUES (1002,'Other')")
    db.execute("INSERT INTO ingredient (ingredient_id,ingredient_name,amount,threshold_gram,gpio) "
               "VALUES (1,'Water',100,60,'G26')")
    db.execute("INSERT INTO recipe VALUES (1001,1,1,50)")
    db.commit()
    assert db.execute("SELECT in_stock FROM drink ORDER BY drink_id").fetchall() == [(1,), (0,)]
    db.execute("UPDATE ingredient SET amount=10 WHERE ingredient_id=1")
    assert db.execute("SELECT in_stock FROM ingredient").fetchone() == (0,)
    assert db.execute("SELECT in_stock FROM drink WHERE drink_id=1001").fetchone() == (0,)
    db.rollback()
    assert db.execute("SELECT amount,in_stock FROM ingredient").fetchone() == (100, 1)
    assert db.execute("SELECT in_stock FROM drink WHERE drink_id=1001").fetchone() == (1,)
    db.execute("UPDATE recipe SET drink_id=1002 WHERE drink_id=1001")
    assert db.execute("SELECT in_stock FROM drink ORDER BY drink_id").fetchall() == [(0,), (1,)]
    db.rollback()
    for sql in (
        "UPDATE ingredient SET amount=-1 WHERE ingredient_id=1",
        "UPDATE ingredient SET gpio='Gbad' WHERE ingredient_id=1",
        "DELETE FROM ingredient WHERE ingredient_id=1",
    ):
        try:
            db.execute(sql)
        except sqlite3.IntegrityError:
            db.rollback()
        else:
            raise AssertionError(f"Invalid operation accepted: {sql}")

    db.execute("INSERT INTO order_ticket (drink_id,price,drink_name,payload,payload_hash,updated_at) "
               "SELECT drink_id,price,drink_name,'123',?,'2000-01-01 00:00:00' "
               "FROM drink WHERE drink_id=1001", ("a" * 64,))
    db.commit()
    for expected in (1, 0):
        assert db.execute("UPDATE order_ticket SET status='in_progress' "
                          "WHERE payload_hash=? AND status='unused'", ("a" * 64,)).rowcount == expected
    db.commit()
    assert db.execute("SELECT updated_at FROM order_ticket").fetchone()[0] != "2000-01-01 00:00:00"
    try:
        db.execute("INSERT INTO order_ticket (drink_id,payload,payload_hash) VALUES (1001,'123',?)",
                   ("a" * 64,))
    except sqlite3.IntegrityError:
        db.rollback()
    else:
        raise AssertionError("Duplicate QR accepted")
    db.execute("DELETE FROM recipe WHERE drink_id=1001")
    assert db.execute("SELECT in_stock FROM drink WHERE drink_id=1001").fetchone() == (0,)
    db.execute("DELETE FROM drink WHERE drink_id=1001")
    assert db.execute("SELECT price,drink_name FROM order_ticket").fetchone() == (30000, "Test")
    print(f"PASS: SQLite file, integrity, {len(tables)} empty tables, SQL reproduction, "
          f"{readers} readers, stock/rollback, constraints, QR single claim, timestamps, sale history.")
finally:
    db.close()
