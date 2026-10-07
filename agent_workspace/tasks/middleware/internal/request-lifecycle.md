> Hồ sơ nội bộ cho agent. Chuyển từ tài liệu HTML ngày 06/10/2026; nội dung và bằng chứng cũ được giữ, chưa kiểm lại sản phẩm. Sơ đồ gốc giữ dưới dạng mã SVG trong khối XML.

KẾ HOẠCH PHÁT TRIỂN / 05.10.2026

# Vòng đời request và biên HTTP

Context riêng, body đọc một lần, response có trạng thái rõ và mọi đường ra giải phóng tài nguyên.

Tài liệu thiết kế và kế hoạch · Offline / In đượcTrang này là nghiên cứu chuyên đề. Kế hoạch thực thi chính thức đi theo phase lớn → phase con; xem [bản đồ chương trình](index.md). Task chi tiết đã chuyển tới phase con liên kết bên dưới.

## Luồng mục tiêu

Hiện trạngĐề xuấtKho dữ liệuLỗi / điều kiện cần chốt

Vòng đời request và nhánh lỗi

```xml
<svg aria-label="Vòng đời request và nhánh lỗi" role="img" viewbox="0 0 1080 365" xmlns="http://www.w3.org/2000/svg"><title>Vòng đời request và nhánh lỗi</title><defs><marker id="arrow-18860" markerheight="7" markerwidth="7" orient="auto" refx="9" refy="5" viewbox="0 0 10 10"><path d="M0 0L10 5L0 10z" fill="#667b8d"></path></marker></defs><path d="M270 80L420 80" fill="none" marker-end="url(#arrow-18860)" stroke="#667b8d" stroke-width="2"></path><rect fill="white" height="22" rx="3" width="68.0" x="311.0" y="58.0"></rect><text fill="#4b6072" font-size="13" text-anchor="middle" x="345.0" y="74.0">kiểm trước</text><path d="M660 80L810 80" fill="none" marker-end="url(#arrow-18860)" stroke="#667b8d" stroke-width="2"></path><rect fill="white" height="22" rx="3" width="61.199999999999996" x="704.4" y="58.0"></rect><text fill="#4b6072" font-size="13" text-anchor="middle" x="735.0" y="74.0">được nhận</text><path d="M810 80L660 285" fill="none" marker-end="url(#arrow-18860)" stroke="#667b8d" stroke-width="2"></path><rect fill="white" height="22" rx="3" width="88.39999999999999" x="690.8" y="160.5"></rect><text fill="#4b6072" font-size="13" text-anchor="middle" x="735.0" y="176.5">body / status</text><path d="M930 130L930 235" fill="none" marker-end="url(#arrow-18860)" stroke="#667b8d" stroke-width="2"></path><rect fill="white" height="22" rx="3" width="61.199999999999996" x="899.4" y="160.5"></rect><text fill="#4b6072" font-size="13" text-anchor="middle" x="930.0" y="176.5">exception</text><path d="M810 285L660 285" fill="none" marker-end="url(#arrow-18860)" stroke="#667b8d" stroke-width="2"></path><rect fill="white" height="22" rx="3" width="81.6" x="694.2" y="263.0"></rect><text fill="#4b6072" font-size="13" text-anchor="middle" x="735.0" y="279.0">nếu chưa gửi</text><path d="M420 285L270 285" fill="none" marker-end="url(#arrow-18860)" stroke="#667b8d" stroke-width="2"></path><rect fill="white" height="22" rx="3" width="74.8" x="307.6" y="263.0"></rect><text fill="#4b6072" font-size="13" text-anchor="middle" x="345.0" y="279.0">mọi kết quả</text><path d="M420 80L270 285" fill="none" marker-end="url(#arrow-18860)" stroke="#667b8d" stroke-width="2"></path><rect fill="white" height="22" rx="3" width="68.0" x="311.0" y="160.5"></rect><text fill="#4b6072" font-size="13" text-anchor="middle" x="345.0" y="176.5">bị từ chối</text><rect fill="#e4f3f0" height="100" rx="10" stroke="#218777" stroke-width="1.8" width="240" x="30" y="30"></rect><text fill="#254154" font-size="17" font-weight="600" text-anchor="middle" x="150" y="58">Request context</text><text fill="#254154" font-size="13.5" font-weight="400" text-anchor="middle" x="150" y="84">ID server + mốc monotonic</text><text fill="#254154" font-size="13.5" font-weight="400" text-anchor="middle" x="150" y="105">Method / route đã nhận diện</text><rect fill="#e4f3f0" height="100" rx="10" stroke="#218777" stroke-width="1.8" width="240" x="420" y="30"></rect><text fill="#254154" font-size="17" font-weight="600" text-anchor="middle" x="540" y="58">Biên + admission thô</text><text fill="#254154" font-size="13.5" font-weight="400" text-anchor="middle" x="540" y="84">Framing / body budget</text><text fill="#254154" font-size="13.5" font-weight="400" text-anchor="middle" x="540" y="105">Chưa biết identity trong JSON</text><rect fill="#edf2f6" height="100" rx="10" stroke="#59748a" stroke-width="1.8" width="240" x="810" y="30"></rect><text fill="#254154" font-size="17" font-weight="600" text-anchor="middle" x="930" y="58">Module / tác vụ</text><text fill="#254154" font-size="13.5" font-weight="400" text-anchor="middle" x="930" y="84">Parse một lần → auth/quyền</text><text fill="#254154" font-size="13.5" font-weight="400" text-anchor="middle" x="930" y="105">Business flow hiện tại</text><rect fill="#e4f3f0" height="100" rx="10" stroke="#218777" stroke-width="1.8" width="240" x="30" y="235"></rect><text fill="#254154" font-size="17" font-weight="600" text-anchor="middle" x="150" y="263">Finalize trong finally</text><text fill="#254154" font-size="13.5" font-weight="400" text-anchor="middle" x="150" y="289">Timing / outcome</text><text fill="#254154" font-size="13.5" font-weight="400" text-anchor="middle" x="150" y="310">Release đúng lease đã giữ</text><rect fill="#e4f3f0" height="100" rx="10" stroke="#218777" stroke-width="1.8" width="240" x="420" y="235"></rect><text fill="#254154" font-size="17" font-weight="600" text-anchor="middle" x="540" y="263">Response một lần</text><text fill="#254154" font-size="13.5" font-weight="400" text-anchor="middle" x="540" y="289">Serialize trước headers</text><text fill="#254154" font-size="13.5" font-weight="400" text-anchor="middle" x="540" y="310">Status / write / disconnect</text><rect fill="#fff1df" height="100" rx="10" stroke="#b07d37" stroke-width="1.8" width="240" x="810" y="235"></rect><text fill="#254154" font-size="17" font-weight="600" text-anchor="middle" x="930" y="263">Exception tại biên</text><text fill="#254154" font-size="13.5" font-weight="400" text-anchor="middle" x="930" y="289">Chưa headers: lỗi phù hợp</text><text fill="#254154" font-size="13.5" font-weight="400" text-anchor="middle" x="930" y="310">Đã headers: đóng, không gửi lại</text></svg>
```

