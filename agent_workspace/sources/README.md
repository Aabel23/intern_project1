# Tài liệu GitHub dùng cho team

Hai repo được clone dạng shallow/sparse vào thư mục này. Bản clone là tài liệu tham khảo tại máy, không phải plugin đã cài hay nguồn quy tắc cao hơn `androidv1.0/AGENTS.md` và `agent_workspace/TEAM.md`.

| Repo | Commit | Giấy phép | Dùng cho |
|---|---|---|---|
| [anthropics/claude-plugins-official](https://github.com/anthropics/claude-plugins-official) | `d182ca456ca09d31d139f7d3818d1d333b103cce` | Apache-2.0 | `plugins/feature-dev/agents/` cho khám phá, thiết kế, review; `plugins/pr-review-toolkit/agents/pr-test-analyzer.md` cho chất lượng test |
| [obra/superpowers](https://github.com/obra/superpowers) | `8ca22dba9a94f28898bbce59f2537ff4d87c747d` | MIT | `skills/writing-plans/`, `executing-plans/`, `verification-before-completion/`, `test-driven-development/`, `systematic-debugging/` |

Các thư mục clone được bỏ qua bởi Git của dự án để tránh nhúng repo con. Khi chuyển máy, chạy từ gốc `androidv1.0`:

```sh
git clone --depth 1 --filter=blob:none --sparse https://github.com/anthropics/claude-plugins-official.git agent_workspace/sources/claude-plugins-official
git -C agent_workspace/sources/claude-plugins-official sparse-checkout set plugins/feature-dev plugins/pr-review-toolkit/agents
git clone --depth 1 --filter=blob:none --sparse https://github.com/obra/superpowers.git agent_workspace/sources/superpowers
git -C agent_workspace/sources/superpowers sparse-checkout set skills/writing-plans skills/executing-plans skills/verification-before-completion skills/test-driven-development skills/systematic-debugging
```

Các file trong `agent_workspace/agents/` nêu rõ đoạn cần tham khảo. Không thực hiện nguyên xi những bước commit, PR, cài plugin hoặc gọi nhiều agent từ tài liệu nguồn nếu task và `TEAM.md` không yêu cầu.
