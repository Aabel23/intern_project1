> Hồ sơ nội bộ cho agent. Chuyển từ tài liệu HTML ngày 06/10/2026; nội dung và bằng chứng cũ được giữ, chưa kiểm lại sản phẩm. Sơ đồ gốc giữ dưới dạng mã SVG trong khối XML.

[G4 · Danh tính, quyền và chính sách bảo vệ](index.md) / PHASE CON

# G4.3 · Quyền, transaction và privacy trạng thái

Role middleware stale có thể phá khóa đọc-quyền-rồi-ghi; GET status đang public.

Nghiên cứu + yêu cầu + kế hoạch triển khai cả team

## Nhiệm vụ phase con

Role middleware stale có thể phá khóa đọc-quyền-rồi-ghi; GET status đang public.

| Thuộc phase lớn | Điều kiện vào | Task nguồn | Trạng thái |
| --- | --- | --- | --- |
| [G4 · Danh tính, quyền và chính sách bảo vệ](index.md) | Contract/schema/quyết định và evidence của G4.2 | D02, S04 | CHƯA THỰC HIỆN |

## Nghiên cứu chi tiết và thông tin đã biết

| Nguồn trong repo | Hiện trạng được đọc từ mã |
| --- | --- |
| [server/service/dashboard_sync/machinelist_sync/machine_list_remove.py:22](../../../../../../server/service/dashboard_sync/machinelist_sync/machine_list_remove.py) | BEGIN IMMEDIATE đặt trước kiểm owner/manager trong cùng conn. |
| [server/service/dashboard_sync/machinelist_sync/machine_list_get.py:29](../../../../../../server/service/dashboard_sync/machinelist_sync/machine_list_get.py) | machine_status hiện không cần token. |

Các nhận định hiện trạng trên là nghiên cứu mã; experiments bên dưới chưa chạy trong đợt lập kế hoạch. Đối chiếu lại source/line trước code vì workspace có thể tiếp tục thay đổi. Không dùng nghiên cứu để khẳng định lỗ hổng đã tái hiện hoặc tính năng đã đạt.

## Định hướng kỹ thuật và vấn đề cần chốt

Giữ role/conn/transaction trong tác vụ. Thay privacy GET là decision contract có Flutter/server/tests đồng bộ; không đưa token query hoặc mặc định status đã được bảo vệ.

- Privacy status thực cần mức nào?
- SQLite busy ở BEGIN IMMEDIATE được map lỗi/rollback ra sao?

Phương án ngoài định hướng chỉ chọn khi có bằng chứng và decision record. Nếu thay packet/status/schema/interface, planner liệt kê toàn bộ caller app/server/machine/tests trước giao coder. Không mở registry, import feature nội bộ hoặc refactor ngoài scope.

## Yêu cầu bắt buộc của phase

| Mã | Yêu cầu | Trạng thái |
| --- | --- | --- |
| G4.3-R1 | Owner/manager/stranger behavior giữ đúng action. | CHƯA KIỂM |
| G4.3-R2 | Remove/revoke/accept race không stale quyền dẫn ghi trái phép. | CHƯA KIỂM |
| G4.3-R3 | Exception giữa ghi rollback bằng get_connection. | CHƯA KIỂM |
| G4.3-R4 | Siết GET nếu chốt phải cập nhật caller và tests, không thay lẻ server. | CHƯA KIỂM |

## Sơ đồ triển khai và dữ liệu bàn giao

Từ nghiên cứu tới nghiệm thu G4.3

