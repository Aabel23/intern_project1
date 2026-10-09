"""Áp những migration mà database này chưa từng nhận, và ghi lại là đã áp.

VÌ SAO CÓ FILE NÀY
    Schema của máy từng đổi qua ba đường, và không đường nào để lại dấu
    vết: database.sql chạy lại mỗi lần và nuốt lỗi "đã tồn tại"
    (IGNORED_SCHEMA_ERROR_CODES), bốn hàm migrate_*() trong db_core.py
    chạy lại mỗi lần, và mười ba file migrate_*.sql chạy bằng tay.

    Cả ba đều idempotent nên không cái nào hỏng. Nhưng *chạy lại được*
    không đồng nghĩa với *có ghi lại*: hỏi "máy số 7 đang ở schema nào"
    thì cách duy nhất là mở MySQL ra soi từng cột. Với một máy thì còn
    nhớ được; với ba mươi thì không.

    Đó là câu agent của Hub phải hỏi TRƯỚC KHI đọc bất cứ thứ gì khác --
    nó từ chối chạy trên schema nó không biết, thay vì đoán. Đoán sai là
    đọc một cột không tồn tại, hoặc tệ hơn, một cột cùng tên đã đổi nghĩa.

QUY TẮC ĐẶT TÊN FILE
    database/migrations/NNNN_ten_viet_lien.sql

    Bốn chữ số, không trùng, không hổng. Sai tên thì TỪ CHỐI chứ không bỏ
    qua: một file đặt sai tên là một migration sẽ không bao giờ chạy, và
    hỏng kiểu đó chỉ lộ ra nhiều tháng sau trên một máy ở xa.

MỖI FILE PHẢI CHỊU ĐƯỢC MỘT LẦN CHẠY DỞ
    MySQL không có transaction cho DDL. File có ba câu lệnh mà câu thứ hai
    hỏng thì câu đầu ĐÃ nằm trong database rồi và không lùi lại được. Dòng
    ghi vào sổ chỉ được viết sau khi cả file chạy xong, nên lần chạy sau
    sẽ làm lại từ đầu file đó.

    Nghĩa là mỗi câu lệnh phải tự chịu được việc chạy lần hai: dùng
    CREATE TABLE IF NOT EXISTS, ADD COLUMN IF NOT EXISTS, hoặc kiểm tra
    trước khi sửa. Đây là cùng một ràng buộc mà migrate_v2_schema() trong
    db_core.py đã phải sống với, và vì cùng một lý do.

CHECKSUM ĐỂ LÀM GÌ
    Một migration bị sửa SAU KHI đã áp là một cỗ máy có lịch sử nói một
    đằng và schema một nẻo. Không ai phát hiện ra, vì phiên bản vẫn khớp.
    So sha256 biến chuyện đó thành một lỗi to tiếng ngay lần chạy kế tiếp.

    Cùng triết lý với configuration/served_paths.py: hỏng thành tiếng thì
    mất mười giây để sửa, hỏng im lặng thì mất một buổi để tìm.
"""

from __future__ import annotations

import hashlib
import re
from pathlib import Path


MIGRATIONS_DIR = Path(__file__).resolve().parent / "migrations"

# NNNN_ten.sql -- chữ thường, số và gạch dưới. Hẹp có chủ đích: tên file là
# thứ đi vào bảng và vào log, nên nó không được chứa khoảng trắng hay dấu.
FILE_PATTERN = re.compile(r"^(\d{4})_([a-z0-9_]+)\.sql$")


class MigrationError(Exception):
    """Một tình trạng migration không được phép chạy tiếp."""


