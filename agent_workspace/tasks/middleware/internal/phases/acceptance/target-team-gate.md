> Hồ sơ nội bộ cho agent. Chuyển từ tài liệu HTML ngày 06/10/2026; nội dung và bằng chứng cũ được giữ, chưa kiểm lại sản phẩm. Sơ đồ gốc giữ dưới dạng mã SVG trong khối XML.

[G5 · Nghiệm thu tích hợp, lỗi và tải](index.md) / PHASE CON

# G5.4 · Thiết bị mục tiêu và gate cả team

Simulation pass không chứng minh Windows/Pi/Flutter mạng thật; lời tự nhận agent không là evidence.

Nghiên cứu + yêu cầu + kế hoạch triển khai cả team

## Nhiệm vụ phase con

Simulation pass không chứng minh Windows/Pi/Flutter mạng thật; lời tự nhận agent không là evidence.

| Thuộc phase lớn | Điều kiện vào | Task nguồn | Trạng thái |
| --- | --- | --- | --- |
| [G5 · Nghiệm thu tích hợp, lỗi và tải](index.md) | Contract/schema/quyết định và evidence của G5.3 | V04, V05 | CHƯA THỰC HIỆN |

## Nghiên cứu chi tiết và thông tin đã biết

| Nguồn trong repo | Hiện trạng được đọc từ mã |
| --- | --- |
| [tests/e2e/run_e2e.py:1](../../../../../../tests/e2e/run_e2e.py) | Công cụ E2E của repo có scope thiết bị riêng. |
| [agent_workspace/TEAM.md:1](../../../../../TEAM.md) | Lead đối chiếu diff/output trước mở gate. |

Các nhận định hiện trạng trên là nghiên cứu mã; experiments bên dưới chưa chạy trong đợt lập kế hoạch. Đối chiếu lại source/line trước code vì workspace có thể tiếp tục thay đổi. Không dùng nghiên cứu để khẳng định lỗ hổng đã tái hiện hoặc tính năng đã đạt.

## Định hướng kỹ thuật và vấn đề cần chốt

Kiểm target chỉ theo scope/môi trường đã có; chưa có thì chưa kiểm, ghi impact. Reviewer/security kết luận trên diff và logs; lead ký acceptance từng requirement.

- Production requirements nào bắt buộc device pass trước G6?
- Phần chưa kiểm nào được chấp nhận cho rollout môi trường hạn chế?

Phương án ngoài định hướng chỉ chọn khi có bằng chứng và decision record. Nếu thay packet/status/schema/interface, planner liệt kê toàn bộ caller app/server/machine/tests trước giao coder. Không mở registry, import feature nội bộ hoặc refactor ngoài scope.

## Yêu cầu bắt buộc của phase

| Mã | Yêu cầu | Trạng thái |
| --- | --- | --- |
| G5.4-R1 | Targets có OS/runtime/network profile và dữ liệu test. | CHƯA KIỂM |
| G5.4-R2 | Bằng chứng mới cho scope chạy, chưa kiểm tách khỏi pass. | CHƯA KIỂM |
| G5.4-R3 | Findings có trigger/file:dòng/consequence và trạng thái sửa. | CHƯA KIỂM |
| G5.4-R4 | Không gate nếu còn blocker contract/quyền/resource/restart. | CHƯA KIỂM |

## Sơ đồ triển khai và dữ liệu bàn giao

Từ nghiên cứu tới nghiệm thu G5.4

