> Hồ sơ nội bộ cho agent. Chuyển từ tài liệu HTML ngày 06/10/2026; nội dung và bằng chứng cũ được giữ, chưa kiểm lại sản phẩm. Sơ đồ gốc giữ dưới dạng mã SVG trong khối XML.

[G0 · Nền nghiên cứu và kiểm chứng](index.md) / PHASE CON

# G0.1 · Nghiên cứu hiện trạng và hợp đồng

Tài liệu/test còn mô tả login hai bước trong khi code đăng nhập hiện tại trả token một bước.

Nghiên cứu + yêu cầu + kế hoạch triển khai cả team

## Nhiệm vụ phase con

Tài liệu/test còn mô tả login hai bước trong khi code đăng nhập hiện tại trả token một bước.

| Thuộc phase lớn | Điều kiện vào | Task nguồn | Trạng thái |
| --- | --- | --- | --- |
| [G0 · Nền nghiên cứu và kiểm chứng](index.md) | Code/caller hiện tại, yêu cầu gốc và baseline lịch sử. | B01 | CHƯA THỰC HIỆN |

## Nghiên cứu chi tiết và thông tin đã biết

| Nguồn trong repo | Hiện trạng được đọc từ mã |
| --- | --- |
| [server/main.py:20](../../../../../../server/main.py) | MODULES import trực tiếp, mặc định chạy toàn bộ. |
| [server/config/routing.py:1](../../../../../../server/config/routing.py) | Route tập trung theo feature; HTTP method không suy từ tên hành động. |
| [server/service/user_login/user_login_process.py:1](../../../../../../server/service/user_login/user_login_process.py) | Flow hiện tại đăng nhập một bước; không LOGIN_STATES. |
| [app/flutter_app/lib/core/server_client.dart:29](../../../../../../app/flutter_app/lib/core/server_client.dart) | Caller account và machineData dùng hai hợp đồng phản hồi. |

Các nhận định hiện trạng trên là nghiên cứu mã; experiments bên dưới chưa chạy trong đợt lập kế hoạch. Đối chiếu lại source/line trước code vì workspace có thể tiếp tục thay đổi. Không dùng nghiên cứu để khẳng định lỗ hổng đã tái hiện hoặc tính năng đã đạt.

## Định hướng kỹ thuật và vấn đề cần chốt

Lần từ route → main → task → database/transport → caller; lấy behavior thực làm snapshot. Đoạn tài liệu cũ chỉ sửa thông tin sau đối chiếu, không khôi phục code cũ.

- Hành vi nào được người dùng chốt nhưng code/test chưa theo?
- Caller nào cần cập nhật nếu siết HTTP hoặc auth?

Phương án ngoài định hướng chỉ chọn khi có bằng chứng và decision record. Nếu thay packet/status/schema/interface, planner liệt kê toàn bộ caller app/server/machine/tests trước giao coder. Không mở registry, import feature nội bộ hoặc refactor ngoài scope.

## Yêu cầu bắt buộc của phase

| Mã | Yêu cầu | Trạng thái |
| --- | --- | --- |
| G0.1-R1 | Mỗi route có method/path/owner, MAX_BODY, auth, shape lỗi và caller. | CHƯA KIỂM |
| G0.1-R2 | Phân biệt body parse trước auth và validate nghiệp vụ sau auth/quyền. | CHƯA KIỂM |
| G0.1-R3 | Danh sách public/app/machine gồm ngoại lệ GET trạng thái; không suy từ prefix. | CHƯA KIỂM |
| G0.1-R4 | Mâu thuẫn được phân loại tài liệu sai/test sai/bug thật/đổi yêu cầu. | CHƯA KIỂM |

## Sơ đồ triển khai và dữ liệu bàn giao

Từ nghiên cứu tới nghiệm thu G0.1

