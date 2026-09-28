"""Đường dẫn HTTP do server cung cấp, xếp theo module đăng ký route đó."""

# service/machine_link: cổng máy, chỉ máy gọi (xưng danh bằng product key)
MACHINE_HEARTBEAT = "/machine/heartbeat"
MACHINE_POLL_COMMAND = "/machine/hoi-lenh"
MACHINE_SEND_RESULT = "/machine/tra-ket-qua"

# service/user_register: đăng ký tài khoản + OTP
APP_REGISTER_USER = "/app/dang-ky-nguoi-dung"
APP_SEND_OTP = "/app/gui-ma-otp"
APP_VERIFY_OTP = "/app/xac-minh-otp"

# service/user_login: đăng nhập, đăng xuất
APP_LOGIN = "/app/dang-nhap"
APP_VERIFY_LOGIN = "/app/xac-minh-dang-nhap"
APP_LOGOUT = "/app/dang-xuat"

# service/machine_register: đăng ký máy (QR / Bluetooth)
APP_REGISTER_MACHINE = "/app/dang-ky-may"

# service/machine_share: mời nhân viên, xem và thu hồi quyền
APP_CREATE_SHARE = "/app/tao-ma-chia-se"
APP_ACCEPT_SHARE = "/app/nhan-chia-se"
APP_MACHINE_STAFF = "/app/nhan-vien-may"
APP_REVOKE_STAFF = "/app/thu-hoi-quyen"

# service/dashboard_sync/machinelist_sync: tab Máy
APP_MY_MACHINES = "/app/may-cua-toi"
APP_RENAME_MACHINE = "/app/doi-ten-may"
APP_REMOVE_MACHINE = "/app/go-may"
MACHINE_STATUS = "/machine/trang-thai"  # GET, app gọi

# service/dashboard_sync/menu_sync: tab Menu
APP_RECEIVE_MENU = "/app/nhan-menu"
APP_SEND_MENU = "/app/gui-menu"

# service/dashboard_sync/ingredient_sync: tab Kho
APP_RECEIVE_INGREDIENTS = "/app/nhan-kho"
APP_REFILL = "/app/nap-kho"