```xml
<svg aria-label="Từ nghiên cứu tới nghiệm thu G4.3" role="img" viewbox="0 0 1120 175" xmlns="http://www.w3.org/2000/svg"><title>Từ nghiên cứu tới nghiệm thu G4.3</title><rect fill="#e4f3f0" height="100" rx="8" stroke="#218777" width="230" x="20" y="20"></rect><text fill="#254154" font-size="17" font-weight="600" text-anchor="middle" x="135" y="54">Nghiên cứu / spec</text><text fill="#476474" font-size="13" text-anchor="middle" x="135" y="79.0">Nguồn + assumptions +</text><text fill="#476474" font-size="13" text-anchor="middle" x="135" y="96.0">requirements</text><path d="M250 65L289 65" fill="none" stroke="#527184" stroke-width="2"></path><path d="M289 65l-7 -5v10z" fill="#527184"></path><rect fill="#e4f3f0" height="100" rx="8" stroke="#218777" width="230" x="295" y="20"></rect><text fill="#254154" font-size="17" font-weight="600" text-anchor="middle" x="410" y="54">Test / design review</text><text fill="#476474" font-size="13" text-anchor="middle" x="410" y="87">Scenario + expected outcome</text><path d="M525 65L564 65" fill="none" stroke="#527184" stroke-width="2"></path><path d="M564 65l-7 -5v10z" fill="#527184"></path><rect fill="#e4f3f0" height="100" rx="8" stroke="#218777" width="230" x="570" y="20"></rect><text fill="#254154" font-size="17" font-weight="600" text-anchor="middle" x="685" y="54">Patch / đo kiểm</text><text fill="#476474" font-size="13" text-anchor="middle" x="685" y="87">Diff + raw logs + sample data</text><path d="M800 65L839 65" fill="none" stroke="#527184" stroke-width="2"></path><path d="M839 65l-7 -5v10z" fill="#527184"></path><rect fill="#e4f3f0" height="100" rx="8" stroke="#218777" width="230" x="845" y="20"></rect><text fill="#254154" font-size="17" font-weight="600" text-anchor="middle" x="960" y="54">Review / lead gate</text><text fill="#476474" font-size="13" text-anchor="middle" x="960" y="79.0">Findings + acceptance + next</text><text fill="#476474" font-size="13" text-anchor="middle" x="960" y="96.0">inputs</text></svg>
```

Sơ đồ quy trình team đề xuất. Dữ liệu qua các khối là hiện vật bàn giao, không credential/payload sản phẩm.

Luồng dữ liệu sản phẩm và nhánh timeout xem [mô hình dữ liệu/command](../../data-model.md); biên thành phần xem [kiến trúc](../../architecture.md). Các sơ đồ kỹ thuật tương ứng nằm trong [chuyên đề nguồn](../../data-model.md).

## Sơ đồ khối hoạt động và dữ liệu của phase con

Mô hình triển khai cần kiểm — G4.3

```xml
<svg aria-label="Mô hình triển khai cần kiểm — G4.3" role="img" viewbox="0 0 1120 175" xmlns="http://www.w3.org/2000/svg"><title>Mô hình triển khai cần kiểm — G4.3</title><rect fill="#e4f3f0" height="100" rx="8" stroke="#218777" width="230" x="20" y="20"></rect><text fill="#254154" font-size="17" font-weight="600" text-anchor="middle" x="135" y="54">User + machine</text><text fill="#476474" font-size="13" text-anchor="middle" x="135" y="87">Đã kiểm phiên</text><path d="M250 65L289 65" fill="none" stroke="#527184" stroke-width="2"></path><path d="M289 65l-7 -5v10z" fill="#527184"></path><rect fill="#e4f3f0" height="100" rx="8" stroke="#218777" width="230" x="295" y="20"></rect><text fill="#254154" font-size="17" font-weight="600" text-anchor="middle" x="410" y="54">BEGIN IMMEDIATE</text><text fill="#476474" font-size="13" text-anchor="middle" x="410" y="87">Đọc quyền cùng conn khi cần</text><path d="M525 65L564 65" fill="none" stroke="#527184" stroke-width="2"></path><path d="M564 65l-7 -5v10z" fill="#527184"></path><rect fill="#e4f3f0" height="100" rx="8" stroke="#218777" width="230" x="570" y="20"></rect><text fill="#254154" font-size="17" font-weight="600" text-anchor="middle" x="685" y="54">Role/task/SQL</text><text fill="#476474" font-size="13" text-anchor="middle" x="685" y="87">Owner/manager/stranger</text><path d="M800 65L839 65" fill="none" stroke="#527184" stroke-width="2"></path><path d="M839 65l-7 -5v10z" fill="#527184"></path><rect fill="#e4f3f0" height="100" rx="8" stroke="#218777" width="230" x="845" y="20"></rect><text fill="#254154" font-size="17" font-weight="600" text-anchor="middle" x="960" y="54">Commit / rollback</text><text fill="#476474" font-size="13" text-anchor="middle" x="960" y="87">Sai quyền không side effect</text></svg>
```

