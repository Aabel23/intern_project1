> Hồ sơ nội bộ cho agent. Chuyển từ tài liệu HTML ngày 06/10/2026; nội dung và bằng chứng cũ được giữ, chưa kiểm lại sản phẩm. Sơ đồ gốc giữ dưới dạng mã SVG trong khối XML.

[G3 · Sức chứa và tiến triển lệnh máy](index.md) / PHASE CON

# G3.4 · Budgets, lỗi đồng thời và phục hồi

Deadline tổng, log sink và kết quả muộn có thể làm mất khả dụng hoặc báo sai semantics.

Nghiên cứu + yêu cầu + kế hoạch triển khai cả team

## Nhiệm vụ phase con

Deadline tổng, log sink và kết quả muộn có thể làm mất khả dụng hoặc báo sai semantics.

| Thuộc phase lớn | Điều kiện vào | Task nguồn | Trạng thái |
| --- | --- | --- | --- |
| [G3 · Sức chứa và tiến triển lệnh máy](index.md) | Contract/schema/quyết định và evidence của G3.3 | C04, C05, O02, O03 | CHƯA THỰC HIỆN |

## Nghiên cứu chi tiết và thông tin đã biết

| Nguồn trong repo | Hiện trạng được đọc từ mã |
| --- | --- |
| [server/lib/machine/machine_transport.py:71](../../../../../../server/lib/machine/machine_transport.py) | Timeout chưa lấy xóa lệnh, đã lấy trả kết quả chưa chắc chắn. |
| [server/lib/machine/machine_transport.py:25](../../../../../../server/lib/machine/machine_transport.py) | Counter command reset về 1 khi process mới. |
| [server/lib/machine/machine_transport.py:94](../../../../../../server/lib/machine/machine_transport.py) | deliver ghép machine_id + id, chưa có generation. |

Các nhận định hiện trạng trên là nghiên cứu mã; experiments bên dưới chưa chạy trong đợt lập kế hoạch. Đối chiếu lại source/line trước code vì workspace có thể tiếp tục thay đổi. Không dùng nghiên cứu để khẳng định lỗ hổng đã tái hiện hoặc tính năng đã đạt.

## Định hướng kỹ thuật và vấn đề cần chốt

Đo stages và sink overhead, bound logging, không retry write. Thử late result qua restart như giả thuyết từ code: old ID có thể trùng new ID; chưa claim tái hiện. Nếu chứng minh, tạo quyết định khắc phục trước rollout, không đẩy lỗi chặn sang backlog dài hạn.

- Threshold nào đã đo trên target, threshold nào vẫn giả định?
- Chống ID reuse cần generation/UUID hay cơ chế tương thích nhỏ hơn?

Phương án ngoài định hướng chỉ chọn khi có bằng chứng và decision record. Nếu thay packet/status/schema/interface, planner liệt kê toàn bộ caller app/server/machine/tests trước giao coder. Không mở registry, import feature nội bộ hoặc refactor ngoài scope.

## Yêu cầu bắt buộc của phase

| Mã | Yêu cầu | Trạng thái |
| --- | --- | --- |
| G3.4-R1 | Budget body/admission/auth/DB/wait/write từ số đo. | CHƯA KIỂM |
| G3.4-R2 | Timeout chưa take và đã take khác nhau, không hứa rollback vật lý. | CHƯA KIỂM |
| G3.4-R3 | Soak/burst→recovery kiểm RSS/thread/queue/permits/log sink. | CHƯA KIỂM |
| G3.4-R4 | Old result sau restart không được hoàn tất new command; nếu hiện fail, ghi blocker và interface change cần chốt. | CHƯA KIỂM |

## Sơ đồ triển khai và dữ liệu bàn giao

Từ nghiên cứu tới nghiệm thu G3.4