Đề xuất. Lỗi parser trước do_GET/do_POST cần hook phù hợp; wrapper do_POST không mặc nhiên thấy mọi request.

## Trạng thái response

| Trạng thái | Cho phép | Không được làm |
| --- | --- | --- |
| Nhận request | Tạo ID/context theo request | Global identity hoặc tin ID client thô |
| Chuẩn bị/serialize | Flow + encode JSON trước headers | Mở transaction bao chờ máy hoặc đọc lại body |
| Headers started | Ghi lỗi/đóng nếu write không hoàn tất | Response JSON lỗi thứ hai |
| Done/disconnected | Finalize và release chính xác | Coi disconnect là rollback máy |

## Tác vụ lifecycle G1

<a id="L01"></a>

### L01 · Context và thời gian theo request

Đặc tả triển khai và yêu cầu team được chuyển tới [phase con chứa tác vụ](phases/lifecycle/context-design.md#L01). Trang này giữ nghiên cứu chuyên đề; kế hoạch thực thi có hai cấp phase lớn/phase con.

<a id="L02"></a>

### L02 · Trạng thái response và serialize

Đặc tả triển khai và yêu cầu team được chuyển tới [phase con chứa tác vụ](phases/lifecycle/response-boundary.md#L02). Trang này giữ nghiên cứu chuyên đề; kế hoạch thực thi có hai cấp phase lớn/phase con.

<a id="L03"></a>

### L03 · Biên exception GET/POST

Đặc tả triển khai và yêu cầu team được chuyển tới [phase con chứa tác vụ](phases/lifecycle/response-boundary.md#L03). Trang này giữ nghiên cứu chuyên đề; kế hoạch thực thi có hai cấp phase lớn/phase con.

<a id="L04"></a>

### L04 · Route, query và method

Đặc tả triển khai và yêu cầu team được chuyển tới [phase con chứa tác vụ](phases/lifecycle/dispatch-correlation.md#L04). Trang này giữ nghiên cứu chuyên đề; kế hoạch thực thi có hai cấp phase lớn/phase con.

## Tác vụ biên HTTP G2

<a id="H01"></a>

### H01 · Framing được chấp nhận

Đặc tả triển khai và yêu cầu team được chuyển tới [phase con chứa tác vụ](phases/http-boundary/framing-policy.md#H01). Trang này giữ nghiên cứu chuyên đề; kế hoạch thực thi có hai cấp phase lớn/phase con.

<a id="H02"></a>

### H02 · Đọc đủ byte và parse một lần

Đặc tả triển khai và yêu cầu team được chuyển tới [phase con chứa tác vụ](phases/http-boundary/body-integrity.md#H02). Trang này giữ nghiên cứu chuyên đề; kế hoạch thực thi có hai cấp phase lớn/phase con.

<a id="H03"></a>

### H03 · Deadline đọc và reject sớm

Đặc tả triển khai và yêu cầu team được chuyển tới [phase con chứa tác vụ](phases/http-boundary/read-deadline.md#H03). Trang này giữ nghiên cứu chuyên đề; kế hoạch thực thi có hai cấp phase lớn/phase con.

<a id="H04"></a>

### H04 · Media type và response headers

Đặc tả triển khai và yêu cầu team được chuyển tới [phase con chứa tác vụ](phases/http-boundary/client-compatibility.md#H04). Trang này giữ nghiên cứu chuyên đề; kế hoạch thực thi có hai cấp phase lớn/phase con.
