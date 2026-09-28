"""Đường dẫn HTTP của server, chia theo module xử lý."""

# Đăng ký tài khoản và xác minh OTP
APP_REGISTER_USER = "/app/dang-ky-nguoi-dung"
APP_SEND_OTP = "/app/gui-ma-otp"
APP_VERIFY_OTP = "/app/xac-minh-otp"

# Đăng nhập, lấy kết quả xác minh và đăng xuất
APP_LOGIN = "/app/dang-nhap"
APP_VERIFY_LOGIN = "/app/xac-minh-dang-nhap"
APP_LOGOUT = "/app/dang-xuat"

# Đăng ký máy qua QR hoặc Bluetooth
APP_REGISTER_MACHINE = "/app/dang-ky-may"

# Chia sẻ máy và quản lý quyền nhân viên
APP_CREATE_SHARE = "/app/tao-ma-chia-se"
APP_ACCEPT_SHARE = "/app/nhan-chia-se"
APP_MACHINE_STAFF = "/app/nhan-vien-may"
APP_REVOKE_STAFF = "/app/thu-hoi-quyen"

# Dashboard — danh sách, đổi tên, gỡ máy và trạng thái kết nối
APP_MY_MACHINES = "/app/may-cua-toi"
APP_RENAME_MACHINE = "/app/doi-ten-may"
APP_REMOVE_MACHINE = "/app/go-may"
MACHINE_STATUS = "/machine/trang-thai"  # GET, app gọi

# Dashboard — đồng bộ Menu
APP_RECEIVE_MENU = "/app/nhan-menu"
APP_SEND_MENU = "/app/gui-menu"

# Dashboard — đồng bộ và nạp Kho
APP_RECEIVE_INGREDIENTS = "/app/nhan-kho"
APP_REFILL = "/app/nap-kho"

# Cổng máy — heartbeat, long-poll nhận lệnh và trả kết quả
MACHINE_HEARTBEAT = "/machine/heartbeat"
MACHINE_POLL_COMMAND = "/machine/hoi-lenh"
MACHINE_SEND_RESULT = "/machine/tra-ket-qua"