```xml
<svg aria-label="Từ nghiên cứu tới nghiệm thu G3.4" role="img" viewbox="0 0 1120 175" xmlns="http://www.w3.org/2000/svg"><title>Từ nghiên cứu tới nghiệm thu G3.4</title><rect fill="#e4f3f0" height="100" rx="8" stroke="#218777" width="230" x="20" y="20"></rect><text fill="#254154" font-size="17" font-weight="600" text-anchor="middle" x="135" y="54">Nghiên cứu / spec</text><text fill="#476474" font-size="13" text-anchor="middle" x="135" y="79.0">Nguồn + assumptions +</text><text fill="#476474" font-size="13" text-anchor="middle" x="135" y="96.0">requirements</text><path d="M250 65L289 65" fill="none" stroke="#527184" stroke-width="2"></path><path d="M289 65l-7 -5v10z" fill="#527184"></path><rect fill="#e4f3f0" height="100" rx="8" stroke="#218777" width="230" x="295" y="20"></rect><text fill="#254154" font-size="17" font-weight="600" text-anchor="middle" x="410" y="54">Test / design review</text><text fill="#476474" font-size="13" text-anchor="middle" x="410" y="87">Scenario + expected outcome</text><path d="M525 65L564 65" fill="none" stroke="#527184" stroke-width="2"></path><path d="M564 65l-7 -5v10z" fill="#527184"></path><rect fill="#e4f3f0" height="100" rx="8" stroke="#218777" width="230" x="570" y="20"></rect><text fill="#254154" font-size="17" font-weight="600" text-anchor="middle" x="685" y="54">Patch / đo kiểm</text><text fill="#476474" font-size="13" text-anchor="middle" x="685" y="87">Diff + raw logs + sample data</text><path d="M800 65L839 65" fill="none" stroke="#527184" stroke-width="2"></path><path d="M839 65l-7 -5v10z" fill="#527184"></path><rect fill="#e4f3f0" height="100" rx="8" stroke="#218777" width="230" x="845" y="20"></rect><text fill="#254154" font-size="17" font-weight="600" text-anchor="middle" x="960" y="54">Review / lead gate</text><text fill="#476474" font-size="13" text-anchor="middle" x="960" y="79.0">Findings + acceptance + next</text><text fill="#476474" font-size="13" text-anchor="middle" x="960" y="96.0">inputs</text></svg>
```

Sơ đồ quy trình team đề xuất. Dữ liệu qua các khối là hiện vật bàn giao, không credential/payload sản phẩm.

Luồng dữ liệu sản phẩm và nhánh timeout xem [mô hình dữ liệu/command](../../data-model.md); biên thành phần xem [kiến trúc](../../architecture.md). Các sơ đồ kỹ thuật tương ứng nằm trong [chuyên đề nguồn](../../capacity.md).

## Sơ đồ khối hoạt động và dữ liệu của phase con

Mô hình triển khai cần kiểm — G3.4

```xml
<svg aria-label="Mô hình triển khai cần kiểm — G3.4" role="img" viewbox="0 0 1120 175" xmlns="http://www.w3.org/2000/svg"><title>Mô hình triển khai cần kiểm — G3.4</title><rect fill="#e4f3f0" height="100" rx="8" stroke="#218777" width="230" x="20" y="20"></rect><text fill="#254154" font-size="17" font-weight="600" text-anchor="middle" x="135" y="54">Stage samples</text><text fill="#476474" font-size="13" text-anchor="middle" x="135" y="87">Read/queue/DB/wait/write</text><path d="M250 65L289 65" fill="none" stroke="#527184" stroke-width="2"></path><path d="M289 65l-7 -5v10z" fill="#527184"></path><rect fill="#e4f3f0" height="100" rx="8" stroke="#218777" width="230" x="295" y="20"></rect><text fill="#254154" font-size="17" font-weight="600" text-anchor="middle" x="410" y="54">Command state</text><text fill="#476474" font-size="13" text-anchor="middle" x="410" y="87">Queued/taken/unknown/result</text><path d="M525 65L564 65" fill="none" stroke="#527184" stroke-width="2"></path><path d="M564 65l-7 -5v10z" fill="#527184"></path><rect fill="#e4f3f0" height="100" rx="8" stroke="#218777" width="230" x="570" y="20"></rect><text fill="#254154" font-size="17" font-weight="600" text-anchor="middle" x="685" y="54">Fault / restart</text><text fill="#476474" font-size="13" text-anchor="middle" x="685" y="87">ID reuse / late / sink fail</text><path d="M800 65L839 65" fill="none" stroke="#527184" stroke-width="2"></path><path d="M839 65l-7 -5v10z" fill="#527184"></path><rect fill="#e4f3f0" height="100" rx="8" stroke="#218777" width="230" x="845" y="20"></rect><text fill="#254154" font-size="17" font-weight="600" text-anchor="middle" x="960" y="54">Recovery proof</text><text fill="#476474" font-size="13" text-anchor="middle" x="960" y="87">No cross-result / bounded RAM</text></svg>
```

Sơ đồ định hướng cho phase con; không phải bằng chứng feature đã chạy. Dữ liệu ghi tên trường/hiện vật, không giá trị credential. Nhánh lỗi và acceptance nằm trong requirements và test matrix.

## Việc cần làm theo thứ tự

Tester chuẩn bị phép kiểm và tái hiện trước sửa khi là bug; coder nhận spec/test rồi viết patch; không sửa test của tester để làm pass. Task dưới đây là phần việc của phase con, không là phase lớn độc lập.

<a id="C04"></a>

C04

### Deadline tổng và hủy đúng nghĩa

Điều kiện vào
:   C01–C03, timeout model.

Bước thực hiện
:   1. Budget body/admission/auth/DB/send/write bằng monotonic.
    2. Không tự cancel command đã take khi protocol chưa có cancel/ack.
    3. Không auto retry write; sau timeout đối soát dữ liệu.
    4. Deadline truyền xuyên flow nếu cần là interface change cập nhật caller/tests cùng đợt.

