# BRIEF — Viết bộ tài liệu luồng `docs/flows/`

## Yêu cầu gốc

"gọi các agent lên opus low thôi, song song hoàn thiện từng document, bạn suy nghĩ và giao việc, kèm cả hướng dẫn và đặc tả trước cho chúng"

Mỗi agent viết **đúng một** file HTML trong `docs/flows/`. Trang này giải thích sâu một luồng app ↔ server ↔ máy cho người mới vào dự án: luồng chạy ra sao, dữ liệu nằm ở đâu, vì sao code làm vậy, chỗ nào dễ hỏng.

## Người đọc

Lập trình viên mới vào `project1_app`. Họ biết Python/Flutter nhưng chưa đọc code. Đọc xong phải tự sửa được luồng mà không phá hợp đồng gói tin.

## Ràng buộc cứng

- Chỉ tạo file được giao. **Không sửa** code, test, README, `docs/manual/`, `docs/README.md` hay file của agent khác.
- Mọi khẳng định phải đối chiếu được với code của nhánh hiện tại (`refactor/heartbeat-long-poll`). Dẫn `file:dòng` hoặc tên hàm. Khi README/`*_FLOW.html` cũ lệch với code, **lấy code làm chuẩn** và ghi chỗ lệch vào khối `note crit`.
- Không bịa con số. Timeout, TTL, giới hạn kích thước... phải lấy từ code (`server/config/config.py`, hằng trong module) và ghi nguồn.
- Viết tiếng Việt, câu ngắn, giữ nguyên tên hàm, route, trường JSON.
- Code máy nằm ở `version1.1/machine/`. Thư mục `machine/` ở gốc repo chỉ còn `__pycache__`, đừng dẫn tới đó.

## Nguồn nên đọc trước

- `server/config/routing.py` (route server), `app/flutter_app/lib/config/` (route app)
- `server/service/<module>/README.md` và `*_FLOW.html` của module mình phụ trách. Đây là tài liệu cũ, chỉ dùng làm gợi ý.
- `server/lib/machine/machine_transport.py` (relay, online)
- `app/flutter_app/lib/feature/<feature>/`
- `log/SECURITY_NOTES.md` (SEC-xx liên quan đến luồng của mình)
- Tests: `tests/python/`, `tests/flutter/`
- Trang mẫu đã có trong cùng thư mục: `docs/flows/menu-ingredient-sync.html`. Tham khảo cách dẫn dắt, nhưng **không** dùng CSS của nó.

## Thiết kế bắt buộc: chuẩn FexMix_Munual

Bắt đầu bằng cách chép `docs/assets/template.html`. Giữ nguyên `<style>` và script renderer, chỉ thay nội dung. Trang mẫu chất lượng: `../FexMix_Munual.html` (ở `internproj/`, ngoài repo). Đọc lướt để so mức hoàn thiện, không chép nội dung.

Sửa phần đầu file: thay 3 dòng Google Fonts (`preconnect` ×2 + stylesheet) bằng `<link rel="stylesheet" href="../assets/fonts.css">`. Giữ Mermaid `11.4.1` từ jsDelivr. Footer ghi rõ "font chạy offline; sơ đồ Mermaid cần mạng, không có mạng sẽ hiện mã nguồn sơ đồ".

### Khung trang

1. **Masthead**:
   - Eyebrow: `Tài liệu luồng · project1_app`.
   - H1 là một câu nói luồng làm gì, không chỉ ghi tên luồng.
   - Meta bên phải: nhánh + commit (`git log -1 --format=%h`), ngày 10/10/2026, quy mô (số route, số file).
2. **Mục 1 · Bức tranh toàn cục**:
   - SVG vẽ tay theo class `ov`, chia 3 vùng App / Server / Máy (`zn`).
   - Đường đi chính tô màu accent, có huy hiệu số thứ tự (`bd`).
   - Có legend và figcaption diễn giải bằng chữ.
3. **Mục 2 · Luồng chính**:
   - Chọn một ví dụ đại diện, vẽ bằng sequence diagram `autonumber`.
   - Kèm bảng "Trong sơ đồ → Trong mã nguồn → Vai trò".
