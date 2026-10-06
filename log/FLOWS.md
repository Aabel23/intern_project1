# Theo dõi luồng kiểm tra

Tự sinh bởi `tests/run_tests.py` (chạy qua `test.ps1`). Tiêu chí: `TIEU_CHI_TEST.md`.

| ID | Nhóm | Luồng | Trạng thái | Lần chạy cuối | Commit | Thời gian |
| --- | --- | --- | --- | --- | --- | --- |
| S10 | py | Ranh giới phụ thuộc và trách nhiệm của app | ĐẠT | 2026-09-29 11:22 | `5bf2710*` | 0s |
| S1 | py | HTTP chung cổng, rate limit, relay, long-poll | ĐẠT | 2026-09-29 11:22 | `5bf2710*` | 8s |
| S2 | py | Đăng ký + OTP | ĐẠT | 2026-09-29 11:22 | `5bf2710*` | 4s |
| S3 | py | Đăng nhập / đăng xuất | ĐẠT | 2026-09-29 11:22 | `5bf2710*` | 1s |
| S4 | py | Đăng ký máy (chủ đầu tiên) | ĐẠT | 2026-09-29 11:22 | `5bf2710*` | 3s |
| S5 | py | Chia sẻ máy, thu hồi nhân viên | ĐẠT | 2026-09-29 11:22 | `5bf2710*` | 1s |
| S6 | py | Tab Máy: danh sách, đổi tên, gỡ máy | ĐẠT | 2026-09-29 11:22 | `5bf2710*` | 1s |
| S7 | py | Gói pairing Bluetooth của máy | ĐẠT | 2026-09-29 11:22 | `5bf2710*` | 0s |
| S8 | py | Máy thật ↔ relay: lệnh, đồng bộ, nạp kho, chặn lệnh lạ | ĐẠT | 2026-09-29 11:22 | `5bf2710*` | 1s |
| S9 | py | Khởi tạo module: route trùng, khởi động lại giữ dữ liệu | ĐẠT | 2026-09-29 11:22 | `5bf2710*` | 1s |
| X1 | py | Kịch bản tấn công server (lỗ hổng đã biết = expectedFailure, xem SECURITY_NOTES) | ĐẠT | 2026-09-29 11:23 | `5bf2710*` | 38s |
| A1 | app | flutter analyze sạch | ĐẠT | 2026-09-29 07:46 | `1838d3e*` | 6s |
| A2 | app | Static check test Flutter ngoài package app | ĐẠT | 2026-09-29 07:46 | `1838d3e*` | 5s |
| F1 | app | Đăng nhập / đăng ký / OTP (widget) | ĐẠT | 2026-09-29 07:47 | `1838d3e*` | 24s |
| F2 | app | Dashboard: menu, kho, nạp, phiên hết hạn (widget) | ĐẠT | 2026-09-29 07:47 | `1838d3e*` | 7s |
| F3 | app | Danh sách máy đồng bộ server, máy offline (widget) | ĐẠT | 2026-09-29 07:47 | `1838d3e*` | 4s |
| F4 | app | Chia sẻ QR + xem/thu hồi nhân viên (widget) | ĐẠT | 2026-09-29 07:47 | `1838d3e*` | 6s |
| F5 | app | Chia sẻ qua Bluetooth (widget) | ĐẠT | 2026-09-29 07:47 | `1838d3e*` | 5s |
| F6 | app | Đổi tên / gỡ máy (widget) | ĐẠT | 2026-09-29 07:47 | `1838d3e*` | 7s |
| F8 | app | Gói Menu/Kho sai version không thay dữ liệu hợp lệ | ĐẠT | 2026-09-29 07:47 | `1838d3e*` | 4s |
| F7 | app | Đăng ký máy QR/Bluetooth (widget) | ĐẠT | 2026-09-29 07:47 | `1838d3e*` | 6s |
| E0 | e2e | Chuẩn bị: USB reverse, server, build/cài, cấp quyền | BỎ QUA | 2026-09-29 03:29 | `16fd283*` | - |
| E1 | e2e | Đăng nhập chủ | BỎ QUA | 2026-09-29 03:29 | `16fd283*` | - |
| E2 | e2e | Pair máy qua Bluetooth | BỎ QUA | 2026-09-29 03:29 | `16fd283*` | - |
| E3 | e2e | Máy online, menu, bật món, xem kho | BỎ QUA | 2026-09-29 03:29 | `16fd283*` | - |
| E4 | e2e | Nạp một bình + nạp tất cả | BỎ QUA | 2026-09-29 03:29 | `16fd283*` | - |
| E5 | e2e | Đổi tên máy | BỎ QUA | 2026-09-29 03:29 | `16fd283*` | - |
| E6 | e2e | Chia sẻ Bluetooth chủ → nhân viên | BỎ QUA | 2026-09-29 03:29 | `16fd283*` | - |
| E7 | e2e | Xem + thu hồi nhân viên | BỎ QUA | 2026-09-29 03:29 | `16fd283*` | - |
| E8 | e2e | Chia sẻ qua QR | BỎ QUA | 2026-09-29 03:29 | `16fd283*` | - |
| E9 | e2e | Đăng xuất xóa phiên server | BỎ QUA | 2026-09-29 03:29 | `16fd283*` | - |
| E10 | e2e | Nhân viên nhận chia sẻ Bluetooth | BỎ QUA | 2026-09-29 03:29 | `16fd283*` | - |
| E11 | e2e | Phiên hết hạn → về đăng nhập | BỎ QUA | 2026-09-29 03:29 | `16fd283*` | - |
| E12 | e2e | Bị thu hồi → máy biến mất khi tải lại | BỎ QUA | 2026-09-29 03:29 | `16fd283*` | - |