File / phạm vi
:   HTTP/config/transport; caller khi behavior đổi.

Xong khi / phép kiểm
:   Chưa lấy/đã lấy/trễ phân biệt, không thực thi lặp vì retry mù.

Nhánh lỗi / cần giữ
:   Disconnect không rollback máy, write latency không chứng minh command chưa chạy.

Đầu ra
:   Measured budget và cancel/retry decision.

Đề xuất · Chưa triển khai

<a id="C05"></a>

C05

### Bão hòa rồi phục hồi

Điều kiện vào
:   Bản ứng viên C01–C04 và harness đã chuẩn bị từ G0.4; chạy scenarios candidate ở G3. V02/V03 tại G5 là nghiệm thu tổng hợp, không là cổng phải đạt trước C05.

Bước thực hiện
:   1. Burst/sustained load/many NAT/full limiter/slow clients.
    2. Tăng rồi giảm tải; ghi slots/queue/thread/RSS residual.
    3. Đo heartbeat stale, timeout/reject theo nhóm, p95 stages.
    4. Sau dừng load kiểm login người mới/logout/read/status trở lại.

File / phạm vi
:   Load/fault tools trong tests/; ngưỡng config.

Xong khi / phép kiểm
:   Có raw logs, số mẫu/lỗi/profile, không deadlock/starvation tái hiện.

Nhánh lỗi / cần giữ
:   Chưa workload thật thì không công bố capacity sản phẩm.

Đầu ra
:   Capacity report và gate G3.

Đề xuất · Chưa triển khai

<a id="O02"></a>

O02

### Đo stages và correlation

Điều kiện vào
:   O01/D04.

Bước thực hiện
:   1. Đo tại điểm thật; absent cho khối chưa đo, không 0 giả.
    2. Queue/admission wait tách command wait; hook take/result nếu cần.
    3. Tổng stage không double count interval lồng; so total để thấy overhead còn thiếu.
    4. Đo observability bật/tắt trên cùng profile.

File / phạm vi
:   HTTP/transport hooks; tools tests/.

Xong khi / phép kiểm
:   Raw samples tính lại được, reviewer phân biệt wait máy với HTTP overhead.

Nhánh lỗi / cần giữ
:   Không cộng p95 stages để suy p95 tổng.

Đầu ra
:   JSONL và bảng timing trước/sau.

Đề xuất · Chưa triển khai

<a id="O03"></a>

O03

### Sink bounded, retention, degraded mode

Điều kiện vào
:   O01, tải đã đo.

Bước thực hiện
:   1. Đo synchronous log trước; queue chỉ khi có lý do.
    2. Nếu queue: cap/drop policy/drop counter, không block result vô hạn.
    3. Rotate/retention/access/disk-full theo môi trường.
    4. Test sink lỗi/event lớn/burst, release vẫn hoàn tất.

File / phạm vi
:   Log/config helper; operations.md.

Xong khi / phép kiểm
:   RAM/disk bounded, sink lỗi có signal và không leak fallback.

Nhánh lỗi / cần giữ
:   Không infrastructure phức tạp khi chưa cần.

Đầu ra
:   Retention policy và sink failure test.

Đề xuất · Chưa triển khai

## Phân công và hợp đồng bàn giao

| Vai | Công việc tại phase này | Hiện vật bắt buộc |
| --- | --- | --- |
| Lead | Kiểm đầu vào G3.3, khóa scope, giao và đối chiếu nghiệm thu. | Decision mở/đóng gate, findings còn mở, phase tiếp có inputs. |
| Planner | Giải nghiên cứu/câu hỏi tại phần định hướng; map C04, C05, O02, O03 và callers. | Spec/ADR: source→decision→requirements→files→tests. |
| Tester | Thực hiện scenarios ở matrix, test tái hiện/hồi quy và samples cần thiết. | Test source + input/expected + lệnh/output/exit + môi trường/giới hạn. |
| Coder | Triển khai đúng yêu cầu, chỉ ghi sản phẩm của task được giao. | Diff/file/caller + CODE_STYLE checklist + lệnh tự kiểm. |
| Reviewer | Sau patch/output: kiểm requirements, scope, contract, concurrency/rollback theo diff. | Finding có trigger/source/consequence + trạng thái xử lý. |
| Cybersecurity | Rà biên tin cậy/secret/resource/identity phù hợp yêu cầu phase. | Security requirements/negative evidence/residual risks, không claim exploit chưa chạy. |

## Phép kiểm, yêu cầu bằng chứng và cổng phase con

| Tình huống | Cách kiểm | Kết quả cần thấy |
| --- | --- | --- |
| Load↑ rồi ↓ + sink fail | Harness từ G0.4, V02/V03 chuẩn bị sớm | Resource phục hồi, control progress |
| Restart rồi old/new id trùng cùng máy | Test local trạng thái/process mô phỏng | Không old result ghép mới; fail là blocker cần quyết định |

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
