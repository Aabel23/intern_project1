# TASK — Kế hoạch middleware dài hạn

## Yêu cầu gốc

> bây giờ tôi muốn tiến hành phát triển middleware cho hệ thống, nghiên cứu sâu

> note vào, các file cho tôi đọc phải được viết bằng html, định dạng theo mẫu đã có

> tài liệu không nên để tên phase00 như vầy, thật ra, planner sẽ vạch ra một kế hoahcj siêu dài hạn, chia thành các file con, các luồng hoạt động, dữ liệu sẽ được biểu thị bằng biểu đồ khối, tham khảo trong pdf! làm lại cho tôi

> chưa có thì thôi, nói chung là một plan cực kỳ chi tiết

## Trạng thái

- Bộ kế hoạch đã tạo; code sản phẩm và test HTTP chưa sửa.
- Planner đã rà soát read-only, lead tạo chi tiết/task/HTML/SVG.
- Trang đọc: index.html; tên con theo nội dung, không phase00.
- PDF chưa có, người dùng đã cho phép tiếp tục không phụ thuộc mẫu.

## Phase lớn và phân công task (chưa triển khai)

- G0 — Nền nghiên cứu và kiểm chứng: B01, B02, B03, B04; phases/foundation/index.html.
- G1 — Vòng đời request và quan sát an toàn: L01, D01, L02, L03, L04, D04, O01; phases/lifecycle/index.html.
- G2 — Biên HTTP, body và tương thích client: H01, H02, H03, H04; phases/http-boundary/index.html.
- G3 — Sức chứa và tiến triển lệnh máy: C01, C02, C03, D03, C04, C05, O02, O03; phases/capacity/index.html.
- G4 — Danh tính, quyền và chính sách bảo vệ: S01, S02, D02, S04, S03, S05; phases/identity/index.html.
- G5 — Nghiệm thu tích hợp, lỗi và tải: V01, V03, V02, O04, V04, V05; phases/acceptance/index.html.
- G6 — Vận hành, rollout và phục hồi: P01, P02, P03, P04, P05; phases/operations/index.html.
- G7 — Mở rộng dài hạn theo bằng chứng: E01, E02, E03, E04, E05, E06; phases/evolution/index.html.

## Bằng chứng từ lượt nghiên cứu trước

- 26 test, 1 failure/18 error, 6.651s, exit 1; không chạy lại trong đợt tài liệu.
- 17 security test lỗi setUp LOGIN_STATES đã bỏ, một lỗi tick, một failure endpoint cũ.
- Chưa benchmark và chưa kiểm Pi/Windows/Flutter hardware thật.

## Tài liệu

- index.html — Kế hoạch phát triển middleware FlexMix
- architecture.html — Kiến trúc và ranh giới trách nhiệm
- baseline.html — Hiện trạng và nền kiểm chứng
- request-lifecycle.html — Vòng đời request và biên HTTP
- data-model.html — Luồng dữ liệu, trạng thái và transaction
- capacity.html — Sức chứa, timeout và độ tin cậy
- security.html — Danh tính, quyền và chính sách request
- observability.html — Quan sát, số đo và chẩn đoán
- verification.html — Ma trận kiểm thử và đo tải
- operations.html — Vận hành, triển khai và phục hồi
- expansion.html — Mở rộng dài hạn có điều kiện
- roadmap.html — Lộ trình dài hạn và cổng nghiệm thu

## Task registry

- B01 — Lập snapshot hợp đồng thực
- B02 — Khôi phục fixture và test lỗi thời
- B03 — Test tái hiện biên và response
- B04 — Đo profile môi trường và ngân sách ban đầu
- L01 — Context và thời gian theo request
- L02 — Trạng thái response và serialize
- L03 — Biên exception GET/POST
- L04 — Route, query và method
- H01 — Framing được chấp nhận
- H02 — Đọc đủ byte và parse một lần
- H03 — Deadline đọc và reject sớm
- H04 — Media type và response headers
- D01 — Contract metadata và context
- D02 — Bảo toàn transaction quyền và ghi
- D03 — Bounded state và cleanup
- D04 — Correlation request và command
- C01 — Bound kết nối trước tạo thread
- C02 — Tách sức chứa các nhóm công việc
- C03 — Bound command queue theo máy và tổng
- C04 — Deadline tổng và hủy đúng nghĩa
- C05 — Bão hòa rồi phục hồi
- S01 — Ma trận route/auth và policy metadata
- S02 — Phiên thu hồi và nhu cầu gom auth
- S03 — Limiter với NAT và bảng đầy
- S04 — Quyền GET status và device threat model
- S05 — Threat model và log sạch secret
- O01 — Schema event và redaction
- O02 — Đo stages và correlation
- O03 — Sink bounded, retention, degraded mode
- O04 — Metric catalogue và cảnh báo
- V01 — Contract suite và hồi quy
- V02 — Công cụ tải tái lập được
- V03 — Đồng thời và fault injection
- V04 — Thiết bị và hệ điều hành mục tiêu
- V05 — Reviewer và nghiệm thu
- P01 — Cấu hình và boot validation
- P02 — Shutdown và restart semantics
- P03 — Rollout chặng nhỏ và rollback
- P04 — Topology mạng và TLS
- P05 — Sổ vận hành và đánh giá tiếp
- E01 — HTTP runtime và TLS topology
- E02 — Device credential khác tem sản phẩm
- E03 — Idempotency và command identity
- E04 — Trạng thái command bền vững
- E05 — Nhiều worker và HA
- E06 — Database và version API