def _checksum(path: Path) -> str:
    """sha256 của file, đúng như nó nằm trên đĩa."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def discover() -> list[tuple[str, str, Path]]:
    """Mọi migration trên đĩa, cũ trước mới sau: (version, name, path).

    Từ chối cả ba kiểu sai có thể khiến một máy chạy nửa vời: tên file
    không đúng khuôn, hai file cùng số, và số bị hổng ở giữa.
    """
    if not MIGRATIONS_DIR.is_dir():
        raise MigrationError(f"Không có thư mục {MIGRATIONS_DIR}.")

    found: list[tuple[str, str, Path]] = []

    for path in sorted(MIGRATIONS_DIR.iterdir()):
        if path.name.startswith(".") or path.suffix != ".sql":
            continue

        match = FILE_PATTERN.match(path.name)

        if match is None:
            raise MigrationError(
                f"Tên file migration sai khuôn: {path.name}. "
                "Phải là NNNN_ten_viet_lien.sql (bốn chữ số).")

        found.append((match.group(1), match.group(2), path))

    versions = [version for version, _, _ in found]
    duplicates = {v for v in versions if versions.count(v) > 1}

    if duplicates:
        raise MigrationError(
            f"Hai file migration cùng số: {', '.join(sorted(duplicates))}.")

    # Hổng số nghĩa là một file đã bị xoá. Áp 0003 mà thiếu 0002 cho ra một
    # schema không ai mô tả được, nên dừng ở đây chứ không đoán.
    for position, version in enumerate(versions, start=1):
        if int(version) == position:
            continue

        # Vị trí 1 phải nói khác. versions[position - 2] ở đây là
        # versions[-1] — phần tử CUỐI danh sách — và câu sinh ra tự mâu
        # thuẫn: "sau 0002 phải là 0001, nhưng file kế tiếp là 0002".
        if position == 1:
            raise MigrationError(
                f"Migration đầu tiên phải là 0001, nhưng file đầu tiên là "
                f"{version}. Thiếu 0001_baseline.sql?")

        raise MigrationError(
            f"Số migration bị hổng: sau {versions[position - 2]} phải là "
            f"{position:04d}, nhưng file kế tiếp là {version}.")

    return found


def applied(cursor) -> dict[str, str]:
    """Những gì database này đã ghi vào sổ: version -> checksum."""
    cursor.execute("SELECT version, checksum FROM schema_migration")

    rows = cursor.fetchall() or []
    result: dict[str, str] = {}

    for row in rows:
        if isinstance(row, dict):
            result[str(row["version"])] = str(row["checksum"])
        else:
            result[str(row[0])] = str(row[1])

    return result


def _apply_one(cursor, version: str, name: str, path: Path) -> None:
    """Chạy một file rồi ghi nó vào sổ. Ghi SAU, không phải trước."""
    from database.db_core import split_sql_statements

    for statement in split_sql_statements(path.read_text(encoding="utf-8")):
        cursor.execute(statement)

    cursor.execute(
        """
        INSERT INTO schema_migration (version, name, checksum)
        VALUES (%s, %s, %s)
        """,
        (version, name, _checksum(path)),
    )


def run(cursor, *, report=print) -> list[str]:
    """Áp những gì còn thiếu. Trả về danh sách version vừa áp.

    Gọi bên trong apply_database_sql(), sau khi database.sql đã chạy --
    chính file đó tạo ra bảng schema_migration, và không đọc được một
    cuốn sổ chưa tồn tại.
    """
    on_disk = discover()
    in_book = applied(cursor)

    # Sổ ghi một version mà trên đĩa không có file: máy đang ĐI TRƯỚC mã
    # nguồn, thường là vì ai đó lùi bản mã mà không lùi được schema. Nói
    # to chứ không ném lỗi: không có gì để áp, nên chặn `update` ở đây chỉ
    # tước mất công cụ sửa chữa của người đang đứng trước máy.
    unknown = sorted(set(in_book) - {version for version, _, _ in on_disk})

    if unknown:
        report(f"[migrate] CẢNH BÁO: database đã ghi {', '.join(unknown)} "
               "nhưng không có file tương ứng — mã nguồn đang cũ hơn schema.")

    pending: list[tuple[str, str, Path]] = []

    for version, name, path in on_disk:
        recorded = in_book.get(version)

        if recorded is None:
            pending.append((version, name, path))
            continue

        if recorded != _checksum(path):
            raise MigrationError(
                f"Migration {version}_{name}.sql đã đổi nội dung sau khi được "
                "áp. Lịch sử của máy này không còn khớp với mã nguồn. Đừng "
                "sửa một migration đã chạy — viết một migration mới.")

    # Thư mục rỗng là một bản checkout hỏng, không phải "không có gì để
    # làm": 0001_baseline.sql nằm trong git và phải luôn ở đó. Nói to ngay
    # đây, vì triệu chứng khi im lặng đi xa hơn nhiều — sổ rỗng, rồi agent
    # ở P3 đọc current_version() ra None và từ chối chạy, cách nguyên nhân
    # thật vài lớp.
    #
    # Kiểm SAU vòng lặp checksum ở trên, để một máy có sổ nhưng mất file
    # còn kịp nhận cảnh báo "mã nguồn cũ hơn schema" — câu đó nói đúng
    # nguyên nhân hơn.
    if not on_disk:
        raise MigrationError(
            f"Không có file migration nào trong {MIGRATIONS_DIR}, kể cả "
            "0001_baseline.sql. Bản checkout này thiếu file — khôi phục "
            "bằng git rồi chạy lại.")

    for version, name, path in pending:
        report(f"[migrate] áp {version}_{name}")
        _apply_one(cursor, version, name, path)

    if not pending:
        report(f"[migrate] schema đã ở {on_disk[-1][0]}, không có gì để áp.")

    return [version for version, _, _ in pending]


def current_version(cursor) -> str | None:
    """Version cao nhất database này đã ghi, hoặc None nếu sổ trống.

    Đây là câu agent của Hub hỏi trước khi tin bất cứ thứ gì nó đọc được.
    """
    book = applied(cursor)
    return max(book) if book else None
