> Hồ sơ nội bộ cho agent. Chuyển từ tài liệu HTML ngày 06/10/2026; nội dung và bằng chứng cũ được giữ, chưa kiểm lại sản phẩm. Sơ đồ gốc giữ dưới dạng mã SVG trong khối XML.

[G6 · Vận hành, rollout và phục hồi](index.md) / PHASE CON

# G6.4 · Topology, TLS và sổ vận hành

HTTP rõ và proxy/trusted headers không thể được coi an toàn chỉ vì có middleware.

Nghiên cứu + yêu cầu + kế hoạch triển khai cả team

## Nhiệm vụ phase con

HTTP rõ và proxy/trusted headers không thể được coi an toàn chỉ vì có middleware.

| Thuộc phase lớn | Điều kiện vào | Task nguồn | Trạng thái |
| --- | --- | --- | --- |
| [G6 · Vận hành, rollout và phục hồi](index.md) | Contract/schema/quyết định và evidence của G6.3 | P04, P05 | CHƯA THỰC HIỆN |

## Nghiên cứu chi tiết và thông tin đã biết

| Nguồn trong repo | Hiện trạng được đọc từ mã |
| --- | --- |
| [server/config/config.py:3](../../../../../../server/config/config.py) | SERVER_HOST hiện 0.0.0.0. |
| [machine/server_connection/machine_server_request.py:18](../../../../../../machine/server_connection/machine_server_request.py) | Máy gọi URL cấu hình qua urllib. |
| [server/lib/http/http_rate_limit.py:18](../../../../../../server/lib/http/http_rate_limit.py) | Limiter hiện dùng IP từ client_address qua handle_routes. |

Các nhận định hiện trạng trên là nghiên cứu mã; experiments bên dưới chưa chạy trong đợt lập kế hoạch. Đối chiếu lại source/line trước code vì workspace có thể tiếp tục thay đổi. Không dùng nghiên cứu để khẳng định lỗ hổng đã tái hiện hoặc tính năng đã đạt.

## Định hướng kỹ thuật và vấn đề cần chốt

Chốt exposure/TLS/trusted proxy theo môi trường; kiểm buffering/long-poll/deadline/trust. Runbook gắn alert→triage→action→verify→rollback, logging retention bounded.

- TLS terminate ở đâu, port nào exposed?
- Ops owner/retention/alert criteria là ai và theo môi trường nào?

Phương án ngoài định hướng chỉ chọn khi có bằng chứng và decision record. Nếu thay packet/status/schema/interface, planner liệt kê toàn bộ caller app/server/machine/tests trước giao coder. Không mở registry, import feature nội bộ hoặc refactor ngoài scope.

## Yêu cầu bắt buộc của phase

| Mã | Yêu cầu | Trạng thái |
| --- | --- | --- |
| G6.4-R1 | Không tin forwarded header nếu chưa trusted proxy. | CHƯA KIỂM |
| G6.4-R2 | Certificate/hostname verification không tắt để test xanh. | CHƯA KIỂM |
| G6.4-R3 | Một worker khi shared RAM chưa thiết kế. | CHƯA KIỂM |
| G6.4-R4 | Chưa topology/device pass thì không claim production-ready. | CHƯA KIỂM |

## Sơ đồ triển khai và dữ liệu bàn giao

Từ nghiên cứu tới nghiệm thu G6.4