Sơ đồ định hướng cho phase con; không phải bằng chứng feature đã chạy. Dữ liệu ghi tên trường/hiện vật, không giá trị credential. Nhánh lỗi và acceptance nằm trong requirements và test matrix.

## Việc cần làm theo thứ tự

Tester chuẩn bị phép kiểm và tái hiện trước sửa khi là bug; coder nhận spec/test rồi viết patch; không sửa test của tester để làm pass. Task dưới đây là phần việc của phase con, không là phase lớn độc lập.

<a id="D02"></a>

D02

### Bảo toàn transaction quyền và ghi

Điều kiện vào
:   B01 matrix, G0 regression.

Bước thực hiện
:   1. Khoanh remove/revoke/accept và các flow đọc quyền rồi ghi.
    2. Giữ BEGIN IMMEDIATE trước đọc quyền của remove, helper nhận cùng conn.
    3. Test cạnh tranh revoke/remove/accept bằng barrier, assert trạng thái cuối.
    4. Inject lỗi giữa nhiều ghi để kiểm rollback; sai quyền không gửi command.

File / phạm vi
:   [`server/service/dashboard_sync/machinelist_sync/machine_list_remove.py`](../../../../../../server/service/dashboard_sync/machinelist_sync/machine_list_remove.py); share tasks/tests.

Xong khi / phép kiểm
:   Không stale role gây vượt quyền; rollback giữ consistency.

Nhánh lỗi / cần giữ
:   Không transaction bao app chờ máy 20s.

Đầu ra
:   Concurrency evidence và sơ đồ transaction.

Đề xuất · Chưa triển khai

<a id="S04"></a>

S04

### Quyền GET status và device threat model

Điều kiện vào
:   B01; yêu cầu riêng tư trạng thái máy.

Bước thực hiện
:   1. Ghi GET status hiện công khai online/last_seen.
    2. Đề xuất auth/can_manage nếu cần, tìm Flutter GET caller và cách gửi credential không query.
    3. Người giữ tem key có thể giả heartbeat/poll/result; ghi rủi ro còn mở.
    4. Device credential riêng chuyển E02, không nói middleware sửa key đã lộ.

File / phạm vi
:   machine_list_get/main; Flutter status; tests nếu contract đổi; device protocol riêng.

Xong khi / phép kiểm
:   Nếu đổi, stranger bị chặn và app vẫn đọc được; nếu chưa đổi có risk record.

Nhánh lỗi / cần giữ
:   GET token transport thay là decision contract riêng; không đưa token URL.

Đầu ra
:   Status privacy/device identity decisions.

Đề xuất · Chưa triển khai

## Phân công và hợp đồng bàn giao

| Vai | Công việc tại phase này | Hiện vật bắt buộc |
| --- | --- | --- |
| Lead | Kiểm đầu vào G4.2, khóa scope, giao và đối chiếu nghiệm thu. | Decision mở/đóng gate, findings còn mở, phase tiếp có inputs. |
| Planner | Giải nghiên cứu/câu hỏi tại phần định hướng; map D02, S04 và callers. | Spec/ADR: source→decision→requirements→files→tests. |
| Tester | Thực hiện scenarios ở matrix, test tái hiện/hồi quy và samples cần thiết. | Test source + input/expected + lệnh/output/exit + môi trường/giới hạn. |
| Coder | Triển khai đúng yêu cầu, chỉ ghi sản phẩm của task được giao. | Diff/file/caller + CODE_STYLE checklist + lệnh tự kiểm. |
| Reviewer | Sau patch/output: kiểm requirements, scope, contract, concurrency/rollback theo diff. | Finding có trigger/source/consequence + trạng thái xử lý. |
| Cybersecurity | Rà biên tin cậy/secret/resource/identity phù hợp yêu cầu phase. | Security requirements/negative evidence/residual risks, không claim exploit chưa chạy. |

## Phép kiểm, yêu cầu bằng chứng và cổng phase con

| Tình huống | Cách kiểm | Kết quả cần thấy |
| --- | --- | --- |
| Revoke/remove race | Event/barrier + DB tạm | Role final/SQL consistent |
| Stranger GET status | Contract test | Hiện public được ghi hoặc policy mới triển khai đồng bộ |

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
