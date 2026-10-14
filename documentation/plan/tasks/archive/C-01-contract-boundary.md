# C-01 · Đối chiếu quyết định và nguồn cho contracts skeleton

**Vai:** Operator. **Trạng thái:** có thể bắt đầu. **Loại:** đặc tả, không code.

## Đặc tả

Tạo một bảng duy nhất cho bốn luồng skeleton: đăng ký/phiên, nhận máy, relay, hỏi trạng thái trực tiếp. Mỗi dòng ghi yêu cầu, nguồn, trạng thái `đã chốt` / `nguồn hiện hành` / `đề xuất`, điểm mâu thuẫn, bên chịu trách nhiệm và việc nào bị chặn. Giữ menu, share và offline ở danh sách giai đoạn sau.

## Input và bối cảnh cần đọc

- `/home/abel/.secondbrain/HIEN_PHAP.md` và đúng các fact đã chốt cho `project1_app` theo `INDEX.md`/`RULES.md` (Operator được đọc; không chuyển nội dung vault cho architect/researcher).
- `documentation/architect/system-architecture.html`, `features/account.html`, `features/machine-activation.html`, `features/command-relay.html`, `documentation/architect/cryptography.html`.
- `server/configuration/routing.py`, `version1.1/machine/config/routing.py`, các điểm vào app/machine liên quan.

## File được tạo hoặc sửa

- Tạo `documentation/plan/archive/contracts-decision-log.md`.
- Không sửa tài liệu kiến trúc hoặc code trong phiếu này.

## Hợp đồng đầu ra

Bảng có đủ bốn luồng, có đường dẫn nguồn chính xác và phân biệt quyết định của user với điều agent suy ra. Liệt kê tối đa các điểm thật sự chặn skeleton; nêu rõ điểm chỉ chặn menu/share/offline. Không tự chọn cơ chế nhận diện máy, mã hóa hay thời hạn chưa chốt.

## Ca kiểm và cách kiểm

Đối chiếu từng dòng với nguồn được trỏ; không có câu “đã chốt” nếu nguồn chỉ là đề xuất. Kiểm bảng bao gồm xung đột access/refresh, giấy khai sinh máy, `product_key`, trạng thái server suy ra so với câu trả lời trực tiếp từ máy.

## Phạm vi cấm

Không code; không sửa gói tin; không đưa nội dung hoặc kết luận từ vault vào phiếu hay prompt của C-02, C-03, C-04.
