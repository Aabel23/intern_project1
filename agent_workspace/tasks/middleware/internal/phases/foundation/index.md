> Hồ sơ nội bộ cho agent. Chuyển từ tài liệu HTML ngày 06/10/2026; nội dung và bằng chứng cũ được giữ, chưa kiểm lại sản phẩm. Sơ đồ gốc giữ dưới dạng mã SVG trong khối XML.

PHASE LỚN / GIAI ĐOẠN CẢ TEAM

# G0 · Nền nghiên cứu và kiểm chứng

Team có hợp đồng đúng, fixture đúng và dữ liệu đo nền để thay đổi không dựa vào suy đoán.

Nghiên cứu + yêu cầu + kế hoạch triển khai cả team

## Mục tiêu và ranh giới triển khai

Team có hợp đồng đúng, fixture đúng và dữ liệu đo nền để thay đổi không dựa vào suy đoán.

| Điều kiện | Hợp đồng |
| --- | --- |
| Đầu vào | Code và caller hiện tại; baseline lỗi đã ghi từ lượt nghiên cứu trước. |
| Đầu ra / gate | Ma trận hợp đồng có nguồn; fixture hiện tại chạy được; rủi ro có test tái hiện; môi trường và dữ liệu đo được lưu. |
| Phụ thuộc | Không; bắt đầu chương trình. |
| Trạng thái | CHƯA THỰC HIỆN triển khai; không dùng nghiên cứu mã thay evidence test. |

## Các phase con

Bốn phase con của G0

```xml
<svg aria-label="Bốn phase con của G0" role="img" viewbox="0 0 1120 175" xmlns="http://www.w3.org/2000/svg"><title>Bốn phase con của G0</title><rect fill="#e4f3f0" height="100" rx="8" stroke="#218777" width="230" x="20" y="20"></rect><text fill="#254154" font-size="17" font-weight="600" text-anchor="middle" x="135" y="54">G0.1</text><text fill="#476474" font-size="13" text-anchor="middle" x="135" y="79.0">Nghiên cứu hiện trạng và hợp</text><text fill="#476474" font-size="13" text-anchor="middle" x="135" y="96.0">đồng</text><path d="M250 65L289 65" fill="none" stroke="#527184" stroke-width="2"></path><path d="M289 65l-7 -5v10z" fill="#527184"></path><rect fill="#e4f3f0" height="100" rx="8" stroke="#218777" width="230" x="295" y="20"></rect><text fill="#254154" font-size="17" font-weight="600" text-anchor="middle" x="410" y="54">G0.2</text><text fill="#476474" font-size="13" text-anchor="middle" x="410" y="79.0">Khôi phục fixture và bộ hồi</text><text fill="#476474" font-size="13" text-anchor="middle" x="410" y="96.0">quy</text><path d="M525 65L564 65" fill="none" stroke="#527184" stroke-width="2"></path><path d="M564 65l-7 -5v10z" fill="#527184"></path><rect fill="#e4f3f0" height="100" rx="8" stroke="#218777" width="230" x="570" y="20"></rect><text fill="#254154" font-size="17" font-weight="600" text-anchor="middle" x="685" y="54">G0.3</text><text fill="#476474" font-size="13" text-anchor="middle" x="685" y="87">Tái hiện rủi ro trước sửa</text><path d="M800 65L839 65" fill="none" stroke="#527184" stroke-width="2"></path><path d="M839 65l-7 -5v10z" fill="#527184"></path><rect fill="#e4f3f0" height="100" rx="8" stroke="#218777" width="230" x="845" y="20"></rect><text fill="#254154" font-size="17" font-weight="600" text-anchor="middle" x="960" y="54">G0.4</text><text fill="#476474" font-size="13" text-anchor="middle" x="960" y="79.0">Đo môi trường và dựng công cụ</text><text fill="#476474" font-size="13" text-anchor="middle" x="960" y="96.0">nền</text></svg>
```

Đề xuất thứ tự triển khai phase con. Mỗi phase con bàn giao output có bằng chứng trước khi mở việc phụ thuộc.

| Phase con | Task nguồn | Nghiên cứu / định hướng |
| --- | --- | --- |
| [G0.1 · Nghiên cứu hiện trạng và hợp đồng](contract-research.md) | B01 | Tài liệu/test còn mô tả login hai bước trong khi code đăng nhập hiện tại trả token một bước. |
| [G0.2 · Khôi phục fixture và bộ hồi quy](fixture-repair.md) | B02 | Lỗi setUp làm security tests chưa chạm vào hành vi cần kiểm. |
| [G0.3 · Tái hiện rủi ro trước sửa](risk-scenarios.md) | B03 | Rủi ro từ đọc code chưa thành bằng chứng thực nghiệm. |
| [G0.4 · Đo môi trường và dựng công cụ nền](environment-baseline.md) | B04 | Chưa có tải mục tiêu hoặc measurements để chọn capacity/deadline. |

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
