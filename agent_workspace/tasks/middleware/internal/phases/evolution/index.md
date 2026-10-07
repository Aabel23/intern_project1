> Hồ sơ nội bộ cho agent. Chuyển từ tài liệu HTML ngày 06/10/2026; nội dung và bằng chứng cũ được giữ, chưa kiểm lại sản phẩm. Sơ đồ gốc giữ dưới dạng mã SVG trong khối XML.

PHASE LỚN / GIAI ĐOẠN CẢ TEAM

# G7 · Mở rộng dài hạn theo bằng chứng

Team nghiên cứu rồi triển khai thay runtime/identity/command durability/scale khi requirements thực đòi.

Nghiên cứu + yêu cầu + kế hoạch triển khai cả team

## Mục tiêu và ranh giới triển khai

Team nghiên cứu rồi triển khai thay runtime/identity/command durability/scale khi requirements thực đòi.

| Điều kiện | Hợp đồng |
| --- | --- |
| Đầu vào | G6 evidence/nhu cầu cụ thể; chỉ kích hoạt nhánh được chọn và quyết định kiến trúc riêng. |
| Đầu ra / gate | Mỗi nhánh kích hoạt có ADR, contract/migration, tests/fault/load và rollback; không yêu cầu mọi nhánh hoàn tất. |
| Phụ thuộc | G6 |
| Trạng thái | CHƯA THỰC HIỆN triển khai; không dùng nghiên cứu mã thay evidence test. |

## Các phase con

Bốn phase con của G7

```xml
<svg aria-label="Bốn phase con của G7" role="img" viewbox="0 0 1120 175" xmlns="http://www.w3.org/2000/svg"><title>Bốn phase con của G7</title><rect fill="#e4f3f0" height="100" rx="8" stroke="#218777" width="230" x="20" y="20"></rect><text fill="#254154" font-size="17" font-weight="600" text-anchor="middle" x="135" y="54">G7.1</text><text fill="#476474" font-size="13" text-anchor="middle" x="135" y="79.0">Runtime HTTP và mạng triển</text><text fill="#476474" font-size="13" text-anchor="middle" x="135" y="96.0">khai</text><path d="M250 65L289 65" fill="none" stroke="#527184" stroke-width="2"></path><path d="M289 65l-7 -5v10z" fill="#527184"></path><rect fill="#e4f3f0" height="100" rx="8" stroke="#218777" width="230" x="295" y="20"></rect><text fill="#254154" font-size="17" font-weight="600" text-anchor="middle" x="410" y="54">G7.2</text><text fill="#476474" font-size="13" text-anchor="middle" x="410" y="87">Vòng đời credential thiết bị</text><path d="M525 65L564 65" fill="none" stroke="#527184" stroke-width="2"></path><path d="M564 65l-7 -5v10z" fill="#527184"></path><rect fill="#e4f3f0" height="100" rx="8" stroke="#218777" width="230" x="570" y="20"></rect><text fill="#254154" font-size="17" font-weight="600" text-anchor="middle" x="685" y="54">G7.3</text><text fill="#476474" font-size="13" text-anchor="middle" x="685" y="79.0">Command identity, idempotency</text><text fill="#476474" font-size="13" text-anchor="middle" x="685" y="96.0">và</text><path d="M800 65L839 65" fill="none" stroke="#527184" stroke-width="2"></path><path d="M839 65l-7 -5v10z" fill="#527184"></path><rect fill="#e4f3f0" height="100" rx="8" stroke="#218777" width="230" x="845" y="20"></rect><text fill="#254154" font-size="17" font-weight="600" text-anchor="middle" x="960" y="54">G7.4</text><text fill="#476474" font-size="13" text-anchor="middle" x="960" y="79.0">Scale-out, database và</text><text fill="#476474" font-size="13" text-anchor="middle" x="960" y="96.0">version AP</text></svg>
```

Đề xuất thứ tự bàn giao. G7 là các nhánh có điều kiện độc lập; mũi tên chỉ thứ tự đọc, không yêu cầu thực hiện tất cả.

| Phase con | Task nguồn | Nghiên cứu / định hướng |
| --- | --- | --- |
| [G7.1 · Runtime HTTP và mạng triển khai](runtime-network.md) | E01 | Stdlib HTTP có giới hạn production; đổi framework không tự giải quyết blocking transport/DB. |
| [G7.2 · Vòng đời credential thiết bị](device-credentials.md) | E02 | Người chụp tem product key có thể xưng danh máy theo cơ chế hiện tại. |
| [G7.3 · Command identity, idempotency và bền vững](command-durability.md) | E03, E04 | Request timeout/restart khiến kết quả không chắc; server-only dedupe không ngăn máy write lặp. |
| [G7.4 · Scale-out, database và version API](shared-state-evolution.md) | E05, E06 | Nhiều worker sẽ chia đôi RAM state; engine/broker mới không tự bảo đảm ownership và giao lệnh. |

## Team triển khai và chuỗi bàn giao

Phối hợp của team trong từng phase con

