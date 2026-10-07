> Hồ sơ nội bộ cho agent. Chuyển từ tài liệu HTML ngày 06/10/2026; nội dung và bằng chứng cũ được giữ, chưa kiểm lại sản phẩm. Sơ đồ gốc giữ dưới dạng mã SVG trong khối XML.

KẾ HOẠCH PHÁT TRIỂN / 05.10.2026

# Quan sát, số đo và chẩn đoán

Biết chậm tại HTTP, DB hay chờ máy; logging không tạo tải không giới hạn hoặc lộ credentials.

Tài liệu thiết kế và kế hoạch · Offline / In đượcTrang này là nghiên cứu chuyên đề. Kế hoạch thực thi chính thức đi theo phase lớn → phase con; xem [bản đồ chương trình](index.md). Task chi tiết đã chuyển tới phase con liên kết bên dưới.

## Luồng quan sát

Hiện trạngĐề xuấtKho dữ liệuLỗi / điều kiện cần chốt

Request tới số đo và chẩn đoán

```xml
<svg aria-label="Request tới số đo và chẩn đoán" role="img" viewbox="0 0 1080 365" xmlns="http://www.w3.org/2000/svg"><title>Request tới số đo và chẩn đoán</title><defs><marker id="arrow-26668" markerheight="7" markerwidth="7" orient="auto" refx="9" refy="5" viewbox="0 0 10 10"><path d="M0 0L10 5L0 10z" fill="#667b8d"></path></marker></defs><path d="M270 80L420 80" fill="none" marker-end="url(#arrow-26668)" stroke="#667b8d" stroke-width="2"></path><rect fill="white" height="22" rx="3" width="54.4" x="317.8" y="58.0"></rect><text fill="#4b6072" font-size="13" text-anchor="middle" x="345.0" y="74.0">sanitize</text><path d="M660 80L810 80" fill="none" marker-end="url(#arrow-26668)" stroke="#667b8d" stroke-width="2"></path><rect fill="white" height="22" rx="3" width="74.8" x="697.6" y="58.0"></rect><text fill="#4b6072" font-size="13" text-anchor="middle" x="735.0" y="74.0">ghi bounded</text><path d="M810 80L270 285" fill="none" marker-end="url(#arrow-26668)" stroke="#667b8d" stroke-width="2"></path><rect fill="white" height="22" rx="3" width="61.199999999999996" x="509.4" y="160.5"></rect><text fill="#4b6072" font-size="13" text-anchor="middle" x="540.0" y="176.5">aggregate</text><path d="M810 80L660 285" fill="none" marker-end="url(#arrow-26668)" stroke="#667b8d" stroke-width="2"></path><rect fill="white" height="22" rx="3" width="81.6" x="694.2" y="160.5"></rect><text fill="#4b6072" font-size="13" text-anchor="middle" x="735.0" y="176.5">ngưỡng đã đo</text><path d="M660 285L810 285" fill="none" marker-end="url(#arrow-26668)" stroke="#667b8d" stroke-width="2"></path><rect fill="white" height="22" rx="3" width="61.199999999999996" x="704.4" y="263.0"></rect><text fill="#4b6072" font-size="13" text-anchor="middle" x="735.0" y="279.0">chẩn đoán</text><rect fill="#e4f3f0" height="100" rx="10" stroke="#218777" stroke-width="1.8" width="240" x="30" y="30"></rect><text fill="#254154" font-size="17" font-weight="600" text-anchor="middle" x="150" y="58">Context request</text><text fill="#254154" font-size="13.5" font-weight="400" text-anchor="middle" x="150" y="84">ID / stages / outcome</text><text fill="#254154" font-size="13.5" font-weight="400" text-anchor="middle" x="150" y="105">Response state / disconnect</text><rect fill="#e4f3f0" height="100" rx="10" stroke="#218777" stroke-width="1.8" width="240" x="420" y="30"></rect><text fill="#254154" font-size="17" font-weight="600" text-anchor="middle" x="540" y="58">Event allowlist</text><text fill="#254154" font-size="13.5" font-weight="400" text-anchor="middle" x="540" y="84">JSON nhỏ / nhãn bounded</text><text fill="#254154" font-size="13.5" font-weight="400" text-anchor="middle" x="540" y="105">Không raw URL / payload</text><rect fill="#e4f3f0" height="100" rx="10" stroke="#218777" stroke-width="1.8" width="240" x="810" y="30"></rect><text fill="#254154" font-size="17" font-weight="600" text-anchor="middle" x="930" y="58">Log / metrics sink</text><text fill="#254154" font-size="13.5" font-weight="400" text-anchor="middle" x="930" y="84">Bounded buffer nếu cần</text><text fill="#254154" font-size="13.5" font-weight="400" text-anchor="middle" x="930" y="105">Retention / access</text><rect fill="#e4f3f0" height="100" rx="10" stroke="#218777" stroke-width="1.8" width="240" x="30" y="235"></rect><text fill="#254154" font-size="17" font-weight="600" text-anchor="middle" x="150" y="263">Tổng hợp tải</text><text fill="#254154" font-size="13.5" font-weight="400" text-anchor="middle" x="150" y="289">Samples / p50 / p95 / lỗi</text><text fill="#254154" font-size="13.5" font-weight="400" text-anchor="middle" x="150" y="310">Theo route và từng khối</text><rect fill="#e4f3f0" height="100" rx="10" stroke="#218777" stroke-width="1.8" width="240" x="420" y="235"></rect><text fill="#254154" font-size="17" font-weight="600" text-anchor="middle" x="540" y="263">Tín hiệu sự cố</text><text fill="#254154" font-size="13.5" font-weight="400" text-anchor="middle" x="540" y="289">Queue / timeout / rejection</text><text fill="#254154" font-size="13.5" font-weight="400" text-anchor="middle" x="540" y="310">Heartbeat / DB busy</text><rect fill="#e4f3f0" height="100" rx="10" stroke="#218777" stroke-width="1.8" width="240" x="810" y="235"></rect><text fill="#254154" font-size="17" font-weight="600" text-anchor="middle" x="930" y="263">Runbook</text><text fill="#254154" font-size="13.5" font-weight="400" text-anchor="middle" x="930" y="289">Request↔command correlation</text><text fill="#254154" font-size="13.5" font-weight="400" text-anchor="middle" x="930" y="310">Chẩn đoán / rollback</text></svg>
```

