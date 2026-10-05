# Dùng team agent

1. Đọc `AGENT.md` và `TEAM.md` từ gốc `androidv1.0`.
2. Nếu chưa có hai repo trong `sources/`, clone theo `sources/README.md`.
3. Chạy `python agent_workspace/sync_agents.py` để chép 5 vai đang dùng vào `.claude/agents/`. Nếu phiên Claude Code đã mở trước khi thư mục này được tạo, mở phiên mới.
4. Tạo `tasks/<tên>/TASK.md` từ `tasks/TEMPLATE.md`, giữ nguyên yêu cầu gốc. Lead giao vai theo bảng trong `TEAM.md`.
5. Chạy `python agent_workspace/sync_agents.py --check` sau khi sửa file vai. Lệnh này chỉ kiểm sự đồng bộ, không sửa file.

Task được chia phase theo `PHASE_FORMAT.md`. Mỗi phase có `phase-XX.html` để người dùng đọc, theo bố cục của `../phase-00.pdf`; planner nêu nội dung, lead tạo và cập nhật báo cáo bằng kết quả thực tế.

`agents/` là nguồn chỉnh sửa duy nhất; `.claude/agents/` là bản sinh tại máy và được Git bỏ qua. `agents/hacker.md` không được đăng ký tự động. Hai repo tham khảo, commit và cách clone lại được ghi ở `sources/README.md`; bản clone cũng được Git bỏ qua.
