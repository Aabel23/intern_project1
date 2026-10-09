"""Đường dẫn tới các file hiệu chuẩn phần cứng.

Chỉ đường dẫn — số liệu nằm trong chính các file .json đó, do
loadcell/init_loadcell.py và pump_control/calib_pump.py ghi ra.

Các setting KHÁC của máy (đấu dây, cổng, thiết bị, chính sách) nằm ở
configuration/machine.py, không ở đây.

VÌ SAO HIỆU CHUẨN KHÔNG CÒN SỐNG TRONG THƯ MỤC MÃ NGUỒN
    Mấy con số này là số đo của ĐÚNG cỗ máy này: gram_per_sec của đúng
    cái bơm đó, điểm zero của đúng cái loadcell đó. Chúng từng nằm trong
    git, nên một bản clone mang số của máy khác đi theo — và máy mới rót
    sai ngay từ ly đầu, sai im lặng, vì r_squared 0.99999 trông không có
    gì đáng ngờ.

    Nặng hơn: mô hình phát hành sắp tới là "checkout tag + đổi symlink",
    tức cả thư mục mã nguồn bị thay mỗi lần cập nhật. Thứ gì nằm trong đó
    đều biến mất. Hiệu chuẩn phải sống ngoài checkout.

    /var/lib/flexmix/ chứ không phải /etc/flexmix/: /etc là cấu hình do
    người đặt, còn đây là số đo do máy tự ghi. Và init_loadcell.py chạy
    dưới quyền flexxource nên phải GHI được, trong khi /etc/flexmix thuộc
    root — service chỉ đọc được qua EnvironmentFile= của systemd.

NHÁNH RƠI VỀ LÀ TẠM THỜI
    runtime_path() vẫn chấp nhận file nằm ở thư mục cũ, để máy chưa
    migrate chạy y như trước. Khi cả đội máy đã chuyển xong thì bỏ nhánh
    đó đi: hai nơi hợp lệ cho cùng một file là cách chắc chắn nhất để hai
    bản lệch nhau — đúng cái bệnh mà net_addresses.py và served_paths.py
    đã phải chữa.

ĐƯỜNG DẪN CHỐT MỘT LẦN LÚC IMPORT
    Không phải mỗi lần đọc. Nên chuyển file trong lúc máy đang chạy thì
    tiến trình đó KHÔNG thấy — phải restart. Đổi lại, vòng rót không tốn
    một lần stat() cho mỗi lần đọc hiệu chuẩn.

Hai hằng số từng nằm trong file này đã bị bỏ vì không nơi nào dùng:
PUMP_STEP_FILE (còn bị khai báo hai lần, chuỗi rồi Path đè lên) và
PUMP_CALIB_PARALLEL_FILE (trỏ tới pump_calib_parallel.json — một file
chưa từng tồn tại).
"""

from pathlib import Path

# loadcell/loadcell.py và pump_control/calib_pump.py nạp file này bằng
# `import *`, và cả hai chỉ cần đúng hai đường dẫn dưới đây. Khai __all__
# để `import *` thôi kéo theo Path lẫn BASE_DIR — calib_pump.py đã phải
# đặt một import xuống DƯỚI dòng star của nó để không bị che mất.
__all__ = ["CALIBLOADCELL_FILE", "PUMP_CALIB_FILE"]

BASE_DIR = Path(__file__).resolve().parent

# Nhà của mọi thứ máy tự ghi ra và phải sống sót qua một lần cập nhật.
# deploy/install.sh tạo thư mục này với chủ sở hữu flexxource, vì
# calib_pump.py và init_loadcell.py chạy dưới quyền người dùng đó.
RUNTIME_DIR = Path("/var/lib/flexmix")


def runtime_path(name: str) -> Path:
    """Nhà mới nếu file đã ở đó, không thì nhà cũ trong thư mục mã nguồn."""
    moved = RUNTIME_DIR / name

    return moved if moved.exists() else BASE_DIR / name


CALIBLOADCELL_FILE = runtime_path("calib_loadcell.json")
PUMP_CALIB_FILE = runtime_path("pump_calib.json")