```xml
<svg aria-label="Phối hợp của team trong từng phase con" role="img" viewbox="0 0 1120 175" xmlns="http://www.w3.org/2000/svg"><title>Phối hợp của team trong từng phase con</title><rect fill="#e4f3f0" height="100" rx="8" stroke="#218777" width="230" x="20" y="20"></rect><text fill="#254154" font-size="17" font-weight="600" text-anchor="middle" x="135" y="54">Lead → Planner</text><text fill="#476474" font-size="13" text-anchor="middle" x="135" y="87">Scope + inputs + nghiên cứu</text><path d="M250 65L289 65" fill="none" stroke="#527184" stroke-width="2"></path><path d="M289 65l-7 -5v10z" fill="#527184"></path><rect fill="#e4f3f0" height="100" rx="8" stroke="#218777" width="230" x="295" y="20"></rect><text fill="#254154" font-size="17" font-weight="600" text-anchor="middle" x="410" y="54">Tester + Cybersecurity</text><text fill="#476474" font-size="13" text-anchor="middle" x="410" y="87">Test design + risk policy</text><path d="M525 65L564 65" fill="none" stroke="#527184" stroke-width="2"></path><path d="M564 65l-7 -5v10z" fill="#527184"></path><rect fill="#e4f3f0" height="100" rx="8" stroke="#218777" width="230" x="570" y="20"></rect><text fill="#254154" font-size="17" font-weight="600" text-anchor="middle" x="685" y="54">Coder → Tester</text><text fill="#476474" font-size="13" text-anchor="middle" x="685" y="87">Patch → output + số đo</text><path d="M800 65L839 65" fill="none" stroke="#527184" stroke-width="2"></path><path d="M839 65l-7 -5v10z" fill="#527184"></path><rect fill="#e4f3f0" height="100" rx="8" stroke="#218777" width="230" x="845" y="20"></rect><text fill="#254154" font-size="17" font-weight="600" text-anchor="middle" x="960" y="54">Reviewer → Lead</text><text fill="#476474" font-size="13" text-anchor="middle" x="960" y="87">Findings → gate quyết định</text></svg>
```

Mỗi vai làm đúng thời điểm; reviewer bắt đầu khi có diff/output. Tester có thể chuẩn bị độc lập, chỉ một coder ghi sản phẩm mỗi task.

| Vai | Trách nhiệm | Yêu cầu đầu ra | Bàn giao |
| --- | --- | --- | --- |
| Lead | Mở đúng scope, kiểm inputs, giao một coder, nhận bằng chứng và quyết định gate. | Phase con phải có đủ artifacts mới; không lời tự nhận. | Giao việc / decision record / blocker triage. |
| Planner | Lần source/caller, giải giả thuyết, chốt interface/phương án và cập nhật phạm vi. | Đặc tả có file:dòng, assumptions, inputs/outputs, requirements. | Research + design/decision record. |
| Tester | Sở hữu test/harness; tái hiện trước sửa khi là bug; chạy sau sửa, thu raw evidence. | Test behavior, DB/cổng tạm, event/barrier, sample counts. | Tests + commands + output/exit + samples/limits. |
| Coder | Một coder ghi sản phẩm mỗi task; xem caller trước interface change, không sửa test tester để pass. | Diff tối thiểu theo scope và contract, tự kiểm CODE_STYLE. | Diff/file/caller + checklist + verification. |
| Reviewer | Rà sau có diff/output; kiểm ranh giới, packet, concurrency, transaction và số đo. | Finding trigger/file:dòng/hậu quả; phân biệt blocker và gợi ý. | Review findings + status xử lý. |
| Cybersecurity | Rà trust boundaries/secret/auth/body/overload/restart từ nghiên cứu và diff. | Không đổi contract vì giả định; policy/negative tests/residual risks rõ. | Security findings + test requirements + residual risk. |

## Hồ sơ mở cổng phase lớn

- Đặc tả phase con được chốt và inputs đủ; không scope/interface mở chưa xử lý.
- Diff/file/caller, requirement→test→output mới, exit code, logs/samples/môi trường.
- Reviewer và security findings có trạng thái, blocker đã sửa hoặc thay scope rõ.
- Bằng chứng resource/transaction/packet invariants theo yêu cầu, limits chưa kiểm được ghi tác động.
- Rollback/recovery instructions và đầu vào phase tiếp đã hình thành.

Nếu gate không đạt, lead trả việc về phase con liên quan. Đây là vòng sửa việc trong phase, không tạo cạnh dependency ngược. Không mở phase phụ thuộc dựa vào một câu “team đã review”.

## Cách kích hoạt nhánh dài hạn

Mỗi nhánh có trigger/ADR và quyết định thay kiến trúc riêng. Device identity không tự phụ thuộc runtime mới. Shared-state phải có command/ownership design phù hợp nếu yêu cầu durability; không thêm nhiều worker trực tiếp trên RAM. Nhánh chưa được chọn giữ KHÔNG KÍCH HOẠT, không cần báo hoàn tất toàn bộ.
