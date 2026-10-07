> Hồ sơ nội bộ cho agent. Chuyển từ tài liệu HTML ngày 06/10/2026; nội dung và bằng chứng cũ được giữ, chưa kiểm lại sản phẩm. Sơ đồ gốc giữ dưới dạng mã SVG trong khối XML.

KẾ HOẠCH PHÁT TRIỂN / 05.10.2026

# Lộ trình dài hạn và cổng nghiệm thu

Thứ tự theo phụ thuộc và đầu ra kiểm được; đặc tả mỗi tác vụ ở tài liệu chuyên đề.

Tài liệu thiết kế và kế hoạch · Offline / In được

## Kế hoạch triển khai hai cấp của team AI

Mỗi phase lớn là một giai đoạn cả team AI. Mỗi phase lớn chứa bốn phase con; từng phase con có nghiên cứu, thông tin/giả thuyết, định hướng, việc cần làm, requirements, vai/bàn giao, tests và gate. Task/bước nằm trong phase con.

| Phase lớn | Mục tiêu / gate | Phase con |
| --- | --- | --- |
| [G0 · Nền nghiên cứu và kiểm chứng](phases/foundation/index.md) | Ma trận hợp đồng có nguồn; fixture hiện tại chạy được; rủi ro có test tái hiện; môi trường và dữ liệu đo được lưu. | [G0.1 · Nghiên cứu hiện trạng và hợp đồng](phases/foundation/contract-research.md) [G0.2 · Khôi phục fixture và bộ hồi quy](phases/foundation/fixture-repair.md) [G0.3 · Tái hiện rủi ro trước sửa](phases/foundation/risk-scenarios.md) [G0.4 · Đo môi trường và dựng công cụ nền](phases/foundation/environment-baseline.md) |
| [G1 · Vòng đời request và quan sát an toàn](phases/lifecycle/index.md) | Context/response/error/dispatch/log contract được kiểm; không packet/schema đổi ngầm. | [G1.1 · Context và dữ liệu request](phases/lifecycle/context-design.md) [G1.2 · Response state và biên lỗi](phases/lifecycle/response-boundary.md) [G1.3 · Dispatch và liên hệ request–command](phases/lifecycle/dispatch-correlation.md) [G1.4 · Event schema và kiểm mọi log sink](phases/lifecycle/safe-observability.md) |
| [G2 · Biên HTTP, body và tương thích client](phases/http-boundary/index.md) | Framing/read/deadline/header suite đạt; mọi contract change có caller tests đồng bộ. | [G2.1 · Nghiên cứu parser và chính sách framing](phases/http-boundary/framing-policy.md) [G2.2 · Đọc body đủ byte và parse một lần](phases/http-boundary/body-integrity.md) [G2.3 · Deadline đọc và early reject](phases/http-boundary/read-deadline.md) [G2.4 · Media type, lỗi và tương thích caller](phases/http-boundary/client-compatibility.md) |
| [G3 · Sức chứa và tiến triển lệnh máy](phases/capacity/index.md) | Không deadlock/starvation trong workload đã kiểm; resource phục hồi; budgets và giới hạn protection rõ. | [G3.1 · Giới hạn ingress trước tạo thread](phases/capacity/ingress-bound.md) [G3.2 · Phân nhóm công việc và headroom](phases/capacity/workload-lanes.md) [G3.3 · Queue, waiter và cleanup](phases/capacity/queue-invariants.md) [G3.4 · Budgets, lỗi đồng thời và phục hồi](phases/capacity/budgets-recovery.md) |
| [G4 · Danh tính, quyền và chính sách bảo vệ](phases/identity/index.md) | Auth/TTL/logout/role/race/limiter/log tests đạt; contract privacy/device changes được tách rõ. | [G4.1 · Route policy và thứ tự xác thực](phases/identity/route-policy.md) [G4.2 · Phiên, thu hồi và lựa chọn gom auth](phases/identity/session-revocation.md) [G4.3 · Quyền, transaction và privacy trạng thái](phases/identity/authorization-transaction.md) [G4.4 · Limiter, NAT và threat model](phases/identity/limiter-threat-model.md) |
| [G5 · Nghiệm thu tích hợp, lỗi và tải](phases/acceptance/index.md) | Evidence package đầy đủ; review/security findings chặn đã xử lý; phần chưa kiểm có tác động và quyết định. | [G5.1 · Hợp đồng liên thành phần và hồi quy](phases/acceptance/contract-regression.md) [G5.2 · Fault injection và bất biến đồng thời](phases/acceptance/fault-concurrency.md) [G5.3 · Đo tải, số liệu stages và cảnh báo](phases/acceptance/load-measurement.md) [G5.4 · Thiết bị mục tiêu và gate cả team](phases/acceptance/target-team-gate.md) |
| [G6 · Vận hành, rollout và phục hồi](phases/operations/index.md) | Boot/stop/recovery/rollback rehearsals có evidence; exposure/TLS và residual risks đã được chốt. | [G6.1 · Cấu hình, boot và profile vận hành](phases/operations/configuration-validation.md) [G6.2 · Dừng server, restart và kết quả chưa chắc chắn](phases/operations/shutdown-restart.md) [G6.3 · Candidate, rollout và quay lui](phases/operations/rollout-rollback.md) [G6.4 · Topology, TLS và sổ vận hành](phases/operations/network-runbooks.md) |
| [G7 · Mở rộng dài hạn theo bằng chứng](phases/evolution/index.md) | Mỗi nhánh kích hoạt có ADR, contract/migration, tests/fault/load và rollback; không yêu cầu mọi nhánh hoàn tất. | [G7.1 · Runtime HTTP và mạng triển khai](phases/evolution/runtime-network.md) [G7.2 · Vòng đời credential thiết bị](phases/evolution/device-credentials.md) [G7.3 · Command identity, idempotency và bền vững](phases/evolution/command-durability.md) [G7.4 · Scale-out, database và version API](phases/evolution/shared-state-evolution.md) |

