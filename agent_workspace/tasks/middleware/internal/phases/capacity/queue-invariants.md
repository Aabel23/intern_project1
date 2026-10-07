> Hồ sơ nội bộ cho agent. Chuyển từ tài liệu HTML ngày 06/10/2026; nội dung và bằng chứng cũ được giữ, chưa kiểm lại sản phẩm. Sơ đồ gốc giữ dưới dạng mã SVG trong khối XML.

[G3 · Sức chứa và tiến triển lệnh máy](index.md) / PHASE CON

# G3.3 · Queue, waiter và cleanup

HOP_THU/DANG_CHO không có bound; reject hoặc race có thể để orphan waiter.

Nghiên cứu + yêu cầu + kế hoạch triển khai cả team

## Nhiệm vụ phase con

HOP_THU/DANG_CHO không có bound; reject hoặc race có thể để orphan waiter.

| Thuộc phase lớn | Điều kiện vào | Task nguồn | Trạng thái |
| --- | --- | --- | --- |
| [G3 · Sức chứa và tiến triển lệnh máy](index.md) | Contract/schema/quyết định và evidence của G3.2 | C03, D03 | CHƯA THỰC HIỆN |

## Nghiên cứu chi tiết và thông tin đã biết

| Nguồn trong repo | Hiện trạng được đọc từ mã |
| --- | --- |
| [server/lib/machine/machine_transport.py:19](../../../../../../server/lib/machine/machine_transport.py) | Mail/pending/heartbeat sống RAM. |
| [server/lib/machine/machine_transport.py:55](../../../../../../server/lib/machine/machine_transport.py) | Insert waiter và append mailbox dưới KHOA. |
| [server/lib/machine/machine_transport.py:63](../../../../../../server/lib/machine/machine_transport.py) | Pending được xóa trong finally. |

Các nhận định hiện trạng trên là nghiên cứu mã; experiments bên dưới chưa chạy trong đợt lập kế hoạch. Đối chiếu lại source/line trước code vì workspace có thể tiếp tục thay đổi. Không dùng nghiên cứu để khẳng định lỗ hổng đã tái hiện hoặc tính năng đã đạt.

## Định hướng kỹ thuật và vấn đề cần chốt

Bound per-machine/global theo measurements; admission+insert nguyên tử. Lifecycle queued/taken/completed/timed-out rõ; cleanup state rỗng phải không xóa state đang sống.

- Admission bound tại HTTP và transport chia ownership thế nào?
- Một máy có nhiều poll có phá guarantee thứ tự hay không?

Phương án ngoài định hướng chỉ chọn khi có bằng chứng và decision record. Nếu thay packet/status/schema/interface, planner liệt kê toàn bộ caller app/server/machine/tests trước giao coder. Không mở registry, import feature nội bộ hoặc refactor ngoài scope.

## Yêu cầu bắt buộc của phase

| Mã | Yêu cầu | Trạng thái |
| --- | --- | --- |
| G3.3-R1 | Reject trước enqueue không tạo waiter/lệnh rác. | CHƯA KIỂM |
| G3.3-R2 | Không silently drop command đã nhận. | CHƯA KIỂM |
| G3.3-R3 | Cleanup/release một lần, mọi lỗi/timeout đều có owner. | CHƯA KIỂM |
| G3.3-R4 | Giữ đúng machine_id+id correlation; state phục hồi về mức giải thích được. | CHƯA KIỂM |

## Sơ đồ triển khai và dữ liệu bàn giao

Từ nghiên cứu tới nghiệm thu G3.3

