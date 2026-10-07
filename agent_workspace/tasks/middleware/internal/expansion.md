> Hồ sơ nội bộ cho agent. Chuyển từ tài liệu HTML ngày 06/10/2026; nội dung và bằng chứng cũ được giữ, chưa kiểm lại sản phẩm. Sơ đồ gốc giữ dưới dạng mã SVG trong khối XML.

KẾ HOẠCH PHÁT TRIỂN / 05.10.2026

# Mở rộng dài hạn có điều kiện

Đích mở rộng chỉ thành task khi requirement và evidence kích hoạt rõ; không mặc định phải đổi framework/broker/database.

Tài liệu thiết kế và kế hoạch · Offline / In đượcTrang này là nghiên cứu chuyên đề. Kế hoạch thực thi chính thức đi theo phase lớn → phase con; xem [bản đồ chương trình](index.md). Task chi tiết đã chuyển tới phase con liên kết bên dưới.

## Bản đồ quyết định

Hiện trạngĐề xuấtKho dữ liệuLỗi / điều kiện cần chốt

Bằng chứng vận hành tới nhánh mở rộng

```xml
<svg aria-label="Bằng chứng vận hành tới nhánh mở rộng" role="img" viewbox="0 0 1080 365" xmlns="http://www.w3.org/2000/svg"><title>Bằng chứng vận hành tới nhánh mở rộng</title><defs><marker id="arrow-50321" markerheight="7" markerwidth="7" orient="auto" refx="9" refy="5" viewbox="0 0 10 10"><path d="M0 0L10 5L0 10z" fill="#667b8d"></path></marker></defs><path d="M270 80L420 80" fill="none" marker-end="url(#arrow-50321)" stroke="#667b8d" stroke-width="2"></path><rect fill="white" height="22" rx="3" width="95.2" x="297.4" y="58.0"></rect><text fill="#4b6072" font-size="13" text-anchor="middle" x="345.0" y="74.0">transport risk</text><path d="M270 80L270 160L810 160L810 80" fill="none" marker-end="url(#arrow-50321)" stroke="#667b8d" stroke-width="2"></path><rect fill="white" height="22" rx="3" width="81.6" x="499.2" y="139"></rect><text fill="#4b6072" font-size="13" text-anchor="middle" x="540.0" y="155">threat model</text><path d="M150 130L150 235" fill="none" marker-end="url(#arrow-50321)" stroke="#667b8d" stroke-width="2"></path><rect fill="white" height="22" rx="3" width="81.6" x="109.2" y="160.5"></rect><text fill="#4b6072" font-size="13" text-anchor="middle" x="150.0" y="176.5">product need</text><path d="M270 285L420 285" fill="none" marker-end="url(#arrow-50321)" stroke="#667b8d" stroke-width="2"></path><rect fill="white" height="22" rx="3" width="115.6" x="287.2" y="263.0"></rect><text fill="#4b6072" font-size="13" text-anchor="middle" x="345.0" y="279.0">state model trước</text><path d="M660 285L810 285" fill="none" marker-end="url(#arrow-50321)" stroke="#667b8d" stroke-width="2"></path><rect fill="white" height="22" rx="3" width="88.39999999999999" x="690.8" y="263.0"></rect><text fill="#4b6072" font-size="13" text-anchor="middle" x="735.0" y="279.0">DB bottleneck</text><rect fill="#e4f3f0" height="100" rx="10" stroke="#218777" stroke-width="1.8" width="240" x="30" y="30"></rect><text fill="#254154" font-size="17" font-weight="600" text-anchor="middle" x="150" y="58">Evidence thực tế</text><text fill="#254154" font-size="13.5" font-weight="400" text-anchor="middle" x="150" y="84">Tải / lỗi / yêu cầu sản phẩm</text><text fill="#254154" font-size="13.5" font-weight="400" text-anchor="middle" x="150" y="105">Không chọn theo xu hướng</text><rect fill="#fff1df" height="100" rx="10" stroke="#b07d37" stroke-width="1.8" width="240" x="420" y="30"></rect><text fill="#254154" font-size="17" font-weight="600" text-anchor="middle" x="540" y="58">Runtime / TLS</text><text fill="#254154" font-size="13.5" font-weight="400" text-anchor="middle" x="540" y="84">Parser/deployment giới hạn?</text><text fill="#254154" font-size="13.5" font-weight="400" text-anchor="middle" x="540" y="105">Decision kiến trúc riêng</text><rect fill="#fff1df" height="100" rx="10" stroke="#b07d37" stroke-width="1.8" width="240" x="810" y="30"></rect><text fill="#254154" font-size="17" font-weight="600" text-anchor="middle" x="930" y="58">Device identity</text><text fill="#254154" font-size="13.5" font-weight="400" text-anchor="middle" x="930" y="84">Tem key không đủ tin cậy?</text><text fill="#254154" font-size="13.5" font-weight="400" text-anchor="middle" x="930" y="105">Provision / revoke / rotate</text><rect fill="#fff1df" height="100" rx="10" stroke="#b07d37" stroke-width="1.8" width="240" x="30" y="235"></rect><text fill="#254154" font-size="17" font-weight="600" text-anchor="middle" x="150" y="263">Command bền vững</text><text fill="#254154" font-size="13.5" font-weight="400" text-anchor="middle" x="150" y="289">Cần status sau restart?</text><text fill="#254154" font-size="13.5" font-weight="400" text-anchor="middle" x="150" y="310">ID / ack / dedupe / state</text><rect fill="#fff1df" height="100" rx="10" stroke="#b07d37" stroke-width="1.8" width="240" x="420" y="235"></rect><text fill="#254154" font-size="17" font-weight="600" text-anchor="middle" x="540" y="263">Nhiều worker / HA</text><text fill="#254154" font-size="13.5" font-weight="400" text-anchor="middle" x="540" y="289">Scale/HA cần bằng chứng</text><text fill="#254154" font-size="13.5" font-weight="400" text-anchor="middle" x="540" y="310">External state + ownership</text><rect fill="#fff1df" height="100" rx="10" stroke="#b07d37" stroke-width="1.8" width="240" x="810" y="235"></rect><text fill="#254154" font-size="17" font-weight="600" text-anchor="middle" x="930" y="263">Database / API evolution</text><text fill="#254154" font-size="13.5" font-weight="400" text-anchor="middle" x="930" y="289">Lock/traffic vượt capacity?</text><text fill="#254154" font-size="13.5" font-weight="400" text-anchor="middle" x="930" y="310">Migration / compatibility</text></svg>
```

