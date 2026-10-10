"""Ảnh món: JSON app → (kết quả máy hoặc lỗi, HTTP status).

App chỉ xin ảnh chưa có trong cache, theo drink_id và image_hash (CRC32 byte ảnh,
lấy từ cột image_hash của gói menu). App không gửi đường dẫn file; máy tự tra.
"""

from server.lib.machine.machine_access import check_access
from server.lib.machine.machine_transport import send

# Cấu hình riêng: quyền xem ảnh giống menu, số ảnh tối đa mỗi lượt.
QUYEN_MENU = {"owner", "manager"}
MAX_IMAGES = 20


# Nhóm 1: kiểm từng giá trị và cả danh sách ảnh cần xin.
def is_drink_id(value):
    return isinstance(value, int) and not isinstance(value, bool) and value > 0


def is_image_hash(value):
    # CRC32 byte ảnh; 0 là món không có ảnh nên không xin.
    return isinstance(value, int) and not isinstance(value, bool) and 0 < value < 2**32


def is_image(item):
    # Một dòng: đúng hai trường {drink_id, image_hash}, từ chối trường lạ.
    return (isinstance(item, dict) and set(item) == {"drink_id", "image_hash"}
            and is_drink_id(item["drink_id"]) and is_image_hash(item["image_hash"]))


def is_images(anh):
    # Danh sách 1..MAX_IMAGES dòng, không trùng món; một dòng sai thì từ chối cả gói.
    return (isinstance(anh, list) and 1 <= len(anh) <= MAX_IMAGES and all(map(is_image, anh))
            and len({item["drink_id"] for item in anh}) == len(anh))


# Nhóm 2: luồng chính được machine_menu_main gọi khi URL ảnh khớp.
def nhan_anh(data):
    # Bước 1: kiểm phiên và quyền máy; lỗi thì dừng.
    machine_id, error = check_access(data, QUYEN_MENU)
    if error:
        return error

    # Bước 2: kiểm danh sách ảnh; token không đi xuống máy.
    anh = data.get("anh")
    if not is_images(anh):
        return {"loi": "Danh sách ảnh không hợp lệ"}, 400
    command_data = {"anh": anh}

    # Bước 3: giao lệnh, chờ máy trả {status, anh, con_lai} hoặc lỗi transport.
    return send(machine_id, "nhan_anh", command_data)
