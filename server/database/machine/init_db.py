"""Chạy từ thư mục dự án: python -m server.database.machine.init_db."""

from pathlib import Path

from ..connection import get_connection


def init_db():
    """Tạo bảng nếu chưa có, giữ nguyên dữ liệu hiện tại."""
    # Bảng users trước vì các bảng máy có khóa ngoại tới users.
    user_schema = Path(__file__).parents[1].joinpath('user', 'schema.sql').read_text(encoding='utf-8')
    schema = Path(__file__).with_name('schema.sql').read_text(encoding='utf-8')
    share_schema = Path(__file__).with_name("machine_share_schema.sql").read_text(encoding="utf-8")
    with get_connection() as conn:
        conn.executescript(user_schema)
        conn.executescript(schema)
        conn.executescript(share_schema)
        # Bổ sung cột cho database cũ, giữ nguyên máy và tài khoản đã có.
        columns = [row['name'] for row in conn.execute('PRAGMA table_info(machines)')]
        if 'product_key_hash' not in columns:
            conn.execute('ALTER TABLE machines ADD COLUMN product_key_hash TEXT')
        conn.execute(
            'CREATE UNIQUE INDEX IF NOT EXISTS machines_product_key ON machines(product_key_hash)'
        )


if __name__ == '__main__':
    init_db()
    print('Da tao bang machines.')