```xml
<svg aria-label="Từ nghiên cứu tới nghiệm thu G6.4" role="img" viewbox="0 0 1120 175" xmlns="http://www.w3.org/2000/svg"><title>Từ nghiên cứu tới nghiệm thu G6.4</title><rect fill="#e4f3f0" height="100" rx="8" stroke="#218777" width="230" x="20" y="20"></rect><text fill="#254154" font-size="17" font-weight="600" text-anchor="middle" x="135" y="54">Nghiên cứu / spec</text><text fill="#476474" font-size="13" text-anchor="middle" x="135" y="79.0">Nguồn + assumptions +</text><text fill="#476474" font-size="13" text-anchor="middle" x="135" y="96.0">requirements</text><path d="M250 65L289 65" fill="none" stroke="#527184" stroke-width="2"></path><path d="M289 65l-7 -5v10z" fill="#527184"></path><rect fill="#e4f3f0" height="100" rx="8" stroke="#218777" width="230" x="295" y="20"></rect><text fill="#254154" font-size="17" font-weight="600" text-anchor="middle" x="410" y="54">Test / design review</text><text fill="#476474" font-size="13" text-anchor="middle" x="410" y="87">Scenario + expected outcome</text><path d="M525 65L564 65" fill="none" stroke="#527184" stroke-width="2"></path><path d="M564 65l-7 -5v10z" fill="#527184"></path><rect fill="#e4f3f0" height="100" rx="8" stroke="#218777" width="230" x="570" y="20"></rect><text fill="#254154" font-size="17" font-weight="600" text-anchor="middle" x="685" y="54">Patch / đo kiểm</text><text fill="#476474" font-size="13" text-anchor="middle" x="685" y="87">Diff + raw logs + sample data</text><path d="M800 65L839 65" fill="none" stroke="#527184" stroke-width="2"></path><path d="M839 65l-7 -5v10z" fill="#527184"></path><rect fill="#e4f3f0" height="100" rx="8" stroke="#218777" width="230" x="845" y="20"></rect><text fill="#254154" font-size="17" font-weight="600" text-anchor="middle" x="960" y="54">Review / lead gate</text><text fill="#476474" font-size="13" text-anchor="middle" x="960" y="79.0">Findings + acceptance + next</text><text fill="#476474" font-size="13" text-anchor="middle" x="960" y="96.0">inputs</text></svg>
```

Sơ đồ quy trình team đề xuất. Dữ liệu qua các khối là hiện vật bàn giao, không credential/payload sản phẩm.

Luồng dữ liệu sản phẩm và nhánh timeout xem [mô hình dữ liệu/command](../../data-model.md); biên thành phần xem [kiến trúc](../../architecture.md). Các sơ đồ kỹ thuật tương ứng nằm trong [chuyên đề nguồn](../../operations.md).

## Sơ đồ khối hoạt động và dữ liệu của phase con

Mô hình triển khai cần kiểm — G6.4

```xml
<svg aria-label="Mô hình triển khai cần kiểm — G6.4" role="img" viewbox="0 0 1120 175" xmlns="http://www.w3.org/2000/svg"><title>Mô hình triển khai cần kiểm — G6.4</title><rect fill="#e4f3f0" height="100" rx="8" stroke="#218777" width="230" x="20" y="20"></rect><text fill="#254154" font-size="17" font-weight="600" text-anchor="middle" x="135" y="54">Exposure/topology</text><text fill="#476474" font-size="13" text-anchor="middle" x="135" y="87">Port/TLS/trusted proxy</text><path d="M250 65L289 65" fill="none" stroke="#527184" stroke-width="2"></path><path d="M289 65l-7 -5v10z" fill="#527184"></path><rect fill="#e4f3f0" height="100" rx="8" stroke="#218777" width="230" x="295" y="20"></rect><text fill="#254154" font-size="17" font-weight="600" text-anchor="middle" x="410" y="54">End-to-end flow</text><text fill="#476474" font-size="13" text-anchor="middle" x="410" y="87">Poll/result/body/deadline</text><path d="M525 65L564 65" fill="none" stroke="#527184" stroke-width="2"></path><path d="M564 65l-7 -5v10z" fill="#527184"></path><rect fill="#e4f3f0" height="100" rx="8" stroke="#218777" width="230" x="570" y="20"></rect><text fill="#254154" font-size="17" font-weight="600" text-anchor="middle" x="685" y="54">Alerts + runbook</text><text fill="#476474" font-size="13" text-anchor="middle" x="685" y="87">Triage/action/verify</text><path d="M800 65L839 65" fill="none" stroke="#527184" stroke-width="2"></path><path d="M839 65l-7 -5v10z" fill="#527184"></path><rect fill="#e4f3f0" height="100" rx="8" stroke="#218777" width="230" x="845" y="20"></rect><text fill="#254154" font-size="17" font-weight="600" text-anchor="middle" x="960" y="54">Ops evidence</text><text fill="#476474" font-size="13" text-anchor="middle" x="960" y="87">Target limits và review</text></svg>
```