## Giới hạn và quyết định

- Không lịch/threshold/framework/broker/schema giả. E* là nhánh có điều kiện.
- Mỗi task có inputs/steps/files/acceptance/risk/output trong HTML; roadmap giữ dependencies/rollback.
- Quy ước AGENTS/PHASE_FORMAT/planner/TEAM/README/TEMPLATE đổi theo tên ngữ nghĩa và sơ đồ khối.

## Kiểm bộ tài liệu đợt này

- Kiểm HTML/local links/SVG XML: 12 trang, 46 task, 13 sơ đồ, 227 liên kết local; không link hỏng hoặc ID trùng, exit 0.
- Chrome headless render: kiến trúc, dữ liệu và mobile lifecycle mở được; kiểm ảnh thực tế. Sơ đồ trên màn nhỏ cuộn ngang để giữ chữ đọc được.
- python3 agent_workspace/sync_agents.py --check: Agents are in sync, exit 0.
- git diff --check: exit 0.
- Các lệnh này kiểm tài liệu/đồng bộ vai, không chứng minh middleware sản phẩm đã triển khai.

## Yêu cầu cập nhật — phân cấp triển khai team AI

> chi tiết hơn, mỗi phase sẽ là một giai ooanj triển khai của cả team AI, với mỗi giai đoạn đó thì chia thành các phase con để triển khai, trong đây chứa nghiên cứu chi tiết kèm thông tin và định hướng, việc cần làm, yêu cầu của phase

- 8 phase lớn / 32 phase con / 46 task được chuyển vào phase con tương ứng.
- Chuyên đề root là nghiên cứu tham chiếu; canonical implementation spec ở phases/.
- Mỗi phase có nguồn/giả thuyết, direction, requirements, steps/files, roles/handoff, tests/gate/rollback.
- Planner/security chỉ đọc mã để lập kế hoạch; chưa coder/tester triển khai sản phẩm.
- Counter reset/late result cross-restart là giả thuyết code; yêu cầu regression và quyết định chặn rollout nếu tái hiện, không claim exploit đã chạy.
- phase-map.json là inventory nội bộ, không scheduler/registry runtime.

### G0 — Nền nghiên cứu và kiểm chứng

- G0.1 Nghiên cứu hiện trạng và hợp đồng → phases/foundation/contract-research.html; tasks B01; CHƯA THỰC HIỆN.
- G0.2 Khôi phục fixture và bộ hồi quy → phases/foundation/fixture-repair.html; tasks B02; CHƯA THỰC HIỆN.
- G0.3 Tái hiện rủi ro trước sửa → phases/foundation/risk-scenarios.html; tasks B03; CHƯA THỰC HIỆN.
- G0.4 Đo môi trường và dựng công cụ nền → phases/foundation/environment-baseline.html; tasks B04; CHƯA THỰC HIỆN.
### G1 — Vòng đời request và quan sát an toàn

- G1.1 Context và dữ liệu request → phases/lifecycle/context-design.html; tasks L01, D01; CHƯA THỰC HIỆN.
- G1.2 Response state và biên lỗi → phases/lifecycle/response-boundary.html; tasks L02, L03; CHƯA THỰC HIỆN.
- G1.3 Dispatch và liên hệ request–command → phases/lifecycle/dispatch-correlation.html; tasks L04, D04; CHƯA THỰC HIỆN.
- G1.4 Event schema và kiểm mọi log sink → phases/lifecycle/safe-observability.html; tasks O01; CHƯA THỰC HIỆN.
### G2 — Biên HTTP, body và tương thích client

- G2.1 Nghiên cứu parser và chính sách framing → phases/http-boundary/framing-policy.html; tasks H01; CHƯA THỰC HIỆN.
- G2.2 Đọc body đủ byte và parse một lần → phases/http-boundary/body-integrity.html; tasks H02; CHƯA THỰC HIỆN.
- G2.3 Deadline đọc và early reject → phases/http-boundary/read-deadline.html; tasks H03; CHƯA THỰC HIỆN.
- G2.4 Media type, lỗi và tương thích caller → phases/http-boundary/client-compatibility.html; tasks H04; CHƯA THỰC HIỆN.
### G3 — Sức chứa và tiến triển lệnh máy