4. **Từng thành phần** (`article.comp`, tiêu đề `N.M · Tên`):
   - Dòng `src` gồm file, loại sơ đồ, số bước.
   - Mục "Làm gì", sơ đồ, rồi "Các bước" (`ol.steps`). Mỗi bước nói **vì sao**.
   - Thành phần có vòng đời (phiên, mã mời, lệnh...) thì dùng `stateDiagram`.
5. **Hợp đồng gói tin**: bảng request/response từng route, gồm trường, kiểu và mã lỗi/`status` có thể trả.
6. **Lỗi và giới hạn**:
   - Bảng "tình huống → app thấy gì → nên làm gì".
   - Bảng thông số `td.num` (timeout, TTL, giới hạn).
   - Ghi SEC-xx còn mở.
7. **Khi sửa code**: những chỗ phải đổi cùng lúc (app `routing.dart` / server `routing.py` / máy / test).
8. **Footer**.

### Màu theo nghĩa (giữ nguyên ở mọi sơ đồ)

| Class | Nghĩa |
|---|---|
| `ui` (xanh dương) | Màn hình, người dùng |
| `proc` (cam) | Xử lý |
| `hot` (viền đỏ dày) | Điểm rủi ro |
| `hw` (tím) | Phần cứng |
| `store` (xám) | Dữ liệu bền |
| `file` (xám, viền đứt) | File cầu nối |
| `dec` / `human` (vàng) | Quyết định / chờ người |
| `ok` (xanh lá) | Kết thúc tốt |
| `bad` (đỏ) | Hỏng |
| `muted` (xám, viền đứt) | Hết hạn, bỏ qua |

### Quy tắc sơ đồ

- Khối chỉ ghi tên gốc (tên trong code) và số ①②. Chi tiết đưa sang bảng nổi `figure.dg.dg-split` + `aside.dg-side`. Hàng nhóm `tr.grp` mang đúng số và tên khối.
- Mũi tên không xéo. Khai báo nhánh chính trước để nó nằm ngang. Dùng `A ~~~ B` để kéo nút về cùng hàng.
- `stateDiagram`:
  - Dùng `direction LR`.
  - Nhãn 2 dòng: `hàm()<br/>giải thích`.
  - Tô màu trạng thái bằng `class`.
- Mermaid: không dùng `;` trong nhãn, vì Mermaid coi nó là dấu tách câu. Không viết `&gt;` thô trong nhãn state.
- Mỗi sơ đồ có figcaption bắt đầu bằng "Nguồn:" và chỉ hàm/file cụ thể.

## Kiểm trước khi giao

1. Kiểm link: mọi `href`/`src` tương đối phải trỏ tới file có thật. Tính từ `docs/flows/`, về gốc repo là `../../`.
2. Chụp bằng `/usr/bin/google-chrome --headless=new --screenshot=<out>.png --window-size=1400,<cao> --virtual-time-budget=8000 file://<path>`, ở 1400 px và 420 px. Lưu ảnh vào thư mục scratchpad riêng được giao. Mở ảnh xem:
   - Không tràn ngang.
   - Sơ đồ Mermaid đã render, không hiện lỗi "Syntax error".
   - Bảng cạnh sơ đồ xuống dưới ở màn hẹp.
   - Mũi tên không cắt nhau.
3. Muốn chụp một mục: chép file sang scratchpad, chèn CSS ẩn các phần khác ngay sau `<style>`. Không chụp theo `#id`, vì trang cuộn mượt nên ảnh sẽ trắng. Bản chép phải sửa đường dẫn `../assets/` thành đường dẫn tuyệt đối.

## Báo cáo khi xong (trả về cho điều phối, ≤ 25 dòng)

- File đã tạo, số mục, số sơ đồ.
- Kết quả kiểm link và ảnh chụp (đường dẫn ảnh).
- Các chỗ code lệch tài liệu cũ, các lỗi/rủi ro phát hiện trong code. **Chỉ báo, không sửa.**
- Điều chưa kiểm được.
