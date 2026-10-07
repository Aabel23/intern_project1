> Hồ sơ nội bộ cho agent. Chuyển từ tài liệu HTML ngày 06/10/2026; nội dung và bằng chứng cũ được giữ, chưa kiểm lại sản phẩm. Sơ đồ gốc giữ dưới dạng mã SVG trong khối XML.

KẾ HOẠCH PHÁT TRIỂN / 05.10.2026

# Vận hành, triển khai và phục hồi

Cấu hình, runbook và rollback có phép diễn tập; kế hoạch không tự cho phép deploy.

Tài liệu thiết kế và kế hoạch · Offline / In đượcTrang này là nghiên cứu chuyên đề. Kế hoạch thực thi chính thức đi theo phase lớn → phase con; xem [bản đồ chương trình](index.md). Task chi tiết đã chuyển tới phase con liên kết bên dưới.

## Luồng sự cố

Hiện trạngĐề xuấtKho dữ liệuLỗi / điều kiện cần chốt

Tín hiệu sự cố tới hành động phục hồi

```xml
<svg aria-label="Tín hiệu sự cố tới hành động phục hồi" role="img" viewbox="0 0 1080 365" xmlns="http://www.w3.org/2000/svg"><title>Tín hiệu sự cố tới hành động phục hồi</title><defs><marker id="arrow-58285" markerheight="7" markerwidth="7" orient="auto" refx="9" refy="5" viewbox="0 0 10 10"><path d="M0 0L10 5L0 10z" fill="#667b8d"></path></marker></defs><path d="M270 80L420 80" fill="none" marker-end="url(#arrow-58285)" stroke="#667b8d" stroke-width="2"></path><rect fill="white" height="22" rx="3" width="50" x="320.0" y="58.0"></rect><text fill="#4b6072" font-size="13" text-anchor="middle" x="345.0" y="74.0">signal</text><path d="M660 80L810 80" fill="none" marker-end="url(#arrow-58285)" stroke="#667b8d" stroke-width="2"></path><rect fill="white" height="22" rx="3" width="50" x="710.0" y="58.0"></rect><text fill="#4b6072" font-size="13" text-anchor="middle" x="735.0" y="74.0">runbook</text><path d="M810 80L270 285" fill="none" marker-end="url(#arrow-58285)" stroke="#667b8d" stroke-width="2"></path><rect fill="white" height="22" rx="3" width="61.199999999999996" x="509.4" y="160.5"></rect><text fill="#4b6072" font-size="13" text-anchor="middle" x="540.0" y="176.5">hành động</text><path d="M810 80L660 285" fill="none" marker-end="url(#arrow-58285)" stroke="#667b8d" stroke-width="2"></path><rect fill="white" height="22" rx="3" width="54.4" x="707.8" y="160.5"></rect><text fill="#4b6072" font-size="13" text-anchor="middle" x="735.0" y="176.5">giới hạn</text><path d="M270 285L270 205L810 205L810 285" fill="none" marker-end="url(#arrow-58285)" stroke="#667b8d" stroke-width="2"></path><rect fill="white" height="22" rx="3" width="68.0" x="506.0" y="184"></rect><text fill="#4b6072" font-size="13" text-anchor="middle" x="540.0" y="200">bằng chứng</text><rect fill="#e4f3f0" height="100" rx="10" stroke="#218777" stroke-width="1.8" width="240" x="30" y="30"></rect><text fill="#254154" font-size="17" font-weight="600" text-anchor="middle" x="150" y="58">Outcomes + resources</text><text fill="#254154" font-size="13.5" font-weight="400" text-anchor="middle" x="150" y="84">Status / stage / queue</text><text fill="#254154" font-size="13.5" font-weight="400" text-anchor="middle" x="150" y="105">Heartbeat / DB / sink</text><rect fill="#e4f3f0" height="100" rx="10" stroke="#218777" stroke-width="1.8" width="240" x="420" y="30"></rect><text fill="#254154" font-size="17" font-weight="600" text-anchor="middle" x="540" y="58">Phân loại nguyên nhân</text><text fill="#254154" font-size="13.5" font-weight="400" text-anchor="middle" x="540" y="84">App/poll load hoặc DB</text><text fill="#254154" font-size="13.5" font-weight="400" text-anchor="middle" x="540" y="105">Máy offline / mạng</text><rect fill="#e4f3f0" height="100" rx="10" stroke="#218777" stroke-width="1.8" width="240" x="810" y="30"></rect><text fill="#254154" font-size="17" font-weight="600" text-anchor="middle" x="930" y="58">Runbook</text><text fill="#254154" font-size="13.5" font-weight="400" text-anchor="middle" x="930" y="84">Giảm tải / kiểm connection</text><text fill="#254154" font-size="13.5" font-weight="400" text-anchor="middle" x="930" y="105">Đối soát / rollback</text><rect fill="#e4f3f0" height="100" rx="10" stroke="#218777" stroke-width="1.8" width="240" x="30" y="235"></rect><text fill="#254154" font-size="17" font-weight="600" text-anchor="middle" x="150" y="263">Kiểm sau phục hồi</text><text fill="#254154" font-size="13.5" font-weight="400" text-anchor="middle" x="150" y="289">Request mới + heartbeat</text><text fill="#254154" font-size="13.5" font-weight="400" text-anchor="middle" x="150" y="310">Slots / queue / RSS</text><rect fill="#fff1df" height="100" rx="10" stroke="#b07d37" stroke-width="1.8" width="240" x="420" y="235"></rect><text fill="#254154" font-size="17" font-weight="600" text-anchor="middle" x="540" y="263">Giới hạn hành động</text><text fill="#254154" font-size="13.5" font-weight="400" text-anchor="middle" x="540" y="289">Không retry write mù</text><text fill="#254154" font-size="13.5" font-weight="400" text-anchor="middle" x="540" y="310">Không replay RAM lệnh</text><rect fill="#e4f3f0" height="100" rx="10" stroke="#218777" stroke-width="1.8" width="240" x="810" y="235"></rect><text fill="#254154" font-size="17" font-weight="600" text-anchor="middle" x="930" y="263">Hồ sơ sự cố</text><text fill="#254154" font-size="13.5" font-weight="400" text-anchor="middle" x="930" y="289">Thời gian / tác động</text><text fill="#254154" font-size="13.5" font-weight="400" text-anchor="middle" x="930" y="310">Config / nguyên nhân</text></svg>
```

