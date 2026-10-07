> Hồ sơ nội bộ cho agent. Chuyển từ tài liệu HTML ngày 06/10/2026; nội dung và bằng chứng cũ được giữ, chưa kiểm lại sản phẩm. Sơ đồ gốc giữ dưới dạng mã SVG trong khối XML.

KẾ HOẠCH PHÁT TRIỂN / 05.10.2026

# Ma trận kiểm thử và đo tải

Kiểm tính đúng, lỗi đồng thời và khả năng phục hồi; so trước/sau cùng workload và môi trường.

Tài liệu thiết kế và kế hoạch · Offline / In đượcTrang này là nghiên cứu chuyên đề. Kế hoạch thực thi chính thức đi theo phase lớn → phase con; xem [bản đồ chương trình](index.md). Task chi tiết đã chuyển tới phase con liên kết bên dưới.

## Bản đồ kiểm chứng

Hiện trạngĐề xuấtKho dữ liệuLỗi / điều kiện cần chốt

Các lớp kiểm và cổng nghiệm thu

```xml
<svg aria-label="Các lớp kiểm và cổng nghiệm thu" role="img" viewbox="0 0 1080 365" xmlns="http://www.w3.org/2000/svg"><title>Các lớp kiểm và cổng nghiệm thu</title><defs><marker id="arrow-34192" markerheight="7" markerwidth="7" orient="auto" refx="9" refy="5" viewbox="0 0 10 10"><path d="M0 0L10 5L0 10z" fill="#667b8d"></path></marker></defs><path d="M270 80L420 80" fill="none" marker-end="url(#arrow-34192)" stroke="#667b8d" stroke-width="2"></path><rect fill="white" height="22" rx="3" width="54.4" x="317.8" y="58.0"></rect><text fill="#4b6072" font-size="13" text-anchor="middle" x="345.0" y="74.0">nền đúng</text><path d="M660 80L810 80" fill="none" marker-end="url(#arrow-34192)" stroke="#667b8d" stroke-width="2"></path><rect fill="white" height="22" rx="3" width="68.0" x="701.0" y="58.0"></rect><text fill="#4b6072" font-size="13" text-anchor="middle" x="735.0" y="74.0">giữ packet</text><path d="M810 80L270 285" fill="none" marker-end="url(#arrow-34192)" stroke="#667b8d" stroke-width="2"></path><rect fill="white" height="22" rx="3" width="68.0" x="506.0" y="160.5"></rect><text fill="#4b6072" font-size="13" text-anchor="middle" x="540.0" y="176.5">đúng luồng</text><path d="M270 285L420 285" fill="none" marker-end="url(#arrow-34192)" stroke="#667b8d" stroke-width="2"></path><rect fill="white" height="22" rx="3" width="88.39999999999999" x="300.8" y="263.0"></rect><text fill="#4b6072" font-size="13" text-anchor="middle" x="345.0" y="279.0">có môi trường</text><path d="M660 285L810 285" fill="none" marker-end="url(#arrow-34192)" stroke="#667b8d" stroke-width="2"></path><rect fill="white" height="22" rx="3" width="102.0" x="684.0" y="263.0"></rect><text fill="#4b6072" font-size="13" text-anchor="middle" x="735.0" y="279.0">bằng chứng thật</text><path d="M270 285L270 205L810 205L810 285" fill="none" marker-end="url(#arrow-34192)" stroke="#667b8d" stroke-width="2"></path><rect fill="white" height="22" rx="3" width="74.8" x="502.6" y="184"></rect><text fill="#4b6072" font-size="13" text-anchor="middle" x="540.0" y="200">giới hạn rõ</text><rect fill="#e4f3f0" height="100" rx="10" stroke="#218777" stroke-width="1.8" width="240" x="30" y="30"></rect><text fill="#254154" font-size="17" font-weight="600" text-anchor="middle" x="150" y="58">Helper / flow tests</text><text fill="#254154" font-size="13.5" font-weight="400" text-anchor="middle" x="150" y="84">Framing / context / policy</text><text fill="#254154" font-size="13.5" font-weight="400" text-anchor="middle" x="150" y="105">SQLite tạm + event/barrier</text><rect fill="#e4f3f0" height="100" rx="10" stroke="#218777" stroke-width="1.8" width="240" x="420" y="30"></rect><text fill="#254154" font-size="17" font-weight="600" text-anchor="middle" x="540" y="58">HTTP integration</text><text fill="#254154" font-size="13.5" font-weight="400" text-anchor="middle" x="540" y="84">Cổng động / raw socket</text><text fill="#254154" font-size="13.5" font-weight="400" text-anchor="middle" x="540" y="105">GET/POST/error/disconnect</text><rect fill="#edf2f6" height="100" rx="10" stroke="#59748a" stroke-width="1.8" width="240" x="810" y="30"></rect><text fill="#254154" font-size="17" font-weight="600" text-anchor="middle" x="930" y="58">Relay mô phỏng</text><text fill="#254154" font-size="13.5" font-weight="400" text-anchor="middle" x="930" y="84">App wait ↔ máy poll/result</text><text fill="#254154" font-size="13.5" font-weight="400" text-anchor="middle" x="930" y="105">Sai máy / late / duplicate</text><rect fill="#e4f3f0" height="100" rx="10" stroke="#218777" stroke-width="1.8" width="240" x="30" y="235"></rect><text fill="#254154" font-size="17" font-weight="600" text-anchor="middle" x="150" y="263">Load / fault injection</text><text fill="#254154" font-size="13.5" font-weight="400" text-anchor="middle" x="150" y="289">Burst / slow body / DB busy</text><text fill="#254154" font-size="13.5" font-weight="400" text-anchor="middle" x="150" y="310">RSS/thread/pending</text><rect fill="#fff1df" height="100" rx="10" stroke="#b07d37" stroke-width="1.8" width="240" x="420" y="235"></rect><text fill="#254154" font-size="17" font-weight="600" text-anchor="middle" x="540" y="263">Thiết bị mục tiêu</text><text fill="#254154" font-size="13.5" font-weight="400" text-anchor="middle" x="540" y="289">Windows / Pi / Flutter</text><text fill="#254154" font-size="13.5" font-weight="400" text-anchor="middle" x="540" y="310">Network/TLS có scope</text><rect fill="#e4f3f0" height="100" rx="10" stroke="#218777" stroke-width="1.8" width="240" x="810" y="235"></rect><text fill="#254154" font-size="17" font-weight="600" text-anchor="middle" x="930" y="263">Nghiệm thu</text><text fill="#254154" font-size="13.5" font-weight="400" text-anchor="middle" x="930" y="289">Contract + correctness</text><text fill="#254154" font-size="13.5" font-weight="400" text-anchor="middle" x="930" y="310">Capacity + vận hành</text></svg>
```