```xml
<svg aria-label="Từ nghiên cứu tới nghiệm thu G0.1" role="img" viewbox="0 0 1120 175" xmlns="http://www.w3.org/2000/svg"><title>Từ nghiên cứu tới nghiệm thu G0.1</title><rect fill="#e4f3f0" height="100" rx="8" stroke="#218777" width="230" x="20" y="20"></rect><text fill="#254154" font-size="17" font-weight="600" text-anchor="middle" x="135" y="54">Nghiên cứu / spec</text><text fill="#476474" font-size="13" text-anchor="middle" x="135" y="79.0">Nguồn + assumptions +</text><text fill="#476474" font-size="13" text-anchor="middle" x="135" y="96.0">requirements</text><path d="M250 65L289 65" fill="none" stroke="#527184" stroke-width="2"></path><path d="M289 65l-7 -5v10z" fill="#527184"></path><rect fill="#e4f3f0" height="100" rx="8" stroke="#218777" width="230" x="295" y="20"></rect><text fill="#254154" font-size="17" font-weight="600" text-anchor="middle" x="410" y="54">Test / design review</text><text fill="#476474" font-size="13" text-anchor="middle" x="410" y="87">Scenario + expected outcome</text><path d="M525 65L564 65" fill="none" stroke="#527184" stroke-width="2"></path><path d="M564 65l-7 -5v10z" fill="#527184"></path><rect fill="#e4f3f0" height="100" rx="8" stroke="#218777" width="230" x="570" y="20"></rect><text fill="#254154" font-size="17" font-weight="600" text-anchor="middle" x="685" y="54">Patch / đo kiểm</text><text fill="#476474" font-size="13" text-anchor="middle" x="685" y="87">Diff + raw logs + sample data</text><path d="M800 65L839 65" fill="none" stroke="#527184" stroke-width="2"></path><path d="M839 65l-7 -5v10z" fill="#527184"></path><rect fill="#e4f3f0" height="100" rx="8" stroke="#218777" width="230" x="845" y="20"></rect><text fill="#254154" font-size="17" font-weight="600" text-anchor="middle" x="960" y="54">Review / lead gate</text><text fill="#476474" font-size="13" text-anchor="middle" x="960" y="79.0">Findings + acceptance + next</text><text fill="#476474" font-size="13" text-anchor="middle" x="960" y="96.0">inputs</text></svg>
```

Sơ đồ quy trình team đề xuất. Dữ liệu qua các khối là hiện vật bàn giao, không credential/payload sản phẩm.

Luồng dữ liệu sản phẩm và nhánh timeout xem [mô hình dữ liệu/command](../../data-model.md); biên thành phần xem [kiến trúc](../../architecture.md). Các sơ đồ kỹ thuật tương ứng nằm trong [chuyên đề nguồn](../../baseline.md).

## Sơ đồ khối hoạt động và dữ liệu của phase con

Mô hình triển khai cần kiểm — G0.1

```xml
<svg aria-label="Mô hình triển khai cần kiểm — G0.1" role="img" viewbox="0 0 1120 175" xmlns="http://www.w3.org/2000/svg"><title>Mô hình triển khai cần kiểm — G0.1</title><rect fill="#e4f3f0" height="100" rx="8" stroke="#218777" width="230" x="20" y="20"></rect><text fill="#254154" font-size="17" font-weight="600" text-anchor="middle" x="135" y="54">Route/module</text><text fill="#476474" font-size="13" text-anchor="middle" x="135" y="87">Method / limits / auth</text><path d="M250 65L289 65" fill="none" stroke="#527184" stroke-width="2"></path><path d="M289 65l-7 -5v10z" fill="#527184"></path><rect fill="#e4f3f0" height="100" rx="8" stroke="#218777" width="230" x="295" y="20"></rect><text fill="#254154" font-size="17" font-weight="600" text-anchor="middle" x="410" y="54">Task + SQL</text><text fill="#476474" font-size="13" text-anchor="middle" x="410" y="87">Dữ liệu và side effects</text><path d="M525 65L564 65" fill="none" stroke="#527184" stroke-width="2"></path><path d="M564 65l-7 -5v10z" fill="#527184"></path><rect fill="#e4f3f0" height="100" rx="8" stroke="#218777" width="230" x="570" y="20"></rect><text fill="#254154" font-size="17" font-weight="600" text-anchor="middle" x="685" y="54">Caller + packet</text><text fill="#476474" font-size="13" text-anchor="middle" x="685" y="87">App/server/machine fields</text><path d="M800 65L839 65" fill="none" stroke="#527184" stroke-width="2"></path><path d="M839 65l-7 -5v10z" fill="#527184"></path><rect fill="#e4f3f0" height="100" rx="8" stroke="#218777" width="230" x="845" y="20"></rect><text fill="#254154" font-size="17" font-weight="600" text-anchor="middle" x="960" y="54">Snapshot</text><text fill="#476474" font-size="13" text-anchor="middle" x="960" y="87">Contract + open issues</text></svg>
```

Sơ đồ định hướng cho phase con; không phải bằng chứng feature đã chạy. Dữ liệu ghi tên trường/hiện vật, không giá trị credential. Nhánh lỗi và acceptance nằm trong requirements và test matrix.

## Việc cần làm theo thứ tự

Tester chuẩn bị phép kiểm và tái hiện trước sửa khi là bug; coder nhận spec/test rồi viết patch; không sửa test của tester để làm pass. Task dưới đây là phần việc của phase con, không là phase lớn độc lập.

<a id="B01"></a>

B01

### Lập snapshot hợp đồng thực

Điều kiện vào
:   Code/caller app/máy và tests/run_tests.py.