```xml
<svg aria-label="Từ nghiên cứu tới nghiệm thu G5.4" role="img" viewbox="0 0 1120 175" xmlns="http://www.w3.org/2000/svg"><title>Từ nghiên cứu tới nghiệm thu G5.4</title><rect fill="#e4f3f0" height="100" rx="8" stroke="#218777" width="230" x="20" y="20"></rect><text fill="#254154" font-size="17" font-weight="600" text-anchor="middle" x="135" y="54">Nghiên cứu / spec</text><text fill="#476474" font-size="13" text-anchor="middle" x="135" y="79.0">Nguồn + assumptions +</text><text fill="#476474" font-size="13" text-anchor="middle" x="135" y="96.0">requirements</text><path d="M250 65L289 65" fill="none" stroke="#527184" stroke-width="2"></path><path d="M289 65l-7 -5v10z" fill="#527184"></path><rect fill="#e4f3f0" height="100" rx="8" stroke="#218777" width="230" x="295" y="20"></rect><text fill="#254154" font-size="17" font-weight="600" text-anchor="middle" x="410" y="54">Test / design review</text><text fill="#476474" font-size="13" text-anchor="middle" x="410" y="87">Scenario + expected outcome</text><path d="M525 65L564 65" fill="none" stroke="#527184" stroke-width="2"></path><path d="M564 65l-7 -5v10z" fill="#527184"></path><rect fill="#e4f3f0" height="100" rx="8" stroke="#218777" width="230" x="570" y="20"></rect><text fill="#254154" font-size="17" font-weight="600" text-anchor="middle" x="685" y="54">Patch / đo kiểm</text><text fill="#476474" font-size="13" text-anchor="middle" x="685" y="87">Diff + raw logs + sample data</text><path d="M800 65L839 65" fill="none" stroke="#527184" stroke-width="2"></path><path d="M839 65l-7 -5v10z" fill="#527184"></path><rect fill="#e4f3f0" height="100" rx="8" stroke="#218777" width="230" x="845" y="20"></rect><text fill="#254154" font-size="17" font-weight="600" text-anchor="middle" x="960" y="54">Review / lead gate</text><text fill="#476474" font-size="13" text-anchor="middle" x="960" y="79.0">Findings + acceptance + next</text><text fill="#476474" font-size="13" text-anchor="middle" x="960" y="96.0">inputs</text></svg>
```

Sơ đồ quy trình team đề xuất. Dữ liệu qua các khối là hiện vật bàn giao, không credential/payload sản phẩm.

Luồng dữ liệu sản phẩm và nhánh timeout xem [mô hình dữ liệu/command](../../data-model.md); biên thành phần xem [kiến trúc](../../architecture.md). Các sơ đồ kỹ thuật tương ứng nằm trong [chuyên đề nguồn](../../verification.md).

## Sơ đồ khối hoạt động và dữ liệu của phase con

Mô hình triển khai cần kiểm — G5.4

```xml
<svg aria-label="Mô hình triển khai cần kiểm — G5.4" role="img" viewbox="0 0 1120 175" xmlns="http://www.w3.org/2000/svg"><title>Mô hình triển khai cần kiểm — G5.4</title><rect fill="#e4f3f0" height="100" rx="8" stroke="#218777" width="230" x="20" y="20"></rect><text fill="#254154" font-size="17" font-weight="600" text-anchor="middle" x="135" y="54">Target scope</text><text fill="#476474" font-size="13" text-anchor="middle" x="135" y="87">OS/CPU/NAT/TLS</text><path d="M250 65L289 65" fill="none" stroke="#527184" stroke-width="2"></path><path d="M289 65l-7 -5v10z" fill="#527184"></path><rect fill="#e4f3f0" height="100" rx="8" stroke="#218777" width="230" x="295" y="20"></rect><text fill="#254154" font-size="17" font-weight="600" text-anchor="middle" x="410" y="54">Device/harness runs</text><text fill="#476474" font-size="13" text-anchor="middle" x="410" y="87">Output thực hoặc chưa kiểm</text><path d="M525 65L564 65" fill="none" stroke="#527184" stroke-width="2"></path><path d="M564 65l-7 -5v10z" fill="#527184"></path><rect fill="#e4f3f0" height="100" rx="8" stroke="#218777" width="230" x="570" y="20"></rect><text fill="#254154" font-size="17" font-weight="600" text-anchor="middle" x="685" y="54">Reviewer/security</text><text fill="#476474" font-size="13" text-anchor="middle" x="685" y="87">Finding + evidence + residual</text><path d="M800 65L839 65" fill="none" stroke="#527184" stroke-width="2"></path><path d="M839 65l-7 -5v10z" fill="#527184"></path><rect fill="#e4f3f0" height="100" rx="8" stroke="#218777" width="230" x="845" y="20"></rect><text fill="#254154" font-size="17" font-weight="600" text-anchor="middle" x="960" y="54">Lead acceptance</text><text fill="#476474" font-size="13" text-anchor="middle" x="960" y="87">Gate/blocked/limited scope</text></svg>
```

