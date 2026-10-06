Tiếp nhận công việc kiểm thử FlexMix từ Codex lúc 02:50 ngày 29/09/2026 (Asia/Bangkok).
Người dùng đã yêu cầu Claude thay phiên test, thêm kịch bản chức năng/bảo mật có ý nghĩa,
sửa bug có bằng chứng, ghi log và commit. Dừng công việc lúc 05:00 cùng ngày.

1. Đọc AGENTS.md, MODULE_PATTERN.md, git status/log và tests/reports/ trước khi sửa.
   Không hoàn tác thay đổi chưa commit của người dùng. Không thay kiến trúc đã chốt.
2. Repo: D:/PROJECT/CODE/InternProj/androidv0.1.
   Python: .venv/Scripts/python.exe; Flutter: E:/Development/flutter-sdk/bin/flutter.bat;
   ADB: D:/Users/NGOCTRAN/AppData/Local/Android/Sdk/platform-tools/adb.exe.
   Điện thoại Samsung SM_A256E, serial R5CWC220YTZ.
3. Giữ màn hình sáng khi cắm USB: adb shell svc power stayon usb; đánh thức bằng keyevent 224.
   Mọi test/công cụ mới nằm trong tests/. Python dùng database tạm.
4. Chạy Python discovery, Flutter analyze và flutter test ../../tests/flutter từ app/flutter_app.
   E2E: python tests/e2e/run_e2e.py; dùng --skip-build chỉ khi APK đúng source hiện tại.
   Không chạy hai lượt E2E đồng thời. Đọc log tests/runs/ và tests/e2e/logs/.
5. Có 6 expectedFailures bảo mật đã biết. Không xóa decorator để làm báo cáo đẹp.
   Thêm kịch bản dựa trên thiếu sót thực tế; phân biệt bug ứng dụng, bug automation và môi trường.
   Không tấn công dịch vụ bên ngoài, không đọc/in secret, không sửa dữ liệu ngoài các bản ghi E2E.
6. Đến 05:00 dừng loop, dọn tiến trình/dữ liệu E2E do mình tạo, ghi kết quả cuối vào
   tests/reports/claude-20260929.md và commit riêng các thay đổi đã kiểm chứng.
   Không push, không deploy, không gửi tin nhắn qua app ngoài.
7. Nếu tài khoản vẫn bị giới hạn token: ghi rõ vào tests/runs/claude-handoff.log và
   chạy tests/night_loop.py với --until 2026-09-29T05:00:00+07:00 để tiếp tục bộ test
   hiện có (xóa marker tests/runs/claude.takeover trước khi khởi động runner).