Đề xuất; chưa triển khai metrics sink hoặc đo ngưỡng cảnh báo.

## Event schema đề xuất

| Trường | Nguồn | Giới hạn / ý nghĩa |
| --- | --- | --- |
| timestamp/request_id | Server | Timestamp UTC đối chiếu; duration monotonic; ID server sinh |
| method/route/module | Route khai báo | Unknown label cố định; không URL/query high-cardinality |
| status/outcome/state | Response hooks | Success/reject/timeout/error/disconnect; 200 không nói write hoàn tất |
| duration/stages | Context | Body/admission/auth/DB/command wait/write khi đo được; absent không phải 0 |
| bytes_expected/write | Serializer/writer | Không gọi expected là bytes client nhận |
| command_id/instruction | Transport hook | Instruction whitelist; không data/ket_qua |
| exception class/code | Exception biên | Không SQL/param/path/trace secret |
| identity class | Sau auth | Public/app/machine; ID user chỉ khi cần và có access control |

## Tác vụ quan sát song hành

<a id="O01"></a>

### O01 · Schema event và redaction

Đặc tả triển khai và yêu cầu team được chuyển tới [phase con chứa tác vụ](phases/lifecycle/safe-observability.md#O01). Trang này giữ nghiên cứu chuyên đề; kế hoạch thực thi có hai cấp phase lớn/phase con.

<a id="O02"></a>

### O02 · Đo stages và correlation

Đặc tả triển khai và yêu cầu team được chuyển tới [phase con chứa tác vụ](phases/capacity/budgets-recovery.md#O02). Trang này giữ nghiên cứu chuyên đề; kế hoạch thực thi có hai cấp phase lớn/phase con.

<a id="O03"></a>

### O03 · Sink bounded, retention, degraded mode

Đặc tả triển khai và yêu cầu team được chuyển tới [phase con chứa tác vụ](phases/capacity/budgets-recovery.md#O03). Trang này giữ nghiên cứu chuyên đề; kế hoạch thực thi có hai cấp phase lớn/phase con.

<a id="O04"></a>

### O04 · Metric catalogue và cảnh báo

Đặc tả triển khai và yêu cầu team được chuyển tới [phase con chứa tác vụ](phases/acceptance/load-measurement.md#O04). Trang này giữ nghiên cứu chuyên đề; kế hoạch thực thi có hai cấp phase lớn/phase con.