Sơ đồ định hướng cho phase con; không phải bằng chứng feature đã chạy. Dữ liệu ghi tên trường/hiện vật, không giá trị credential. Nhánh lỗi và acceptance nằm trong requirements và test matrix.

## Việc cần làm theo thứ tự

Tester chuẩn bị phép kiểm và tái hiện trước sửa khi là bug; coder nhận spec/test rồi viết patch; không sửa test của tester để làm pass. Task dưới đây là phần việc của phase con, không là phase lớn độc lập.

<a id="V04"></a>

V04

### Thiết bị và hệ điều hành mục tiêu

Điều kiện vào
:   Simulation G5 đạt và scope môi trường cụ thể.

Bước thực hiện
:   1. Ghi Pi/Windows/Flutter/runtime/network/NAT/TLS.
    2. Kiểm drain/reset Windows, poll máy 10s, app 25s trên target.
    3. E2E menu/kho/share/lỗi mạng chỉ khi scope được yêu cầu, dữ liệu test.
    4. Đối chiếu dev/target, đổi bounds bằng evidence.

File / phạm vi
:   tests/e2e hiện có; fixtures riêng.

Xong khi / phép kiểm
:   Output thật cho scope chạy; chưa có device→CHƯA KIỂM kèm tác động.

Nhánh lỗi / cần giữ
:   Plan không mặc định authorize điều khiển hardware thật.

Đầu ra
:   Device report/config profile.

Đề xuất · Chưa triển khai

<a id="V05"></a>

V05

### Reviewer và nghiệm thu

Điều kiện vào
:   V01–V04 trong scope.

Bước thực hiện
:   1. Coder diff/caller/lệnh/exit; tester samples/time/errors/limits.
    2. Reviewer finding file:dòng/trigger/hậu quả; security review nếu auth/network/secrets.
    3. Lead đối chiếu raw output, acceptance pass/fail/chưa kiểm.
    4. Không bottleneck rõ→chưa cần tối ưu, không sửa để khớp dự đoán.

File / phạm vi
:   TASK.md nội bộ + HTML chuyên đề.

Xong khi / phép kiểm
:   Claim đạt có chứng cứ, lỗi mở có scope/decision.

Nhánh lỗi / cần giữ
:   Không mở chặng phụ thuộc khi gate chưa phân tích giới hạn.

Đầu ra
:   Acceptance record và quyết định tiếp/rollback.

Đề xuất · Chưa triển khai

## Phân công và hợp đồng bàn giao

| Vai | Công việc tại phase này | Hiện vật bắt buộc |
| --- | --- | --- |
| Lead | Kiểm đầu vào G5.3, khóa scope, giao và đối chiếu nghiệm thu. | Decision mở/đóng gate, findings còn mở, phase tiếp có inputs. |
| Planner | Giải nghiên cứu/câu hỏi tại phần định hướng; map V04, V05 và callers. | Spec/ADR: source→decision→requirements→files→tests. |
| Tester | Thực hiện scenarios ở matrix, test tái hiện/hồi quy và samples cần thiết. | Test source + input/expected + lệnh/output/exit + môi trường/giới hạn. |
| Coder | Triển khai đúng yêu cầu, chỉ ghi sản phẩm của task được giao. | Diff/file/caller + CODE_STYLE checklist + lệnh tự kiểm. |
| Reviewer | Sau patch/output: kiểm requirements, scope, contract, concurrency/rollback theo diff. | Finding có trigger/source/consequence + trạng thái xử lý. |
| Cybersecurity | Rà biên tin cậy/secret/resource/identity phù hợp yêu cầu phase. | Security requirements/negative evidence/residual risks, không claim exploit chưa chạy. |

## Phép kiểm, yêu cầu bằng chứng và cổng phase con

| Tình huống | Cách kiểm | Kết quả cần thấy |
| --- | --- | --- |
| Target long-poll/body/drain | Scope được xác định | Output thật hoặc CHƯA KIỂM có tác động |
| Evidence review | Đối chiếu raw logs/diff | Lead decision không dựa lời agent |

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
