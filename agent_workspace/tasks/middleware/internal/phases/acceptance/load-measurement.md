> Hồ sơ nội bộ cho agent. Chuyển từ tài liệu HTML ngày 06/10/2026; nội dung và bằng chứng cũ được giữ, chưa kiểm lại sản phẩm. Sơ đồ gốc giữ dưới dạng mã SVG trong khối XML.

[G5 · Nghiệm thu tích hợp, lỗi và tải](index.md) / PHASE CON

# G5.3 · Đo tải, số liệu stages và cảnh báo

Ngưỡng capacity/alert chưa có dữ liệu nếu chỉ chọn theo cảm giác.

Nghiên cứu + yêu cầu + kế hoạch triển khai cả team

## Nhiệm vụ phase con

Ngưỡng capacity/alert chưa có dữ liệu nếu chỉ chọn theo cảm giác.

| Thuộc phase lớn | Điều kiện vào | Task nguồn | Trạng thái |
| --- | --- | --- | --- |
| [G5 · Nghiệm thu tích hợp, lỗi và tải](index.md) | Contract/schema/quyết định và evidence của G5.2 | V02, O04 | CHƯA THỰC HIỆN |

## Nghiên cứu chi tiết và thông tin đã biết

| Nguồn trong repo | Hiện trạng được đọc từ mã |
| --- | --- |
| [server/config/config.py:5](../../../../../../server/config/config.py) | Budgets hiện có liên hệ với TTL/poll/command. |
| [app/flutter_app/lib/core/server_client.dart:111](../../../../../../app/flutter_app/lib/core/server_client.dart) | Timeout client giới hạn tổng request. |

Các nhận định hiện trạng trên là nghiên cứu mã; experiments bên dưới chưa chạy trong đợt lập kế hoạch. Đối chiếu lại source/line trước code vì workspace có thể tiếp tục thay đổi. Không dùng nghiên cứu để khẳng định lỗ hổng đã tái hiện hoặc tính năng đã đạt.

## Định hướng kỹ thuật và vấn đề cần chốt

Workload khởi tạo G0.4 mở rộng ở G3, phase này đo candidate cuối cùng với warm-up/sample count/error rate/raw logs. Reviewer chỉ tối ưu sau giả thuyết đo được.

- Tải mục tiêu thật khác harness ở điểm nào?
- Ngưỡng nào chỉ áp môi trường dev?

Phương án ngoài định hướng chỉ chọn khi có bằng chứng và decision record. Nếu thay packet/status/schema/interface, planner liệt kê toàn bộ caller app/server/machine/tests trước giao coder. Không mở registry, import feature nội bộ hoặc refactor ngoài scope.

## Yêu cầu bắt buộc của phase

| Mã | Yêu cầu | Trạng thái |
| --- | --- | --- |
| G5.3-R1 | Before/after cùng profile/hardware/config/seed. | CHƯA KIỂM |
| G5.3-R2 | p50/p95 có sample count và lỗi, không cộng p95 stages. | CHƯA KIỂM |
| G5.3-R3 | Closed-loop/arrival-rate model và bias ghi rõ. | CHƯA KIỂM |
| G5.3-R4 | Metric/alert bounded labels và threshold nguồn số đo. | CHƯA KIỂM |

## Sơ đồ triển khai và dữ liệu bàn giao

Từ nghiên cứu tới nghiệm thu G5.3

