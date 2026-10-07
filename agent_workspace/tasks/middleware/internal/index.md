> Hồ sơ nội bộ cho agent. Chuyển từ tài liệu HTML ngày 06/10/2026; nội dung và bằng chứng cũ được giữ, chưa kiểm lại sản phẩm. Sơ đồ gốc giữ dưới dạng mã SVG trong khối XML.

KẾ HOẠCH PHÁT TRIỂN / 05.10.2026

# Kế hoạch phát triển middleware FlexMix

Bộ kế hoạch chi tiết từ HTTP lifecycle tới vận hành và mở rộng; luồng hoạt động và dữ liệu bằng sơ đồ khối.

Tài liệu thiết kế và kế hoạch · Offline / In được

<a id="packet-scope"></a>

## Phạm vi mới: mã hóa và bảo vệ gói tin

06/10/2026: người dùng xác nhận middleware là mã hóa trước gửi và kiểm chứng trước nhận, gồm debounce, chống trùng, anti-replay và mã hóa ứng dụng hai chiều. [Đọc bộ nghiên cứu gói tin mới](packet-security/index.md) và [kế hoạch 8 giai đoạn / 32 phase con](packet-security/roadmap.md). Kế hoạch HTTP/runtime bên dưới được giữ làm backlog hỗ trợ; không phải đặc tả đầy đủ của lớp mã hóa.

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

## Bạn cần biết

Kế hoạch phát triển middleware HTTP FlexMix từ nền kiểm chứng tới vận hành và mở rộng có điều kiện. Gần hạn tận dụng `server/lib/http`, giữ module, packet và transaction hiện có. Đây là kế hoạch công việc; middleware mới chưa được triển khai.

Ưu tiên đầu: nền test login một bước, response một lần, body bounded. Rủi ro trung tâm: app chờ máy chiếm hết tài nguyên khiến máy không gửi được kết quả.

## Bản đồ đọc

| Tài liệu | Nội dung |
| --- | --- |
| [Kiến trúc và ranh giới trách nhiệm](architecture.md) | Middleware phục vụ vận chuyển chung; nghiệp vụ và quyền tiếp tục ở module đã chốt. |
| [Hiện trạng và nền kiểm chứng](baseline.md) | Sửa test theo code hiện tại trước khi coi chúng là hàng rào cho middleware. |
| [Vòng đời request và biên HTTP](request-lifecycle.md) | Context riêng, body đọc một lần, response có trạng thái rõ và mọi đường ra giải phóng tài nguyên. |
| [Luồng dữ liệu, trạng thái và transaction](data-model.md) | Dữ liệu ở đâu, sống bao lâu, ai đọc/ghi và điều gì mất khi app timeout hoặc server restart. |
| [Sức chứa, timeout và độ tin cậy](capacity.md) | Giới hạn tải phải cho hệ thống tiến triển: app chờ không chặn heartbeat/result cần để hoàn tất chính request đó. |
| [Danh tính, quyền và chính sách request](security.md) | Gom cơ chế có chọn lọc; role nghiệp vụ và transaction vẫn ở tác vụ. |
| [Quan sát, số đo và chẩn đoán](observability.md) | Biết chậm tại HTTP, DB hay chờ máy; logging không tạo tải không giới hạn hoặc lộ credentials. |
| [Ma trận kiểm thử và đo tải](verification.md) | Kiểm tính đúng, lỗi đồng thời và khả năng phục hồi; so trước/sau cùng workload và môi trường. |
| [Vận hành, triển khai và phục hồi](operations.md) | Cấu hình, runbook và rollback có phép diễn tập; kế hoạch không tự cho phép deploy. |
| [Mở rộng dài hạn có điều kiện](expansion.md) | Đích mở rộng chỉ thành task khi requirement và evidence kích hoạt rõ; không mặc định phải đổi framework/broker/database. |
| [Lộ trình dài hạn và cổng nghiệm thu](roadmap.md) | Thứ tự theo phụ thuộc và đầu ra kiểm được; đặc tả mỗi tác vụ ở tài liệu chuyên đề. |

