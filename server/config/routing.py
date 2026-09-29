"""Đường dẫn HTTP của server, chia theo module xử lý."""

# Tên route: ĐỐI_TƯỢNG_MỤC_TIÊU_HÀNH_ĐỘNG (xem MODULE_PATTERN.md).

# Đăng ký tài khoản và xác minh OTP
USER_ACCOUNT_REGISTER = "/app/dang-ky-nguoi-dung"
USER_OTP_SEND = "/app/gui-ma-otp"
USER_OTP_VERIFY = "/app/xac-minh-otp"

# Đăng nhập, lấy kết quả xác minh và đăng xuất
USER_SESSION_LOGIN = "/app/dang-nhap"
USER_LOGIN_VERIFY = "/app/xac-minh-dang-nhap"
USER_SESSION_LOGOUT = "/app/dang-xuat"

# Đăng ký máy qua QR hoặc Bluetooth
USER_MACHINE_REGISTER = "/app/dang-ky-may"

# Chia sẻ máy và quản lý quyền nhân viên
MACHINE_SHARE_CREATE = "/app/tao-ma-chia-se"
MACHINE_SHARE_ACCEPT = "/app/nhan-chia-se"
MACHINE_STAFF_LIST = "/app/nhan-vien-may"
MACHINE_STAFF_REVOKE = "/app/thu-hoi-quyen"

# Dashboard — danh sách, đổi tên, gỡ máy và trạng thái kết nối
USER_MACHINE_LIST = "/app/may-cua-toi"
MACHINE_NAME_UPDATE = "/app/doi-ten-may"
USER_MACHINE_REMOVE = "/app/go-may"
MACHINE_STATUS_GET = "/machine/trang-thai"  # GET, app gọi

# Dashboard — đồng bộ Menu
MACHINE_MENU_GET = "/app/nhan-menu"
MACHINE_MENU_UPDATE = "/app/cap-nhat-menu"

# Dashboard — đồng bộ và nạp Kho
MACHINE_INGREDIENT_GET = "/app/nhan-kho"
MACHINE_INGREDIENT_REFILL = "/app/nap-kho"

# Cổng máy — heartbeat, long-poll nhận lệnh và trả kết quả
MACHINE_HEARTBEAT_SEND = "/machine/heartbeat"
MACHINE_COMMAND_POLL = "/machine/hoi-lenh"
MACHINE_RESULT_SEND = "/machine/tra-ket-qua"