Đề xuất vận hành; chưa xác định môi trường deployment, chưa rollout thực.

## Runbook tối thiểu

| Sự cố | Tín hiệu phân biệt | Hành động / điều cần tránh |
| --- | --- | --- |
| App/poll quá tải | Active group/queue wait/reject/thread | Chặn enqueue mới, giữ result/heartbeat, không tăng trần vô hạn |
| DB busy/chậm | DB stage/SQLite outcome/locks | Tìm transaction dài, giữ fallback, không retry write mù |
| Máy offline | Heartbeat stale/poll-result timings | Kiểm mạng máy, không coi mọi command timeout là offline |
| Đã take/mất result | Pending/late correlation | Đọc lại máy, không nói lệnh chưa chạy |
| Disconnect | Business result + write outcome | Release HTTP, không tự cancel máy đã nhận |
| Log sink/disk full | Drop counter/sink failures | Bound logging, sửa storage, không fallback secret |
| Restart | RAM mất/DB giữ | Không replay write, đối soát máy/session |
| Sai config | Boot validation | Fail sớm, không fallback silently bỏ cap |

## Tác vụ vận hành G6

<a id="P01"></a>

### P01 · Cấu hình và boot validation

Đặc tả triển khai và yêu cầu team được chuyển tới [phase con chứa tác vụ](phases/operations/configuration-validation.md#P01). Trang này giữ nghiên cứu chuyên đề; kế hoạch thực thi có hai cấp phase lớn/phase con.

<a id="P02"></a>

### P02 · Shutdown và restart semantics

Đặc tả triển khai và yêu cầu team được chuyển tới [phase con chứa tác vụ](phases/operations/shutdown-restart.md#P02). Trang này giữ nghiên cứu chuyên đề; kế hoạch thực thi có hai cấp phase lớn/phase con.

<a id="P03"></a>

### P03 · Rollout chặng nhỏ và rollback

Đặc tả triển khai và yêu cầu team được chuyển tới [phase con chứa tác vụ](phases/operations/rollout-rollback.md#P03). Trang này giữ nghiên cứu chuyên đề; kế hoạch thực thi có hai cấp phase lớn/phase con.

<a id="P04"></a>

### P04 · Topology mạng và TLS

Đặc tả triển khai và yêu cầu team được chuyển tới [phase con chứa tác vụ](phases/operations/network-runbooks.md#P04). Trang này giữ nghiên cứu chuyên đề; kế hoạch thực thi có hai cấp phase lớn/phase con.

<a id="P05"></a>

### P05 · Sổ vận hành và đánh giá tiếp

Đặc tả triển khai và yêu cầu team được chuyển tới [phase con chứa tác vụ](phases/operations/network-runbooks.md#P05). Trang này giữ nghiên cứu chuyên đề; kế hoạch thực thi có hai cấp phase lớn/phase con.