## Bản đồ chương trình

Hiện trạngĐề xuấtKho dữ liệuLỗi / điều kiện cần chốt

Lộ trình theo cổng nghiệm thu

```xml
<svg aria-label="Lộ trình theo cổng nghiệm thu" role="img" viewbox="0 0 1080 365" xmlns="http://www.w3.org/2000/svg"><title>Lộ trình theo cổng nghiệm thu</title><defs><marker id="arrow-26197" markerheight="7" markerwidth="7" orient="auto" refx="9" refy="5" viewbox="0 0 10 10"><path d="M0 0L10 5L0 10z" fill="#667b8d"></path></marker></defs><path d="M270 80L420 80" fill="none" marker-end="url(#arrow-26197)" stroke="#667b8d" stroke-width="2"></path><rect fill="white" height="22" rx="3" width="54.4" x="317.8" y="58.0"></rect><text fill="#4b6072" font-size="13" text-anchor="middle" x="345.0" y="74.0">đạt gate</text><path d="M660 80L810 80" fill="none" marker-end="url(#arrow-26197)" stroke="#667b8d" stroke-width="2"></path><rect fill="white" height="22" rx="3" width="54.4" x="707.8" y="58.0"></rect><text fill="#4b6072" font-size="13" text-anchor="middle" x="735.0" y="74.0">đạt gate</text><path d="M810 80L660 285" fill="none" marker-end="url(#arrow-26197)" stroke="#667b8d" stroke-width="2"></path><rect fill="white" height="22" rx="3" width="115.6" x="677.2" y="160.5"></rect><text fill="#4b6072" font-size="13" text-anchor="middle" x="735.0" y="176.5">capacity / policy</text><path d="M420 285L270 285" fill="none" marker-end="url(#arrow-26197)" stroke="#667b8d" stroke-width="2"></path><rect fill="white" height="22" rx="3" width="61.199999999999996" x="314.4" y="263.0"></rect><text fill="#4b6072" font-size="13" text-anchor="middle" x="345.0" y="279.0">kiểm + đo</text><path d="M270 285L270 205L810 205L810 285" fill="none" marker-end="url(#arrow-26197)" stroke="#667b8d" stroke-width="2"></path><rect fill="white" height="22" rx="3" width="102.0" x="489.0" y="184"></rect><text fill="#4b6072" font-size="13" text-anchor="middle" x="540.0" y="200">môi trường thật</text><rect fill="#e4f3f0" height="100" rx="10" stroke="#218777" stroke-width="1.8" width="240" x="30" y="30"></rect><text fill="#254154" font-size="17" font-weight="600" text-anchor="middle" x="150" y="58">G0 · Nền kiểm chứng</text><text fill="#254154" font-size="13.5" font-weight="400" text-anchor="middle" x="150" y="84">Snapshot + fixtures + đo nền</text><text fill="#254154" font-size="13.5" font-weight="400" text-anchor="middle" x="150" y="105">Chưa thực hiện sửa test</text><rect fill="#e4f3f0" height="100" rx="10" stroke="#218777" stroke-width="1.8" width="240" x="420" y="30"></rect><text fill="#254154" font-size="17" font-weight="600" text-anchor="middle" x="540" y="58">G1 · Lifecycle</text><text fill="#254154" font-size="13.5" font-weight="400" text-anchor="middle" x="540" y="84">Context / response / log</text><text fill="#254154" font-size="13.5" font-weight="400" text-anchor="middle" x="540" y="105">G0 → G1</text><rect fill="#e4f3f0" height="100" rx="10" stroke="#218777" stroke-width="1.8" width="240" x="810" y="30"></rect><text fill="#254154" font-size="17" font-weight="600" text-anchor="middle" x="930" y="58">G2 · Biên HTTP</text><text fill="#254154" font-size="13.5" font-weight="400" text-anchor="middle" x="930" y="84">Framing / body / deadlines</text><text fill="#254154" font-size="13.5" font-weight="400" text-anchor="middle" x="930" y="105">G1 → G2</text><rect fill="#e4f3f0" height="100" rx="10" stroke="#218777" stroke-width="1.8" width="240" x="30" y="235"></rect><text fill="#254154" font-size="17" font-weight="600" text-anchor="middle" x="150" y="263">G5 · Load + faults</text><text fill="#254154" font-size="13.5" font-weight="400" text-anchor="middle" x="150" y="289">G3/G4 → evidence + review</text><text fill="#254154" font-size="13.5" font-weight="400" text-anchor="middle" x="150" y="310">Bounds lấy từ số đo</text><rect fill="#e4f3f0" height="100" rx="10" stroke="#218777" stroke-width="1.8" width="240" x="420" y="235"></rect><text fill="#254154" font-size="17" font-weight="600" text-anchor="middle" x="540" y="263">G3/G4 · Tải + identity</text><text fill="#254154" font-size="13.5" font-weight="400" text-anchor="middle" x="540" y="289">Capacity / quota / quyền</text><text fill="#254154" font-size="13.5" font-weight="400" text-anchor="middle" x="540" y="310">G2 là điều kiện nền</text><rect fill="#fff1df" height="100" rx="10" stroke="#b07d37" stroke-width="1.8" width="240" x="810" y="235"></rect><text fill="#254154" font-size="17" font-weight="600" text-anchor="middle" x="930" y="263">G6/G7 · Vận hành</text><text fill="#254154" font-size="13.5" font-weight="400" text-anchor="middle" x="930" y="289">Runbook → nhu cầu → nhánh</text><text fill="#254154" font-size="13.5" font-weight="400" text-anchor="middle" x="930" y="310">Không tự đổi kiến trúc</text></svg>
```