Sơ đồ định hướng cho phase con; không phải bằng chứng feature đã chạy. Dữ liệu ghi tên trường/hiện vật, không giá trị credential. Nhánh lỗi và acceptance nằm trong requirements và test matrix.

## Việc cần làm theo thứ tự

Tester chuẩn bị phép kiểm và tái hiện trước sửa khi là bug; coder nhận spec/test rồi viết patch; không sửa test của tester để làm pass. Task dưới đây là phần việc của phase con, không là phase lớn độc lập.

<a id="P04"></a>

P04

### Topology mạng và TLS

Điều kiện vào
:   G5 đạt và môi trường/topology cụ thể. Không yêu cầu E01/G7.1 đã hoàn tất. Nếu topology bắt buộc runtime/contract mới, lead ghi blocker, mở quyết định đổi kế hoạch và cập nhật DAG trước triển khai, không tạo phụ thuộc vòng G6→G7→G6.

Bước thực hiện
:   1. Xác định exposed port/interface, TLS termination, trusted proxy.
    2. Proxy buffering/header/body/timeouts/forwarded spoofing và long-poll.
    3. Certificate/hostname validation caller đúng, không tắt verification.
    4. Giữ một worker khi RAM chưa externalize; firewall theo environment.

File / phạm vi
:   Deployment file chưa chốt; caller nếu URL đổi.

Xong khi / phép kiểm
:   End-to-end HTTPS/poll/result tests; không claim production-safe chỉ do middleware.

Nhánh lỗi / cần giữ
:   Python cảnh báo http.server không phù hợp production; proxy không tự chữa runtime.

Đầu ra
:   TLS topology/trust tests/runtime decision.

Đề xuất · Chưa triển khai

<a id="P05"></a>

P05

### Sổ vận hành và đánh giá tiếp

Điều kiện vào
:   O04/P01–P04 scope.

Bước thực hiện
:   1. Owner components, steps triage, error/outcome và artifacts.
    2. Workload/capacity đã kiểm và phần chưa kiểm/risk.
    3. Sự cố mới gắn trigger/root cause/test hồi quy.
    4. Mở nhánh dài hạn theo nhu cầu/số đo, không vì plan có nhánh.

File / phạm vi
:   operations/observability/roadmap HTML + TASK.md.

Xong khi / phép kiểm
:   Người khác đọc runbook phân biệt DB/máy/server và kiểm recovery.

Nhánh lỗi / cần giữ
:   Không credentials thật trong tài liệu.

Đầu ra
:   Operations handbook theo environment.

Đề xuất · Chưa triển khai

## Phân công và hợp đồng bàn giao

| Vai | Công việc tại phase này | Hiện vật bắt buộc |
| --- | --- | --- |
| Lead | Kiểm đầu vào G6.3, khóa scope, giao và đối chiếu nghiệm thu. | Decision mở/đóng gate, findings còn mở, phase tiếp có inputs. |
| Planner | Giải nghiên cứu/câu hỏi tại phần định hướng; map P04, P05 và callers. | Spec/ADR: source→decision→requirements→files→tests. |
| Tester | Thực hiện scenarios ở matrix, test tái hiện/hồi quy và samples cần thiết. | Test source + input/expected + lệnh/output/exit + môi trường/giới hạn. |
| Coder | Triển khai đúng yêu cầu, chỉ ghi sản phẩm của task được giao. | Diff/file/caller + CODE_STYLE checklist + lệnh tự kiểm. |
| Reviewer | Sau patch/output: kiểm requirements, scope, contract, concurrency/rollback theo diff. | Finding có trigger/source/consequence + trạng thái xử lý. |
| Cybersecurity | Rà biên tin cậy/secret/resource/identity phù hợp yêu cầu phase. | Security requirements/negative evidence/residual risks, không claim exploit chưa chạy. |

## Phép kiểm, yêu cầu bằng chứng và cổng phase con

| Tình huống | Cách kiểm | Kết quả cần thấy |
| --- | --- | --- |
| TLS/proxy end-to-end | Target đã chọn | Poll/result/status/trust behavior đúng |
| Overload/DB busy/offline/sink full | Runbook drill | Triage đúng và recovery evidence |

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
