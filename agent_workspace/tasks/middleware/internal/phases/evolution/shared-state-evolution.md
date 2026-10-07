> Hồ sơ nội bộ cho agent. Chuyển từ tài liệu HTML ngày 06/10/2026; nội dung và bằng chứng cũ được giữ, chưa kiểm lại sản phẩm. Sơ đồ gốc giữ dưới dạng mã SVG trong khối XML.

[G7 · Mở rộng dài hạn theo bằng chứng](index.md) / PHASE CON

# G7.4 · Scale-out, database và version API

Nhiều worker sẽ chia đôi RAM state; engine/broker mới không tự bảo đảm ownership và giao lệnh.

Nghiên cứu + yêu cầu + kế hoạch triển khai cả team

## Nhiệm vụ phase con

Nhiều worker sẽ chia đôi RAM state; engine/broker mới không tự bảo đảm ownership và giao lệnh.

| Thuộc phase lớn | Điều kiện vào | Task nguồn | Trạng thái |
| --- | --- | --- | --- |
| [G7 · Mở rộng dài hạn theo bằng chứng](index.md) | Contract/schema/quyết định và evidence của G6.4 | E05, E06 | CHƯA THỰC HIỆN |

## Nghiên cứu chi tiết và thông tin đã biết

| Nguồn trong repo | Hiện trạng được đọc từ mã |
| --- | --- |
| [server/lib/machine/machine_transport.py:19](../../../../../../server/lib/machine/machine_transport.py) | Hộp thư và pending thuộc process. |
| [server/lib/http/http_rate_limit.py:10](../../../../../../server/lib/http/http_rate_limit.py) | Counters IP thuộc RAM process. |
| [server/database/connection.py:17](../../../../../../server/database/connection.py) | SQLite connection riêng per flow/context. |

Các nhận định hiện trạng trên là nghiên cứu mã; experiments bên dưới chưa chạy trong đợt lập kế hoạch. Đối chiếu lại source/line trước code vì workspace có thể tiếp tục thay đổi. Không dùng nghiên cứu để khẳng định lỗ hổng đã tái hiện hoặc tính năng đã đạt.

## Định hướng kỹ thuật và vấn đề cần chốt

Nhánh cần load/HA evidence. Inventory RAM kể cả OTP/đăng ký, shared/partition ownership, notification/fencing/lease và consistency. Đo DB bottleneck/sửa nhỏ trước engine mới; API capability và schema migration có compatibility/rollback.

- Nút nghẽn đo được là DB, threads hay wait máy?
- Mức HA/consistency/cost nào thực cần?

Phương án ngoài định hướng chỉ chọn khi có bằng chứng và decision record. Nếu thay packet/status/schema/interface, planner liệt kê toàn bộ caller app/server/machine/tests trước giao coder. Không mở registry, import feature nội bộ hoặc refactor ngoài scope.

## Yêu cầu bắt buộc của phase

| Mã | Yêu cầu | Trạng thái |
| --- | --- | --- |
| G7.4-R1 | App worker A và máy worker B vẫn đúng command/result. | CHƯA KIỂM |
| G7.4-R2 | Worker crash/lease expiry không duplicate dispatch trái semantics. | CHƯA KIỂM |
| G7.4-R3 | Session/OTP/quota consistency phù hợp requirement. | CHƯA KIỂM |
| G7.4-R4 | Migration/backup/restore kiểm được, không sticky-session-only claim HA. | CHƯA KIỂM |

## Sơ đồ triển khai và dữ liệu bàn giao

Từ nghiên cứu tới nghiệm thu G7.4