8 phase lớn · 32 phase con · 46 task. Trang chuyên đề cũ là tài liệu nghiên cứu tham chiếu; đặc tả thực thi ở phases/. G7 là nhánh có điều kiện, không buộc thực hiện mọi nhánh.

## Ánh xạ cổng nghiệm thu với nghiên cứu chuyên đề

Hiện trạngĐề xuấtKho dữ liệuLỗi / điều kiện cần chốt

Lộ trình theo cổng nghiệm thu

```xml
<svg aria-label="Lộ trình theo cổng nghiệm thu" role="img" viewbox="0 0 1080 365" xmlns="http://www.w3.org/2000/svg"><title>Lộ trình theo cổng nghiệm thu</title><defs><marker id="arrow-26197" markerheight="7" markerwidth="7" orient="auto" refx="9" refy="5" viewbox="0 0 10 10"><path d="M0 0L10 5L0 10z" fill="#667b8d"></path></marker></defs><path d="M270 80L420 80" fill="none" marker-end="url(#arrow-26197)" stroke="#667b8d" stroke-width="2"></path><rect fill="white" height="22" rx="3" width="54.4" x="317.8" y="58.0"></rect><text fill="#4b6072" font-size="13" text-anchor="middle" x="345.0" y="74.0">đạt gate</text><path d="M660 80L810 80" fill="none" marker-end="url(#arrow-26197)" stroke="#667b8d" stroke-width="2"></path><rect fill="white" height="22" rx="3" width="54.4" x="707.8" y="58.0"></rect><text fill="#4b6072" font-size="13" text-anchor="middle" x="735.0" y="74.0">đạt gate</text><path d="M810 80L660 285" fill="none" marker-end="url(#arrow-26197)" stroke="#667b8d" stroke-width="2"></path><rect fill="white" height="22" rx="3" width="115.6" x="677.2" y="160.5"></rect><text fill="#4b6072" font-size="13" text-anchor="middle" x="735.0" y="176.5">capacity / policy</text><path d="M420 285L270 285" fill="none" marker-end="url(#arrow-26197)" stroke="#667b8d" stroke-width="2"></path><rect fill="white" height="22" rx="3" width="61.199999999999996" x="314.4" y="263.0"></rect><text fill="#4b6072" font-size="13" text-anchor="middle" x="345.0" y="279.0">kiểm + đo</text><path d="M270 285L270 205L810 205L810 285" fill="none" marker-end="url(#arrow-26197)" stroke="#667b8d" stroke-width="2"></path><rect fill="white" height="22" rx="3" width="102.0" x="489.0" y="184"></rect><text fill="#4b6072" font-size="13" text-anchor="middle" x="540.0" y="200">môi trường thật</text><rect fill="#e4f3f0" height="100" rx="10" stroke="#218777" stroke-width="1.8" width="240" x="30" y="30"></rect><text fill="#254154" font-size="17" font-weight="600" text-anchor="middle" x="150" y="58">G0 · Nền kiểm chứng</text><text fill="#254154" font-size="13.5" font-weight="400" text-anchor="middle" x="150" y="84">Snapshot + fixtures + đo nền</text><text fill="#254154" font-size="13.5" font-weight="400" text-anchor="middle" x="150" y="105">Chưa thực hiện sửa test</text><rect fill="#e4f3f0" height="100" rx="10" stroke="#218777" stroke-width="1.8" width="240" x="420" y="30"></rect><text fill="#254154" font-size="17" font-weight="600" text-anchor="middle" x="540" y="58">G1 · Lifecycle</text><text fill="#254154" font-size="13.5" font-weight="400" text-anchor="middle" x="540" y="84">Context / response / log</text><text fill="#254154" font-size="13.5" font-weight="400" text-anchor="middle" x="540" y="105">G0 → G1</text><rect fill="#e4f3f0" height="100" rx="10" stroke="#218777" stroke-width="1.8" width="240" x="810" y="30"></rect><text fill="#254154" font-size="17" font-weight="600" text-anchor="middle" x="930" y="58">G2 · Biên HTTP</text><text fill="#254154" font-size="13.5" font-weight="400" text-anchor="middle" x="930" y="84">Framing / body / deadlines</text><text fill="#254154" font-size="13.5" font-weight="400" text-anchor="middle" x="930" y="105">G1 → G2</text><rect fill="#e4f3f0" height="100" rx="10" stroke="#218777" stroke-width="1.8" width="240" x="30" y="235"></rect><text fill="#254154" font-size="17" font-weight="600" text-anchor="middle" x="150" y="263">G5 · Load + faults</text><text fill="#254154" font-size="13.5" font-weight="400" text-anchor="middle" x="150" y="289">G3/G4 → evidence + review</text><text fill="#254154" font-size="13.5" font-weight="400" text-anchor="middle" x="150" y="310">Bounds lấy từ số đo</text><rect fill="#e4f3f0" height="100" rx="10" stroke="#218777" stroke-width="1.8" width="240" x="420" y="235"></rect><text fill="#254154" font-size="17" font-weight="600" text-anchor="middle" x="540" y="263">G3/G4 · Tải + identity</text><text fill="#254154" font-size="13.5" font-weight="400" text-anchor="middle" x="540" y="289">Capacity / quota / quyền</text><text fill="#254154" font-size="13.5" font-weight="400" text-anchor="middle" x="540" y="310">G2 là điều kiện nền</text><rect fill="#fff1df" height="100" rx="10" stroke="#b07d37" stroke-width="1.8" width="240" x="810" y="235"></rect><text fill="#254154" font-size="17" font-weight="600" text-anchor="middle" x="930" y="263">G6/G7 · Vận hành</text><text fill="#254154" font-size="13.5" font-weight="400" text-anchor="middle" x="930" y="289">Runbook → nhu cầu → nhánh</text><text fill="#254154" font-size="13.5" font-weight="400" text-anchor="middle" x="930" y="310">Không tự đổi kiến trúc</text></svg>
```