```xml
<svg aria-label="Từ nghiên cứu tới nghiệm thu G3.3" role="img" viewbox="0 0 1120 175" xmlns="http://www.w3.org/2000/svg"><title>Từ nghiên cứu tới nghiệm thu G3.3</title><rect fill="#e4f3f0" height="100" rx="8" stroke="#218777" width="230" x="20" y="20"></rect><text fill="#254154" font-size="17" font-weight="600" text-anchor="middle" x="135" y="54">Nghiên cứu / spec</text><text fill="#476474" font-size="13" text-anchor="middle" x="135" y="79.0">Nguồn + assumptions +</text><text fill="#476474" font-size="13" text-anchor="middle" x="135" y="96.0">requirements</text><path d="M250 65L289 65" fill="none" stroke="#527184" stroke-width="2"></path><path d="M289 65l-7 -5v10z" fill="#527184"></path><rect fill="#e4f3f0" height="100" rx="8" stroke="#218777" width="230" x="295" y="20"></rect><text fill="#254154" font-size="17" font-weight="600" text-anchor="middle" x="410" y="54">Test / design review</text><text fill="#476474" font-size="13" text-anchor="middle" x="410" y="87">Scenario + expected outcome</text><path d="M525 65L564 65" fill="none" stroke="#527184" stroke-width="2"></path><path d="M564 65l-7 -5v10z" fill="#527184"></path><rect fill="#e4f3f0" height="100" rx="8" stroke="#218777" width="230" x="570" y="20"></rect><text fill="#254154" font-size="17" font-weight="600" text-anchor="middle" x="685" y="54">Patch / đo kiểm</text><text fill="#476474" font-size="13" text-anchor="middle" x="685" y="87">Diff + raw logs + sample data</text><path d="M800 65L839 65" fill="none" stroke="#527184" stroke-width="2"></path><path d="M839 65l-7 -5v10z" fill="#527184"></path><rect fill="#e4f3f0" height="100" rx="8" stroke="#218777" width="230" x="845" y="20"></rect><text fill="#254154" font-size="17" font-weight="600" text-anchor="middle" x="960" y="54">Review / lead gate</text><text fill="#476474" font-size="13" text-anchor="middle" x="960" y="79.0">Findings + acceptance + next</text><text fill="#476474" font-size="13" text-anchor="middle" x="960" y="96.0">inputs</text></svg>
```

Sơ đồ quy trình team đề xuất. Dữ liệu qua các khối là hiện vật bàn giao, không credential/payload sản phẩm.

Luồng dữ liệu sản phẩm và nhánh timeout xem [mô hình dữ liệu/command](../../data-model.md); biên thành phần xem [kiến trúc](../../architecture.md). Các sơ đồ kỹ thuật tương ứng nằm trong [chuyên đề nguồn](../../capacity.md).

## Sơ đồ khối hoạt động và dữ liệu của phase con

Mô hình triển khai cần kiểm — G3.3

```xml
<svg aria-label="Mô hình triển khai cần kiểm — G3.3" role="img" viewbox="0 0 1120 175" xmlns="http://www.w3.org/2000/svg"><title>Mô hình triển khai cần kiểm — G3.3</title><rect fill="#e4f3f0" height="100" rx="8" stroke="#218777" width="230" x="20" y="20"></rect><text fill="#254154" font-size="17" font-weight="600" text-anchor="middle" x="135" y="54">Validated command</text><text fill="#476474" font-size="13" text-anchor="middle" x="135" y="87">Machine/action/data</text><path d="M250 65L289 65" fill="none" stroke="#527184" stroke-width="2"></path><path d="M289 65l-7 -5v10z" fill="#527184"></path><rect fill="#e4f3f0" height="100" rx="8" stroke="#218777" width="230" x="295" y="20"></rect><text fill="#254154" font-size="17" font-weight="600" text-anchor="middle" x="410" y="54">Bound + enqueue</text><text fill="#476474" font-size="13" text-anchor="middle" x="410" y="87">Per-machine/global nguyên tử</text><path d="M525 65L564 65" fill="none" stroke="#527184" stroke-width="2"></path><path d="M564 65l-7 -5v10z" fill="#527184"></path><rect fill="#e4f3f0" height="100" rx="8" stroke="#218777" width="230" x="570" y="20"></rect><text fill="#254154" font-size="17" font-weight="600" text-anchor="middle" x="685" y="54">Take / waiter / result</text><text fill="#476474" font-size="13" text-anchor="middle" x="685" y="87">Correlation dưới khóa</text><path d="M800 65L839 65" fill="none" stroke="#527184" stroke-width="2"></path><path d="M839 65l-7 -5v10z" fill="#527184"></path><rect fill="#e4f3f0" height="100" rx="8" stroke="#218777" width="230" x="845" y="20"></rect><text fill="#254154" font-size="17" font-weight="600" text-anchor="middle" x="960" y="54">Cleanup</text><text fill="#476474" font-size="13" text-anchor="middle" x="960" y="87">Timeout/reject không orphan</text></svg>
```

