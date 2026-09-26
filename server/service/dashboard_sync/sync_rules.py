"""Lệnh đọc dữ liệu dashboard app được gửi qua /app/dong-bo.

Server không hiểu dữ liệu, chỉ kiểm tra: lệnh có trong bảng và vai trò của
người gửi với máy (owner/manager) có được phép không. Lệnh ngoài bảng bị chặn.
"""

QUYEN_DONG_BO = {
    "dong_bo_nguyen_lieu": {"owner", "manager"},
}

# Vai trò được nạp kho qua /machine/refill.
QUYEN_NAP_KHO = {"owner", "manager"}