```xml
<svg aria-label="Từ nghiên cứu tới nghiệm thu G7.4" role="img" viewbox="0 0 1120 175" xmlns="http://www.w3.org/2000/svg"><title>Từ nghiên cứu tới nghiệm thu G7.4</title><rect fill="#e4f3f0" height="100" rx="8" stroke="#218777" width="230" x="20" y="20"></rect><text fill="#254154" font-size="17" font-weight="600" text-anchor="middle" x="135" y="54">Nghiên cứu / spec</text><text fill="#476474" font-size="13" text-anchor="middle" x="135" y="79.0">Nguồn + assumptions +</text><text fill="#476474" font-size="13" text-anchor="middle" x="135" y="96.0">requirements</text><path d="M250 65L289 65" fill="none" stroke="#527184" stroke-width="2"></path><path d="M289 65l-7 -5v10z" fill="#527184"></path><rect fill="#e4f3f0" height="100" rx="8" stroke="#218777" width="230" x="295" y="20"></rect><text fill="#254154" font-size="17" font-weight="600" text-anchor="middle" x="410" y="54">Test / design review</text><text fill="#476474" font-size="13" text-anchor="middle" x="410" y="87">Scenario + expected outcome</text><path d="M525 65L564 65" fill="none" stroke="#527184" stroke-width="2"></path><path d="M564 65l-7 -5v10z" fill="#527184"></path><rect fill="#e4f3f0" height="100" rx="8" stroke="#218777" width="230" x="570" y="20"></rect><text fill="#254154" font-size="17" font-weight="600" text-anchor="middle" x="685" y="54">Patch / đo kiểm</text><text fill="#476474" font-size="13" text-anchor="middle" x="685" y="87">Diff + raw logs + sample data</text><path d="M800 65L839 65" fill="none" stroke="#527184" stroke-width="2"></path><path d="M839 65l-7 -5v10z" fill="#527184"></path><rect fill="#e4f3f0" height="100" rx="8" stroke="#218777" width="230" x="845" y="20"></rect><text fill="#254154" font-size="17" font-weight="600" text-anchor="middle" x="960" y="54">Review / lead gate</text><text fill="#476474" font-size="13" text-anchor="middle" x="960" y="79.0">Findings + acceptance + next</text><text fill="#476474" font-size="13" text-anchor="middle" x="960" y="96.0">inputs</text></svg>
```

Sơ đồ quy trình team đề xuất. Dữ liệu qua các khối là hiện vật bàn giao, không credential/payload sản phẩm.

Luồng dữ liệu sản phẩm và nhánh timeout xem [mô hình dữ liệu/command](../../data-model.md); biên thành phần xem [kiến trúc](../../architecture.md). Các sơ đồ kỹ thuật tương ứng nằm trong [chuyên đề nguồn](../../expansion.md).

## Sơ đồ khối hoạt động và dữ liệu của phase con

Mô hình triển khai cần kiểm — G7.4

```xml
<svg aria-label="Mô hình triển khai cần kiểm — G7.4" role="img" viewbox="0 0 1120 175" xmlns="http://www.w3.org/2000/svg"><title>Mô hình triển khai cần kiểm — G7.4</title><rect fill="#e4f3f0" height="100" rx="8" stroke="#218777" width="230" x="20" y="20"></rect><text fill="#254154" font-size="17" font-weight="600" text-anchor="middle" x="135" y="54">Load / HA evidence</text><text fill="#476474" font-size="13" text-anchor="middle" x="135" y="87">State/DB bottleneck</text><path d="M250 65L289 65" fill="none" stroke="#527184" stroke-width="2"></path><path d="M289 65l-7 -5v10z" fill="#527184"></path><rect fill="#e4f3f0" height="100" rx="8" stroke="#218777" width="230" x="295" y="20"></rect><text fill="#254154" font-size="17" font-weight="600" text-anchor="middle" x="410" y="54">Shared ownership</text><text fill="#476474" font-size="13" text-anchor="middle" x="410" y="87">Lease/fencing/notifications</text><path d="M525 65L564 65" fill="none" stroke="#527184" stroke-width="2"></path><path d="M564 65l-7 -5v10z" fill="#527184"></path><rect fill="#e4f3f0" height="100" rx="8" stroke="#218777" width="230" x="570" y="20"></rect><text fill="#254154" font-size="17" font-weight="600" text-anchor="middle" x="685" y="54">Cross-worker flow</text><text fill="#476474" font-size="13" text-anchor="middle" x="685" y="87">App A, máy B, crash</text><path d="M800 65L839 65" fill="none" stroke="#527184" stroke-width="2"></path><path d="M839 65l-7 -5v10z" fill="#527184"></path><rect fill="#e4f3f0" height="100" rx="8" stroke="#218777" width="230" x="845" y="20"></rect><text fill="#254154" font-size="17" font-weight="600" text-anchor="middle" x="960" y="54">Version/migration</text><text fill="#476474" font-size="13" text-anchor="middle" x="960" y="87">Consistency/rollback evidence</text></svg>
```