Đề xuất phụ thuộc, không lịch cam kết. G3/G4 có phần độc lập; quota dựa admission. Nhánh G7 mở theo evidence riêng.

Gần hạn: G0–G2. Trung hạn: G3–G6. Dài hạn: G7 có điều kiện. Đây là chân trời phụ thuộc, không quy đổi thành tuần/tháng khi chưa có nhân lực, môi trường và workload mục tiêu.

## Cổng đi tiếp

| Cổng | Nội dung / task | Điều kiện vào | Bằng chứng ra |
| --- | --- | --- | --- |
| G0 | [Nền kiểm chứng](baseline.md) `B01–B04` | Code/caller hiện tại. | Snapshot/fixtures đúng, test tái hiện và profile môi trường. |
| G1 | [Lifecycle và quan sát tối thiểu](request-lifecycle.md) `L01–L04, D01, D04, O01` | G0. | Context riêng, response một lần, lỗi safe, log allowlist. |
| G2 | [Biên HTTP và body bounded](request-lifecycle.md) `H01–H04` | G1 + raw tests. | Framing/EOF/deadline đúng, parse một lần; caller tốt không hồi quy. |
| G3 | [Sức chứa và kênh máy](capacity.md) `C01–C05, D03, O02–O03` | G2 + B04. | Bounded thread/queue/lease, máy thật tiến triển trong tải kiểm, resource phục hồi. |
| G4 | [Danh tính / limiter / quyền](security.md) `S01–S05, D02` | G2; quota phụ thuộc G3. | Logout/TTL/role đúng, NAT/full table, secrets sạch. |
| G5 | [Kiểm tải và tính đúng](verification.md) `V01–V05, O04` | G3/G4 scope. | Contract + fault/load raw data + review; giới hạn rõ. |
| G6 | [Vận hành theo môi trường](operations.md) `P01–P05` | G5 + environment. | Config/runbook/shutdown/rollback diễn tập, TLS theo topology. |
| G7 | [Mở rộng theo nhu cầu](expansion.md) `E01–E06 có chọn lọc` | G6 evidence và dependencies mỗi E\*. | Requirements/prototype/decision/migration riêng từng nhánh. |

