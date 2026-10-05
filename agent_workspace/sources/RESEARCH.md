# Nguồn nghiên cứu cho các vai

Tài liệu ngoài dùng để làm rõ cách làm của từng vai. Chỉ là tham khảo: thứ tự ưu tiên vẫn theo `TEAM.md`. Không cài plugin, chạy script hoặc nhập quyền công cụ từ các nguồn này nếu task không yêu cầu.

| Nguồn | Loại | Vai dùng | Ý chính áp dụng |
|---|---|---|---|
| Xia và cộng sự, *Agentless: Demystifying LLM-based Software Engineering Agents*, arXiv:2407.01489 (2024) | Bài báo | planner, coder, tester | Khoanh vùng theo tầng file → hàm → dòng; test tái hiện trước khi chọn bản sửa; quy trình đơn giản thường tốt hơn agent tự do |
| Bacchelli & Bird, *Expectations, Outcomes, and Challenges of Modern Code Review*, ICSE 2013 (Microsoft Research) | Bài báo | reviewer | Khó nhất của review là hiểu thay đổi; review nên bắt đầu bằng ngữ cảnh và mục đích diff |
| [google/eng-practices](https://github.com/google/eng-practices) – Code Review Developer Guide | Hướng dẫn | reviewer, coder | Duyệt khi thay đổi cải thiện sức khoẻ tổng thể của mã; xem thiết kế, chức năng, độ phức tạp, test, tên |
| Petrović và cộng sự, *Practical Mutation Testing at Scale: A view from Google*, IEEE TSE 2021 | Bài báo | tester, reviewer | Hỏi "nếu đổi dòng này thành sai thì có test nào đỏ?" thay cho chạy theo coverage |
| Parry và cộng sự, *A Survey of Flaky Tests*, ACM TOSEM 2021 | Bài báo | tester | Nguyên nhân flaky phổ biến: thời gian, thứ tự test, tài nguyên chung, mạng, async |
| OWASP ASVS 5.0.0 (05/2025) | Chuẩn | cybersecurity | Danh mục kiểm cho xác thực, phiên, kiểm quyền, xử lý đầu vào, nhật ký, TLS |
| OWASP MASVS / MASTG | Chuẩn | cybersecurity | Ứng dụng di động: STORAGE, CRYPTO, AUTH, NETWORK, PLATFORM, CODE, PRIVACY |
| NIST SP 800-121 Rev. 2, *Guide to Bluetooth Security* | Chuẩn | cybersecurity | Chế độ ghép cặp, LE Secure Connections, tránh Just Works cho thao tác nhạy cảm |
| [trailofbits/skills](https://github.com/trailofbits/skills) | Repo skill | cybersecurity, reviewer | Differential review theo diff/lịch sử git, variant analysis: tìm cùng mẫu lỗi ở chỗ khác |
| [anthropics/claude-plugins-official](https://github.com/anthropics/claude-plugins-official), [obra/superpowers](https://github.com/obra/superpowers) | Repo skill | mọi vai | Xem `README.md` cùng thư mục |