```xml
<svg aria-label="Từ nghiên cứu tới nghiệm thu G5.3" role="img" viewbox="0 0 1120 175" xmlns="http://www.w3.org/2000/svg"><title>Từ nghiên cứu tới nghiệm thu G5.3</title><rect fill="#e4f3f0" height="100" rx="8" stroke="#218777" width="230" x="20" y="20"></rect><text fill="#254154" font-size="17" font-weight="600" text-anchor="middle" x="135" y="54">Nghiên cứu / spec</text><text fill="#476474" font-size="13" text-anchor="middle" x="135" y="79.0">Nguồn + assumptions +</text><text fill="#476474" font-size="13" text-anchor="middle" x="135" y="96.0">requirements</text><path d="M250 65L289 65" fill="none" stroke="#527184" stroke-width="2"></path><path d="M289 65l-7 -5v10z" fill="#527184"></path><rect fill="#e4f3f0" height="100" rx="8" stroke="#218777" width="230" x="295" y="20"></rect><text fill="#254154" font-size="17" font-weight="600" text-anchor="middle" x="410" y="54">Test / design review</text><text fill="#476474" font-size="13" text-anchor="middle" x="410" y="87">Scenario + expected outcome</text><path d="M525 65L564 65" fill="none" stroke="#527184" stroke-width="2"></path><path d="M564 65l-7 -5v10z" fill="#527184"></path><rect fill="#e4f3f0" height="100" rx="8" stroke="#218777" width="230" x="570" y="20"></rect><text fill="#254154" font-size="17" font-weight="600" text-anchor="middle" x="685" y="54">Patch / đo kiểm</text><text fill="#476474" font-size="13" text-anchor="middle" x="685" y="87">Diff + raw logs + sample data</text><path d="M800 65L839 65" fill="none" stroke="#527184" stroke-width="2"></path><path d="M839 65l-7 -5v10z" fill="#527184"></path><rect fill="#e4f3f0" height="100" rx="8" stroke="#218777" width="230" x="845" y="20"></rect><text fill="#254154" font-size="17" font-weight="600" text-anchor="middle" x="960" y="54">Review / lead gate</text><text fill="#476474" font-size="13" text-anchor="middle" x="960" y="79.0">Findings + acceptance + next</text><text fill="#476474" font-size="13" text-anchor="middle" x="960" y="96.0">inputs</text></svg>
```

Sơ đồ quy trình team đề xuất. Dữ liệu qua các khối là hiện vật bàn giao, không credential/payload sản phẩm.

Luồng dữ liệu sản phẩm và nhánh timeout xem [mô hình dữ liệu/command](../../data-model.md); biên thành phần xem [kiến trúc](../../architecture.md). Các sơ đồ kỹ thuật tương ứng nằm trong [chuyên đề nguồn](../../verification.md).

## Sơ đồ khối hoạt động và dữ liệu của phase con

Mô hình triển khai cần kiểm — G5.3

```xml
<svg aria-label="Mô hình triển khai cần kiểm — G5.3" role="img" viewbox="0 0 1120 175" xmlns="http://www.w3.org/2000/svg"><title>Mô hình triển khai cần kiểm — G5.3</title><rect fill="#e4f3f0" height="100" rx="8" stroke="#218777" width="230" x="20" y="20"></rect><text fill="#254154" font-size="17" font-weight="600" text-anchor="middle" x="135" y="54">Load config</text><text fill="#476474" font-size="13" text-anchor="middle" x="135" y="87">Seed/count/profile/version</text><path d="M250 65L289 65" fill="none" stroke="#527184" stroke-width="2"></path><path d="M289 65l-7 -5v10z" fill="#527184"></path><rect fill="#e4f3f0" height="100" rx="8" stroke="#218777" width="230" x="295" y="20"></rect><text fill="#254154" font-size="17" font-weight="600" text-anchor="middle" x="410" y="54">Harness + stages</text><text fill="#476474" font-size="13" text-anchor="middle" x="410" y="87">Candidate ổn định</text><path d="M525 65L564 65" fill="none" stroke="#527184" stroke-width="2"></path><path d="M564 65l-7 -5v10z" fill="#527184"></path><rect fill="#e4f3f0" height="100" rx="8" stroke="#218777" width="230" x="570" y="20"></rect><text fill="#254154" font-size="17" font-weight="600" text-anchor="middle" x="685" y="54">Raw timing/resource</text><text fill="#476474" font-size="13" text-anchor="middle" x="685" y="87">Samples/p50/p95/errors</text><path d="M800 65L839 65" fill="none" stroke="#527184" stroke-width="2"></path><path d="M839 65l-7 -5v10z" fill="#527184"></path><rect fill="#e4f3f0" height="100" rx="8" stroke="#218777" width="230" x="845" y="20"></rect><text fill="#254154" font-size="17" font-weight="600" text-anchor="middle" x="960" y="54">Threshold decision</text><text fill="#476474" font-size="13" text-anchor="middle" x="960" y="79.0">Bounds/alerts theo</text><text fill="#476474" font-size="13" text-anchor="middle" x="960" y="96.0">environment</text></svg>
```