## G0 · Nền kiểm chứng

**Điều kiện vào:** Code/caller hiện tại.

**Tác vụ:** B01–B04 · [Đặc tả chi tiết](baseline.md).

**Phạm vi:** Test/tài liệu trước code middleware.

**Xong khi:** Snapshot/fixtures đúng, test tái hiện và profile môi trường.

**Không đạt / quay lui:** Không sửa nghiệp vụ chiều fixture cũ.

**Trạng thái:** Đề xuất, chưa triển khai.

## G1 · Lifecycle và quan sát tối thiểu

**Điều kiện vào:** G0.

**Tác vụ:** L01–L04, D01, D04, O01 · [Đặc tả chi tiết](request-lifecycle.md).

**Phạm vi:** HTTP helpers; không packet/schema.

**Xong khi:** Context riêng, response một lần, lỗi safe, log allowlist.

**Không đạt / quay lui:** Quay lui wrapper/hook, giữ evidence/test.

**Trạng thái:** Đề xuất, chưa triển khai.

## G2 · Biên HTTP và body bounded

**Điều kiện vào:** G1 + raw tests.

**Tác vụ:** H01–H04 · [Đặc tả chi tiết](request-lifecycle.md).

**Phạm vi:** HTTP; caller nếu contract status/media đổi.

**Xong khi:** Framing/EOF/deadline đúng, parse một lần; caller tốt không hồi quy.

