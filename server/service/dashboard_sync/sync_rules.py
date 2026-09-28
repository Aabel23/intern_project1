"""Lệnh đọc dữ liệu dashboard app được gửi qua /app/dong-bo.

Server không hiểu dữ liệu, chỉ kiểm tra: lệnh có trong bảng và vai trò của
người gửi với máy (owner/manager) có được phép không. Lệnh ngoài bảng bị chặn.
"""

QUYEN_DONG_BO = {
    "dong_bo_nguyen_lieu": {"owner", "manager"},
}

# Lệnh app gửi qua /app/gui-lenh và vai trò được gửi; lệnh ngoài bảng bị chặn
# ở server, không chuyển xuống máy.
QUYEN_LENH = {
    "xem_nguyen_lieu": {"owner", "manager"},
    "dat_luong_nguyen_lieu": {"owner", "manager"},
    "them_nguyen_lieu": {"owner", "manager"},
    "tru_nguyen_lieu": {"owner", "manager"},
}

# Vai trò được nhận menu và gửi thay đổi món qua tab Menu (menu_sync/).
QUYEN_MENU = {"owner", "manager"}

# Vai trò được nạp kho qua /machine/refill.
QUYEN_NAP_KHO = {"owner", "manager"}