Đề xuất phụ thuộc, không lịch cam kết. G3/G4 có phần độc lập; quota dựa admission. Nhánh G7 mở theo evidence riêng.

## Quy mô và trạng thái thực

| Mục | Giá trị |
| --- | --- |
| Tài liệu | 1 tổng quan + 11 chuyên đề tham chiếu + 8 phase lớn + 32 phase con |
| Tác vụ | 46 task có đầu vào/bước/file/kiểm/lỗi/output, chưa triển khai |
| Baseline trước | 26 test, 1 failure/18 error, 6.651s, exit 1 |
| Đợt này | Chỉ tài liệu và quy ước planner/team; không code/test HTTP |
| Benchmark/thiết bị | Chưa có tải nền, chưa kiểm Pi/Windows/điện thoại thật |
| PDF | Chưa có; người dùng cho tiếp tục không phụ thuộc PDF, không claim khớp mẫu |

## Cách dùng bộ kế hoạch

- Đọc [kiến trúc](architecture.md) và [lộ trình](roadmap.md) để nắm ranh giới/gates.
- Đọc [luồng dữ liệu](data-model.md) để hiểu command/timeout và state mất khi restart.
- Bắt đầu [G0](baseline.md); acceptance có output mới hoặc giới hạn rõ.
- Nhánh [dài hạn](expansion.md) không tự authorize đổi công nghệ hoặc deploy.

## Nguồn đối chiếu

Hiện trạng từ code/output đã ghi. Sơ đồ màu đề xuất không mô tả một hệ đang chạy. Planner rà soát read-only HTTP/caller/transport và đưa lộ trình; lead xây tài liệu chi tiết. Nguồn chính thức hỗ trợ nguyên tắc, lựa chọn tích hợp là suy luận cho FlexMix.

- [Python http.server: giới hạn production](https://docs.python.org/3/library/http.server.html)
- [OWASP API4: resource consumption](https://api-security.owasp.org/editions/2023/en/0xa4-unrestricted-resource-consumption/)
- [OWASP: logging và dữ liệu phải loại trừ](https://cheatsheetseries.owasp.org/cheatsheets/Logging_Cheat_Sheet.html)
- [OWASP: REST security](https://cheatsheetseries.owasp.org/cheatsheets/REST_Security_Cheat_Sheet.html)
