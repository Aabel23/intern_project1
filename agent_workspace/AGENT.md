# Điểm vào của team agent

Làm việc từ gốc `androidv1.0`. Đọc `AGENTS.md` và `agent_workspace/TEAM.md` trước khi giao hoặc nhận việc. Lead là phiên chính; các vai ở `agent_workspace/agents/` được đăng ký vào Claude Code bằng `python agent_workspace/sync_agents.py`.

Mỗi việc dùng một `agent_workspace/tasks/<tên>/TASK.md` theo `tasks/TEMPLATE.md`. Operator chạy quy trình hai architect → người dùng chốt HTML → planner → coder → reviewer độc lập → sơ đồ tiến độ theo TEAM.md. Repo trong `sources/` là tài liệu tham khảo; không nhập nguyên quy trình hoặc quyền công cụ của chúng.

Khi thay endpoint hoặc gói tin, kiểm app, server và machine. Test Python trên loopback không xác nhận đường HTTPS qua Caddy. E2E điện thoại, Bluetooth, service thật và phần cứng cần task nêu rõ môi trường và phạm vi kiểm.