Sơ đồ định hướng cho phase con; không phải bằng chứng feature đã chạy. Dữ liệu ghi tên trường/hiện vật, không giá trị credential. Nhánh lỗi và acceptance nằm trong requirements và test matrix.

## Việc cần làm theo thứ tự

Tester chuẩn bị phép kiểm và tái hiện trước sửa khi là bug; coder nhận spec/test rồi viết patch; không sửa test của tester để làm pass. Task dưới đây là phần việc của phase con, không là phase lớn độc lập.

<a id="V02"></a>

V02

### Công cụ tải tái lập được

Điều kiện vào
:   Nghiệm thu G5: G3/G4 đạt trong scope; harness gốc B04 và các lượt candidate G3 là inputs. Dựng harness/đo ban đầu không chờ G5.

Bước thực hiện
:   1. Server DB tạm/cổng động, máy mô phỏng execution delay điều khiển.
    2. Workload public/app short/app wait/poll/heartbeat/result; nêu closed-loop hay arrival-rate.
    3. Warm-up rồi tăng tải/burst/soak; chốt profile/số mẫu trước đo.
    4. Raw mỗi sample: flow/stage/duration/status/outcome; resource snapshots; tổng hợp p50/p95/lỗi.

File / phạm vi
:   tests/tools hoặc tests/performance dự kiến; artifacts dưới tests/.

Xong khi / phép kiểm
:   Before/after cùng điều kiện, raw tái tổng hợp, percentile có số mẫu.

Nhánh lỗi / cần giữ
:   Máy mô phỏng nhanh không đại diện máy thật.

Đầu ra
:   Profiles/JSONL/HTML báo cáo đo.

Đề xuất · Chưa triển khai

<a id="O04"></a>

O04

### Metric catalogue và cảnh báo

Điều kiện vào
:   V02/G3.

Bước thực hiện
:   1. Gauges pending/queue/active/thread/RSS và counters reject/error/disconnect.
    2. Threshold dựa tải/deadline đã đo, gắn environment.
    3. Phân biệt offline máy, overload server và DB busy qua stage/outcome.
    4. Chưa dashboard live thì xuất HTML từ samples, không giả số.

File / phạm vi
:   Report tools tests/; operations/observability HTML.

Xong khi / phép kiểm
:   Mỗi alert có runbook/test tái hiện, labels cardinality bounded.

Nhánh lỗi / cần giữ
:   Không SLA khi chưa có môi trường/load thật.

Đầu ra
:   Metric/alert→runbook mapping.

Đề xuất · Chưa triển khai

## Phân công và hợp đồng bàn giao

| Vai | Công việc tại phase này | Hiện vật bắt buộc |
| --- | --- | --- |
| Lead | Kiểm đầu vào G5.2, khóa scope, giao và đối chiếu nghiệm thu. | Decision mở/đóng gate, findings còn mở, phase tiếp có inputs. |
| Planner | Giải nghiên cứu/câu hỏi tại phần định hướng; map V02, O04 và callers. | Spec/ADR: source→decision→requirements→files→tests. |
| Tester | Thực hiện scenarios ở matrix, test tái hiện/hồi quy và samples cần thiết. | Test source + input/expected + lệnh/output/exit + môi trường/giới hạn. |
| Coder | Triển khai đúng yêu cầu, chỉ ghi sản phẩm của task được giao. | Diff/file/caller + CODE_STYLE checklist + lệnh tự kiểm. |
| Reviewer | Sau patch/output: kiểm requirements, scope, contract, concurrency/rollback theo diff. | Finding có trigger/source/consequence + trạng thái xử lý. |
| Cybersecurity | Rà biên tin cậy/secret/resource/identity phù hợp yêu cầu phase. | Security requirements/negative evidence/residual risks, không claim exploit chưa chạy. |

## Phép kiểm, yêu cầu bằng chứng và cổng phase con

| Tình huống | Cách kiểm | Kết quả cần thấy |
| --- | --- | --- |
| Burst/sustained/soak/recovery | Version/profile cố định | Bounded resources + completion/timeout rates |
| Log on/off | Cùng workload | Overhead quan sát được, không giả timings |

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