**Không đạt / quay lui:** Rollback siết giao thức sai; không bỏ mọi kiểm body.

**Trạng thái:** Đề xuất, chưa triển khai.

## G3 · Sức chứa và kênh máy

**Điều kiện vào:** G2 + B04.

**Tác vụ:** C01–C05, D03, O02–O03 · [Đặc tả chi tiết](capacity.md).

**Phạm vi:** HTTP/transport/config từng task nhỏ.

**Xong khi:** Bounded thread/queue/lease, máy thật tiến triển trong tải kiểm, resource phục hồi.

**Không đạt / quay lui:** Quay config đã kiểm; không tăng bound tùy ý/replay command.

**Trạng thái:** Đề xuất, chưa triển khai.

## G4 · Danh tính / limiter / quyền

**Điều kiện vào:** G2; quota phụ thuộc G3.

**Tác vụ:** S01–S05, D02 · [Đặc tả chi tiết](security.md).

**Phạm vi:** Helpers; quyền vẫn task.

**Xong khi:** Logout/TTL/role đúng, NAT/full table, secrets sạch.

**Không đạt / quay lui:** Auth change phải compatibility; không role cache ngoài transaction.

**Trạng thái:** Đề xuất, chưa triển khai.

## G5 · Kiểm tải và tính đúng

**Điều kiện vào:** G3/G4 scope.

**Tác vụ:** V01–V05, O04 · [Đặc tả chi tiết](verification.md).

**Phạm vi:** Tests, sửa code theo nguyên nhân thật.

**Xong khi:** Contract + fault/load raw data + review; giới hạn rõ.

**Không đạt / quay lui:** Không đạt→về task lỗi, không công bố capacity.

**Trạng thái:** Đề xuất, chưa triển khai.

## G6 · Vận hành theo môi trường

**Điều kiện vào:** G5 + environment.

**Tác vụ:** P01–P05 · [Đặc tả chi tiết](operations.md).

**Phạm vi:** Deployment riêng được yêu cầu; không auto deploy.

**Xong khi:** Config/runbook/shutdown/rollback diễn tập, TLS theo topology.

**Không đạt / quay lui:** Rollback code/config không undo máy, cần đối soát.

**Trạng thái:** Đề xuất, chưa triển khai.

## G7 · Mở rộng theo nhu cầu

**Điều kiện vào:** G6 evidence và dependencies mỗi E\*.

**Tác vụ:** E01–E06 có chọn lọc · [Đặc tả chi tiết](expansion.md).

**Phạm vi:** API/runtime/schema/state theo quyết định.

**Xong khi:** Requirements/prototype/decision/migration riêng từng nhánh.

**Không đạt / quay lui:** Rollback/migration riêng; không phải mọi nhánh đều thực hiện.

**Trạng thái:** Đề xuất, chưa triển khai.

## Chuẩn bị phép kiểm trước từng cổng

B03 tạo test tái hiện trước sửa. V02/V03 được dựng và chạy trên bản ứng viên C01–C04 để chốt C05/G3; không chờ G3 đạt mới bắt đầu viết công cụ đo. G5 là lượt nghiệm thu tổng hợp trên bản và cấu hình ổn định sau G3/G4. O01 dựa threat model sơ bộ, S05 kiểm lại schema sau khi có candidate; không tạo vòng phụ thuộc giữa thiết kế log và kiểm log.

## Chia việc để coder không phải đoán

- Requirement/test tái hiện/scope/caller/acceptance/rollback trước sửa.
- Một coder ghi sản phẩm mỗi task; tester sở hữu test; reviewer sau diff/output.
- Planner đổi plan khi evidence đổi scope; lead ghi TASK.md và HTML.
- Không G1–G4 thành refactor lớn; kiểm một behavior mỗi thay đổi.
- Lịch và ước lượng chỉ lập sau khi gần hạn rõ, biết nhân lực/môi trường/tải mục tiêu.