Các nhánh có thể độc lập, không chuỗi bắt buộc. Thay API/schema/runtime chỉ triển khai sau decision và kế hoạch migration riêng.

## Nhánh nghiên cứu và triển khai riêng

<a id="E01"></a>

### E01 · HTTP runtime và TLS topology

Đặc tả triển khai và yêu cầu team được chuyển tới [phase con chứa tác vụ](phases/evolution/runtime-network.md#E01). Trang này giữ nghiên cứu chuyên đề; kế hoạch thực thi có hai cấp phase lớn/phase con.

<a id="E02"></a>

### E02 · Device credential khác tem sản phẩm

Đặc tả triển khai và yêu cầu team được chuyển tới [phase con chứa tác vụ](phases/evolution/device-credentials.md#E02). Trang này giữ nghiên cứu chuyên đề; kế hoạch thực thi có hai cấp phase lớn/phase con.

<a id="E03"></a>

### E03 · Idempotency và command identity

Đặc tả triển khai và yêu cầu team được chuyển tới [phase con chứa tác vụ](phases/evolution/command-durability.md#E03). Trang này giữ nghiên cứu chuyên đề; kế hoạch thực thi có hai cấp phase lớn/phase con.

<a id="E04"></a>

### E04 · Trạng thái command bền vững

Đặc tả triển khai và yêu cầu team được chuyển tới [phase con chứa tác vụ](phases/evolution/command-durability.md#E04). Trang này giữ nghiên cứu chuyên đề; kế hoạch thực thi có hai cấp phase lớn/phase con.

<a id="E05"></a>

### E05 · Nhiều worker và HA

Đặc tả triển khai và yêu cầu team được chuyển tới [phase con chứa tác vụ](phases/evolution/shared-state-evolution.md#E05). Trang này giữ nghiên cứu chuyên đề; kế hoạch thực thi có hai cấp phase lớn/phase con.

<a id="E06"></a>

### E06 · Database và version API

Đặc tả triển khai và yêu cầu team được chuyển tới [phase con chứa tác vụ](phases/evolution/shared-state-evolution.md#E06). Trang này giữ nghiên cứu chuyên đề; kế hoạch thực thi có hai cấp phase lớn/phase con.

## Giả định và quyết định còn mở

| Câu hỏi | Mặc định hiện tại | Kích hoạt thay đổi |
| --- | --- | --- |
| Bao nhiêu máy/app? | Chưa biết, đo tăng dần | Có workload mục tiêu/profile thực |
| Gom auth? | Giữ helper/quyền task | Profiling/bug chứng minh ích lợi |
| Status lệnh sau restart? | RAM mất, đối soát máy khi được | Product need→E03/E04 |
| Deployment/TLS ở đâu? | Chưa xác định, chưa deploy | Topology cụ thể→E01/P04 |
| Broker/multiworker? | Một process | Load/HA+shared state design→E05 |