Sơ đồ định hướng cho phase con; không phải bằng chứng feature đã chạy. Dữ liệu ghi tên trường/hiện vật, không giá trị credential. Nhánh lỗi và acceptance nằm trong requirements và test matrix.

## Việc cần làm theo thứ tự

Tester chuẩn bị phép kiểm và tái hiện trước sửa khi là bug; coder nhận spec/test rồi viết patch; không sửa test của tester để làm pass. Task dưới đây là phần việc của phase con, không là phase lớn độc lập.

<a id="C03"></a>

C03

### Bound command queue theo máy và tổng

Điều kiện vào
:   C02/D03 inventory.

Bước thực hiện
:   1. Đo pending/queue depth per-machine/global.
    2. Acquire trước append, reject không tạo DANG_CHO/command rác.
    3. Release đúng khi take/result/timeout/finally theo state machine; lock không bao wait.
    4. Kiểm máy chậm không làm máy nhanh mất dịch vụ; nhiều app cùng máy.

File / phạm vi
:   machine_transport.py; flow/caller nếu overload response mới.

Xong khi / phép kiểm
:   Không exceed bound hoặc drop âm thầm command đã nhận; pending phục hồi.

Nhánh lỗi / cần giữ
:   Nhiều poll cùng máy có thể đổi thứ tự thực thi; kiểm topology trước bảo đảm FIFO.

Đầu ra
:   Queue/overload contract và cleanup proof.

Đề xuất · Chưa triển khai

<a id="D03"></a>

D03

### Bounded state và cleanup

Điều kiện vào
:   C01–C03; inventory state.

Bước thực hiện
:   1. Inventory RAM owner/lock/TTL/cleanup: transport, limiter, OTP/register.
    2. Trần queue/pending theo số đo; quá tải reject trước enqueue, không drop lệnh đã nhận.
    3. Kiểm timeout/disconnect/late/wrong result/restart; cleanup dưới lock phù hợp.
    4. Sau burst so residual state với baseline; cache bounded có giải thích.

File / phạm vi
:   machine_transport.py; limiter; trạng thái feature giữ feature.

Xong khi / phép kiểm
:   State không tăng vô hạn, queue/permit về mức giải thích được.

Nhánh lỗi / cần giữ
:   Bound transport có thể cần overload contract mới, cập nhật caller/test.

Đầu ra
:   Retention inventory và cleanup proof.

Đề xuất · Chưa triển khai

## Phân công và hợp đồng bàn giao

| Vai | Công việc tại phase này | Hiện vật bắt buộc |
| --- | --- | --- |
| Lead | Kiểm đầu vào G3.2, khóa scope, giao và đối chiếu nghiệm thu. | Decision mở/đóng gate, findings còn mở, phase tiếp có inputs. |
| Planner | Giải nghiên cứu/câu hỏi tại phần định hướng; map C03, D03 và callers. | Spec/ADR: source→decision→requirements→files→tests. |
| Tester | Thực hiện scenarios ở matrix, test tái hiện/hồi quy và samples cần thiết. | Test source + input/expected + lệnh/output/exit + môi trường/giới hạn. |
| Coder | Triển khai đúng yêu cầu, chỉ ghi sản phẩm của task được giao. | Diff/file/caller + CODE_STYLE checklist + lệnh tự kiểm. |
| Reviewer | Sau patch/output: kiểm requirements, scope, contract, concurrency/rollback theo diff. | Finding có trigger/source/consequence + trạng thái xử lý. |
| Cybersecurity | Rà biên tin cậy/secret/resource/identity phù hợp yêu cầu phase. | Security requirements/negative evidence/residual risks, không claim exploit chưa chạy. |

## Phép kiểm, yêu cầu bằng chứng và cổng phase con

| Tình huống | Cách kiểm | Kết quả cần thấy |
| --- | --- | --- |
| Queue full từng máy/tổng | Concurrency controlled | Reject rõ, máy khác còn progress |
| Take/timeout/deliver race | Event/barrier | Không orphan/cross-result hoặc double release |

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
