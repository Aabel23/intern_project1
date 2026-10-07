# Dùng team agent

1. Đọc `AGENT.md` và `TEAM.md` từ gốc `androidv1.0`.
2. Nếu chưa có hai repo trong `sources/`, clone theo `sources/README.md`.
3. Chạy `python agent_workspace/sync_agents.py` để chép 6 vai đang dùng vào `.claude/agents/`. Nếu phiên Claude Code đã mở trước khi thư mục này được tạo, mở phiên mới.
4. Tạo `tasks/<tên>/TASK.md` từ `tasks/TEMPLATE.md`, giữ nguyên yêu cầu gốc. Lead giao vai theo bảng trong `TEAM.md`.
5. Chạy `python agent_workspace/sync_agents.py --check` sau khi sửa file vai. Lệnh này chỉ kiểm sự đồng bộ, không sửa file.

Luồng chuẩn: ý tưởng → hai architect phản biện → HTML người dùng chốt → planner
chia phase nhỏ → coder → reviewer độc lập → cập nhật ✓/✗ và lặp tới hoàn thiện.
Chi tiết tại TEAM.md.

Người dùng đọc vài trang HTML hệ thống: mặc định `tasks/<tên>/index.html`,
chỉ thêm 1–2 trang theo nội dung khi cần. Middleware hiện có tổng quan, kiến trúc/luồng
và bảo vệ gói tin; trang kiến trúc phải đủ feature/luồng và index có sơ đồ tiến độ.
Nghiên cứu chi tiết, kế hoạch phase lớn/phase con, phân công và bằng
chứng giữ bằng Markdown trong `TASK.md` và `internal/`; xem `PHASE_FORMAT.md`.

`agents/` là nguồn chỉnh sửa duy nhất; `.claude/agents/` là bản sinh tại máy và được Git bỏ qua. `agents/hacker.md` không được đăng ký tự động. Hai repo tham khảo, commit và cách clone lại được ghi ở `sources/README.md`; bản clone cũng được Git bỏ qua.