- G3.1 Giới hạn ingress trước tạo thread → phases/capacity/ingress-bound.html; tasks C01; CHƯA THỰC HIỆN.
- G3.2 Phân nhóm công việc và headroom → phases/capacity/workload-lanes.html; tasks C02; CHƯA THỰC HIỆN.
- G3.3 Queue, waiter và cleanup → phases/capacity/queue-invariants.html; tasks C03, D03; CHƯA THỰC HIỆN.
- G3.4 Budgets, lỗi đồng thời và phục hồi → phases/capacity/budgets-recovery.html; tasks C04, C05, O02, O03; CHƯA THỰC HIỆN.
### G4 — Danh tính, quyền và chính sách bảo vệ

- G4.1 Route policy và thứ tự xác thực → phases/identity/route-policy.html; tasks S01; CHƯA THỰC HIỆN.
- G4.2 Phiên, thu hồi và lựa chọn gom auth → phases/identity/session-revocation.html; tasks S02; CHƯA THỰC HIỆN.
- G4.3 Quyền, transaction và privacy trạng thái → phases/identity/authorization-transaction.html; tasks D02, S04; CHƯA THỰC HIỆN.
- G4.4 Limiter, NAT và threat model → phases/identity/limiter-threat-model.html; tasks S03, S05; CHƯA THỰC HIỆN.
### G5 — Nghiệm thu tích hợp, lỗi và tải

- G5.1 Hợp đồng liên thành phần và hồi quy → phases/acceptance/contract-regression.html; tasks V01; CHƯA THỰC HIỆN.
- G5.2 Fault injection và bất biến đồng thời → phases/acceptance/fault-concurrency.html; tasks V03; CHƯA THỰC HIỆN.
- G5.3 Đo tải, số liệu stages và cảnh báo → phases/acceptance/load-measurement.html; tasks V02, O04; CHƯA THỰC HIỆN.
- G5.4 Thiết bị mục tiêu và gate cả team → phases/acceptance/target-team-gate.html; tasks V04, V05; CHƯA THỰC HIỆN.
### G6 — Vận hành, rollout và phục hồi

- G6.1 Cấu hình, boot và profile vận hành → phases/operations/configuration-validation.html; tasks P01; CHƯA THỰC HIỆN.
- G6.2 Dừng server, restart và kết quả chưa chắc chắn → phases/operations/shutdown-restart.html; tasks P02; CHƯA THỰC HIỆN.
- G6.3 Candidate, rollout và quay lui → phases/operations/rollout-rollback.html; tasks P03; CHƯA THỰC HIỆN.
- G6.4 Topology, TLS và sổ vận hành → phases/operations/network-runbooks.html; tasks P04, P05; CHƯA THỰC HIỆN.
### G7 — Mở rộng dài hạn theo bằng chứng

- G7.1 Runtime HTTP và mạng triển khai → phases/evolution/runtime-network.html; tasks E01; CHƯA THỰC HIỆN.
- G7.2 Vòng đời credential thiết bị → phases/evolution/device-credentials.html; tasks E02; CHƯA THỰC HIỆN.
- G7.3 Command identity, idempotency và bền vững → phases/evolution/command-durability.html; tasks E03, E04; CHƯA THỰC HIỆN.
- G7.4 Scale-out, database và version API → phases/evolution/shared-state-evolution.html; tasks E05, E06; CHƯA THỰC HIỆN.

## Kiểm và review bộ phase hai cấp

- Planner kiểm độc lập: 46 task không trùng ownership, DAG G0–G6 + G7 branches không vòng.
- Đã sửa mâu thuẫn canonical V03/C05 (candidate harness G3 khác final G5) và P04/E01 (không gate G6 chờ G7).
- Checker local links/fragments/SVG/IDs/manifest: 52 trang HTML, 8 phase lớn, 32 phase con, 46 task canonical, 93 sơ đồ; pass.
- Rà dependency bằng JSON không thay narrative review; giữ cả hai bằng chứng.

- Chrome headless đã render và kiểm ảnh trang tổng quan, phase lớn G1 và phase con G3.4; nguồn/quy tắc/requirements/luồng/team hiển thị rõ. Đã wrap nhãn sơ đồ dài để không tràn khối.

- Planner recheck: các vòng C05/V02/V03 và P04/E01 đã sửa; ĐẠT trong phạm vi tính nhất quán kế hoạch. Không phải nghiệm thu middleware sản phẩm.