Bước thực hiện
:   1. Liệt kê method/path, module, MAX_BODY, auth và error shape từ code, không suy theo prefix.
    2. Ghi login một bước và endpoint đã bỏ; đối chiếu caller với test gọi route cũ.
    3. Đánh dấu mô tả cũ trong tài liệu để sửa thông tin, không đổi kiến trúc.
    4. Ghi riêng GET trạng thái đang công khai và quyền owner/manager theo action.

File / phạm vi
:   Routing, module main, caller, tài liệu khi lỗi thời.

Xong khi / phép kiểm
:   Ma trận có nguồn code; mọi mâu thuẫn có trạng thái/decision.

Nhánh lỗi / cần giữ
:   Không tái tạo login hai bước để test cũ pass.

Đầu ra
:   Snapshot contract và danh sách sai lệch.

Đề xuất · Chưa triển khai

## Phân công và hợp đồng bàn giao

| Vai | Công việc tại phase này | Hiện vật bắt buộc |
| --- | --- | --- |
| Lead | Kiểm đầu vào Không, khóa scope, giao và đối chiếu nghiệm thu. | Decision mở/đóng gate, findings còn mở, phase tiếp có inputs. |
| Planner | Giải nghiên cứu/câu hỏi tại phần định hướng; map B01 và callers. | Spec/ADR: source→decision→requirements→files→tests. |
| Tester | Thực hiện scenarios ở matrix, test tái hiện/hồi quy và samples cần thiết. | Test source + input/expected + lệnh/output/exit + môi trường/giới hạn. |
| Coder | Triển khai đúng yêu cầu, chỉ ghi sản phẩm của task được giao. | Diff/file/caller + CODE_STYLE checklist + lệnh tự kiểm. |
| Reviewer | Sau patch/output: kiểm requirements, scope, contract, concurrency/rollback theo diff. | Finding có trigger/source/consequence + trạng thái xử lý. |
| Cybersecurity | Rà biên tin cậy/secret/resource/identity phù hợp yêu cầu phase. | Security requirements/negative evidence/residual risks, không claim exploit chưa chạy. |

## Phép kiểm, yêu cầu bằng chứng và cổng phase con

| Tình huống | Cách kiểm | Kết quả cần thấy |
| --- | --- | --- |
| Route khai báo + caller | Đọc hai phía và test hiện có | Không endpoint/field bị bỏ sót |
| Login một bước | So flow và fixture | Không yêu cầu xác minh route đã bỏ |

Mỗi requirement R\* phải map tới test/quan sát cụ thể và output mới, hoặc CHƯA KIỂM kèm lý do/tác động. Thu lệnh đầy đủ, exit code, log dưới tests/artifacts/middleware/ khi thực hiện; measurements có số mẫu, p50/p95/lỗi và profile. Không claim pass bằng việc đọc code hoặc hình sơ đồ.

- Inputs/decision không còn mâu thuẫn chặn code.
- Tasks đạt requirements; tests hợp đồng liên quan không hồi quy.
- Review/security blocker đã xử lý và evidence cập nhật.
- Output được lead nhận, việc tiếp theo đủ input, phase trạng thái cập nhật.

## Nhánh lỗi, quay lui và phạm vi chưa thực hiện

- Nghiên cứu khác giả định→dừng task phụ thuộc, planner cập nhật spec/source và impact trước code.
- Test không đỏ trước sửa bug→tester xác minh scenario, không ép expected để tạo đỏ.
- Regression/secret leak/role violation/resource leak→không mở gate, coder sửa nguyên nhân và tester kiểm lại cùng điều kiện.
- Interface change ngoài scope→lead khoanh caller/compatibility; chưa triển khai ngầm.
- Quay lui patch/config theo task, giữ dữ liệu đã commit/máy đã chạy để đối soát; không replay write mù.
- Thiếu target/hardware→ghi CHƯA KIỂM; lead đánh giá có chặn rollout target không.

## Thông tin nghiên cứu tham khảo

- [Python HTTP](https://docs.python.org/3/library/http.server.html)
- [Python socketserver](https://docs.python.org/3/library/socketserver.html)
- [SQLite transactions](https://www.sqlite.org/lang_transaction.html)
- [OWASP logging](https://cheatsheetseries.owasp.org/cheatsheets/Logging_Cheat_Sheet.html)
- [OWASP resource bounds](https://api-security.owasp.org/editions/2023/en/0xa4-unrestricted-resource-consumption/)

Nguồn chính thức dùng cho nguyên tắc; khuyến nghị cụ thể trong phase là suy luận theo mã FlexMix. PDF đã được người dùng bỏ làm điều kiện, không ảnh hưởng tiến độ lập kế hoạch.