Sơ đồ định hướng cho phase con; không phải bằng chứng feature đã chạy. Dữ liệu ghi tên trường/hiện vật, không giá trị credential. Nhánh lỗi và acceptance nằm trong requirements và test matrix.

## Việc cần làm theo thứ tự

Tester chuẩn bị phép kiểm và tái hiện trước sửa khi là bug; coder nhận spec/test rồi viết patch; không sửa test của tester để làm pass. Task dưới đây là phần việc của phase con, không là phase lớn độc lập.

<a id="E05"></a>

E05

### Nhiều worker và HA

Điều kiện vào
:   Đơn process không đủ theo số đo hoặc HA requirement; state shared design đã có.

Bước thực hiện
:   1. Inventory RAM transport/heartbeat/limiter/OTP/register; externalize hoặc partition có owner.
    2. Notification/single consumer/fencing/lease/shared quota consistency.
    3. App worker A, poll/result B, worker crash/restart/duplicate dispatch.
    4. Chốt framework/broker/DB từ requirement và cost, không chọn trước.

File / phạm vi
:   Runtime/config/stores/transport/auth/OTP, toàn suite.

Xong khi / phép kiểm
:   Không split-brain lệnh/kết quả/session/OTP/quota, topology rollback rõ.

Nhánh lỗi / cần giữ
:   Sticky session không tự chứng minh HA khi worker chết.

Đầu ra
:   HA decision/migration plan riêng.

Đề xuất · Chưa triển khai

<a id="E06"></a>

E06

### Database và version API

Điều kiện vào
:   DB-stage/lock bottleneck hoặc feature/API requirement thật.

Bước thực hiện
:   1. Đo query/index/transaction, sửa nhỏ trước engine mới.
    2. Migration backup/restore, forward/backward compatibility và FK/transaction semantics.
    3. API version/capability app/máy cũ khi packet/status thay.
    4. Data migration/rollback trên giả lập đại diện, retention theo vận hành.

File / phạm vi
:   Database/caller/schema/contract tests theo decision.

Xong khi / phép kiểm
:   Quyền/packet invariants giữ; rollback limitations ghi rõ và đã thử.

Nhánh lỗi / cần giữ
:   Không PostgreSQL/Redis chỉ vì dài hạn.

Đầu ra
:   DB/API decision và kế hoạch độc lập.

Đề xuất · Chưa triển khai

## Phân công và hợp đồng bàn giao

| Vai | Công việc tại phase này | Hiện vật bắt buộc |
| --- | --- | --- |
| Lead | Kiểm đầu vào G6.4, khóa scope, giao và đối chiếu nghiệm thu. | Decision mở/đóng gate, findings còn mở, phase tiếp có inputs. |
| Planner | Giải nghiên cứu/câu hỏi tại phần định hướng; map E05, E06 và callers. | Spec/ADR: source→decision→requirements→files→tests. |
| Tester | Thực hiện scenarios ở matrix, test tái hiện/hồi quy và samples cần thiết. | Test source + input/expected + lệnh/output/exit + môi trường/giới hạn. |
| Coder | Triển khai đúng yêu cầu, chỉ ghi sản phẩm của task được giao. | Diff/file/caller + CODE_STYLE checklist + lệnh tự kiểm. |
| Reviewer | Sau patch/output: kiểm requirements, scope, contract, concurrency/rollback theo diff. | Finding có trigger/source/consequence + trạng thái xử lý. |
| Cybersecurity | Rà biên tin cậy/secret/resource/identity phù hợp yêu cầu phase. | Security requirements/negative evidence/residual risks, không claim exploit chưa chạy. |

## Phép kiểm, yêu cầu bằng chứng và cổng phase con

| Tình huống | Cách kiểm | Kết quả cần thấy |
| --- | --- | --- |
| Worker split/crash/restart | Prototype shared state | Không mất/misroute command/result/OTP |
| DB/API migration | Dữ liệu giả đại diện | FK/quyền/packet invariants + rollback limits rõ |

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
