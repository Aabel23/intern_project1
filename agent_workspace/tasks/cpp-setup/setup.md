> Hồ sơ nội bộ cho agent. Chuyển từ tài liệu HTML ngày 06/10/2026; nội dung và bằng chứng cũ được giữ, chưa kiểm lại sản phẩm. Sơ đồ gốc giữ dưới dạng mã SVG trong khối XML.

# Cài môi trường C++ cho VS Code

Phase 00 · 05/10/2026 · Trạng thái: hoàn tất

## Bạn cần biết

Extension và cấu hình workspace đã hoàn tất. Máy Ubuntu 26.04 có g++ 15.2.0 và GDB 17.1. Đã kiểm tra biên dịch, nhập/xuất và breakpoint.

## Component và thứ tự

| Thành phần | Kết quả |
| --- | --- |
| Extension C/C++ | ms-vscode.cpptools 1.34.4 đã cài |
| Compiler và debugger | g++ 15.2.0 và GDB 17.1 đã sẵn sàng |
| Workspace | .vscode/tasks.json, launch.json, c_cpp_properties.json |

## Cách hoàn tất và sử dụng

Chạy trong Terminal:

```
sudo apt update && sudo apt install -y build-essential gdb
```

Mở file .cpp. Ctrl+Shift+B biên dịch với C++17. F5 biên dịch và debug; Ctrl+F5 chạy không debug. Chương trình được tạo cạnh file nguồn. Cấu hình áp dụng cho chương trình một file trong workspace này; dự án nhiều file cần điều chỉnh task.

## Kết quả kiểm và tiêu chí hoàn tất

Lệnh cài extension trả exit code 0. Sudo -n true trả exit code 1 vì yêu cầu xác thực. Kiểm tra hoàn tất: g++ biên dịch C++17 với -Wall -Wextra -g, exit code 0; chương trình nhận 12 30 và in Sum: 42, exit code 0. GDB đặt breakpoint tại main và dừng đúng, exit code 0. Ba file cấu hình VS Code đọc được dưới dạng JSON. Chưa kiểm thao tác phím trong giao diện VS Code; compiler và debugger đã kiểm bằng dòng lệnh.

## Giới hạn đối chiếu

Đã đọc agent_workspace/PHASE_FORMAT.md. Không tìm thấy ../phase-00.pdf, nên chưa đối chiếu hình thức với mẫu PDF.