Relay tests hiện có làm nền; tải/fault/device là kế hoạch. Chưa kiểm device phải ghi giới hạn, không coi simulation đã chứng minh phần cứng.

## Ma trận bắt buộc

| Nhóm | Tình huống | Kết quả cần chứng minh |
| --- | --- | --- |
| Framing | CL thiếu/sai/âm/trùng, TE+CL, TE unsupported, EOF | Reject/close bounded, không nhận JSON prefix thiếu bytes |
| JSON | Non-object/UTF-8/deep/surrogate/Unicode tốt | Error shape giữ, max body giữ |
| Response | Serialize fail, exception trước/sau headers, reset | Một response, outcome đúng, server còn phục vụ |
| Auth/quyền | Thiếu/sai/TTL/logout/stranger/staff | login_required đúng, không SQL/command trái quyền |
| Máy | Wrong key/wrong machine result/id lỗi | Không lấy/deliver lệnh người khác |
| Timeout | Chưa take/đã take/late/duplicate | Hủy chưa lấy, không hứa rollback đã take, late không ghép mới |
| Capacity | App full/poll full/giả máy/slow body/full limiter | Bounded và progress trong profile kiểm, không starvation |
| Transaction | Revoke/remove/accept race, DB busy/lỗi ghi | Rollback và role check cùng conn |
| Log | Secrets trong mọi kênh, sink full | Allowlist sạch secret, sink không giữ slot |
| Restart | Queued/in-flight command, RAM OTP, session DB | RAM mất được ghi; không replay write, DB persist đúng |

## Tác vụ kiểm chứng G5

<a id="V01"></a>

### V01 · Contract suite và hồi quy

Đặc tả triển khai và yêu cầu team được chuyển tới [phase con chứa tác vụ](phases/acceptance/contract-regression.md#V01). Trang này giữ nghiên cứu chuyên đề; kế hoạch thực thi có hai cấp phase lớn/phase con.

<a id="V02"></a>

### V02 · Công cụ tải tái lập được

Đặc tả triển khai và yêu cầu team được chuyển tới [phase con chứa tác vụ](phases/acceptance/load-measurement.md#V02). Trang này giữ nghiên cứu chuyên đề; kế hoạch thực thi có hai cấp phase lớn/phase con.

<a id="V03"></a>

### V03 · Đồng thời và fault injection

Đặc tả triển khai và yêu cầu team được chuyển tới [phase con chứa tác vụ](phases/acceptance/fault-concurrency.md#V03). Trang này giữ nghiên cứu chuyên đề; kế hoạch thực thi có hai cấp phase lớn/phase con.

<a id="V04"></a>

### V04 · Thiết bị và hệ điều hành mục tiêu

Đặc tả triển khai và yêu cầu team được chuyển tới [phase con chứa tác vụ](phases/acceptance/target-team-gate.md#V04). Trang này giữ nghiên cứu chuyên đề; kế hoạch thực thi có hai cấp phase lớn/phase con.

<a id="V05"></a>

### V05 · Reviewer và nghiệm thu

Đặc tả triển khai và yêu cầu team được chuyển tới [phase con chứa tác vụ](phases/acceptance/target-team-gate.md#V05). Trang này giữ nghiên cứu chuyên đề; kế hoạch thực thi có hai cấp phase lớn/phase con.

## Lệnh kiểm dự kiến

```
python3 -m unittest tests.python.test_server_modules tests.python.test_server
python3 -m unittest tests.python.test_user_login tests.python.test_user_register
python3 -m unittest tests.python.test_server_security
python3 -m unittest tests.python.test_machine_share tests.python.test_machine_list tests.python.test_machine_register
python3 -m unittest tests.python.test_machine_relay tests.python.test_app_boundaries
```

Đây là lệnh các chặng sau. Đợt làm tài liệu không chạy lại chúng; baseline trước đã ghi ở [nền kiểm chứng](baseline.md).
