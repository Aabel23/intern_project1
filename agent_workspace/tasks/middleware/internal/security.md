> Hồ sơ nội bộ cho agent. Chuyển từ tài liệu HTML ngày 06/10/2026; nội dung và bằng chứng cũ được giữ, chưa kiểm lại sản phẩm. Sơ đồ gốc giữ dưới dạng mã SVG trong khối XML.

KẾ HOẠCH PHÁT TRIỂN / 05.10.2026

# Danh tính, quyền và chính sách request

Gom cơ chế có chọn lọc; role nghiệp vụ và transaction vẫn ở tác vụ.

Tài liệu thiết kế và kế hoạch · Offline / In đượcTrang này là nghiên cứu chuyên đề. Kế hoạch thực thi chính thức đi theo phase lớn → phase con; xem [bản đồ chương trình](index.md). Task chi tiết đã chuyển tới phase con liên kết bên dưới.

## Luồng xác thực

Hiện trạngĐề xuấtKho dữ liệuLỗi / điều kiện cần chốt

Danh tính trước quyền nghiệp vụ và quota

```xml
<svg aria-label="Danh tính trước quyền nghiệp vụ và quota" role="img" viewbox="0 0 1080 365" xmlns="http://www.w3.org/2000/svg"><title>Danh tính trước quyền nghiệp vụ và quota</title><defs><marker id="arrow-35500" markerheight="7" markerwidth="7" orient="auto" refx="9" refy="5" viewbox="0 0 10 10"><path d="M0 0L10 5L0 10z" fill="#667b8d"></path></marker></defs><path d="M270 80L420 80" fill="none" marker-end="url(#arrow-35500)" stroke="#667b8d" stroke-width="2"></path><rect fill="white" height="22" rx="3" width="61.199999999999996" x="314.4" y="58.0"></rect><text fill="#4b6072" font-size="13" text-anchor="middle" x="345.0" y="74.0">route app</text><path d="M270 80L270 160L810 160L810 80" fill="none" marker-end="url(#arrow-35500)" stroke="#667b8d" stroke-width="2"></path><rect fill="white" height="22" rx="3" width="61.199999999999996" x="509.4" y="139"></rect><text fill="#4b6072" font-size="13" text-anchor="middle" x="540.0" y="155">route máy</text><path d="M150 130L150 235" fill="none" marker-end="url(#arrow-35500)" stroke="#667b8d" stroke-width="2"></path><rect fill="white" height="22" rx="3" width="74.8" x="112.6" y="160.5"></rect><text fill="#4b6072" font-size="13" text-anchor="middle" x="150.0" y="176.5">login / OTP</text><path d="M540 130L540 235" fill="none" marker-end="url(#arrow-35500)" stroke="#667b8d" stroke-width="2"></path><rect fill="white" height="22" rx="3" width="50" x="515.0" y="160.5"></rect><text fill="#4b6072" font-size="13" text-anchor="middle" x="540.0" y="176.5">user_id</text><path d="M930 130L930 235" fill="none" marker-end="url(#arrow-35500)" stroke="#667b8d" stroke-width="2"></path><rect fill="white" height="22" rx="3" width="68.0" x="896.0" y="160.5"></rect><text fill="#4b6072" font-size="13" text-anchor="middle" x="930.0" y="176.5">machine_id</text><rect fill="#edf2f6" height="100" rx="10" stroke="#59748a" stroke-width="1.8" width="240" x="30" y="30"></rect><text fill="#254154" font-size="17" font-weight="600" text-anchor="middle" x="150" y="58">Method / route</text><text fill="#254154" font-size="13.5" font-weight="400" text-anchor="middle" x="150" y="84">Public / app / máy</text><text fill="#254154" font-size="13.5" font-weight="400" text-anchor="middle" x="150" y="105">GET status hiện công khai</text><rect fill="#edf2f6" height="100" rx="10" stroke="#59748a" stroke-width="1.8" width="240" x="420" y="30"></rect><text fill="#254154" font-size="17" font-weight="600" text-anchor="middle" x="540" y="58">Phiên app</text><text fill="#254154" font-size="13.5" font-weight="400" text-anchor="middle" x="540" y="84">Token hash → SQLite</text><text fill="#254154" font-size="13.5" font-weight="400" text-anchor="middle" x="540" y="105">TTL / logout</text><rect fill="#edf2f6" height="100" rx="10" stroke="#59748a" stroke-width="1.8" width="240" x="810" y="30"></rect><text fill="#254154" font-size="17" font-weight="600" text-anchor="middle" x="930" y="58">Danh tính máy</text><text fill="#254154" font-size="13.5" font-weight="400" text-anchor="middle" x="930" y="84">Product key hash → ID</text><text fill="#254154" font-size="13.5" font-weight="400" text-anchor="middle" x="930" y="105">Không phải token app</text><rect fill="#edf2f6" height="100" rx="10" stroke="#59748a" stroke-width="1.8" width="240" x="30" y="235"></rect><text fill="#254154" font-size="17" font-weight="600" text-anchor="middle" x="150" y="263">Public auth</text><text fill="#254154" font-size="13.5" font-weight="400" text-anchor="middle" x="150" y="289">Limit IP login/OTP</text><text fill="#254154" font-size="13.5" font-weight="400" text-anchor="middle" x="150" y="310">Logout được miễn</text><rect fill="#edf2f6" height="100" rx="10" stroke="#59748a" stroke-width="1.8" width="240" x="420" y="235"></rect><text fill="#254154" font-size="17" font-weight="600" text-anchor="middle" x="540" y="263">Quyền trong tác vụ</text><text fill="#254154" font-size="13.5" font-weight="400" text-anchor="middle" x="540" y="289">Role theo action</text><text fill="#254154" font-size="13.5" font-weight="400" text-anchor="middle" x="540" y="310">Cùng transaction khi cần</text><rect fill="#e4f3f0" height="100" rx="10" stroke="#218777" stroke-width="1.8" width="240" x="810" y="235"></rect><text fill="#254154" font-size="17" font-weight="600" text-anchor="middle" x="930" y="263">Quota sau auth</text><text fill="#254154" font-size="13.5" font-weight="400" text-anchor="middle" x="930" y="289">User/machine đã xác minh</text><text fill="#254154" font-size="13.5" font-weight="400" text-anchor="middle" x="930" y="310">Không raw key làm nhãn</text></svg>
```

Cơ chế phiên/quyền/máy hiện tại; quota là đề xuất. GET /app/machine/status/get do app gọi và đang công khai; siết quyền là thay contract cần caller/test.

## Ma trận chính sách

| Nhóm | Hiện tại | Đề xuất / ranh giới |
| --- | --- | --- |
| Login/register/OTP | Public, limited IP | Chống hash/SMTP spam; per-route nếu measurements cần |
| Logout | Xóa token hash, miễn limiter login | Không flood cùng NAT cản logout |
| Register/share/list máy | App token, valid/message | Giữ role và status task |
| Menu/Kho | Token+machine_id, loi/login_required | Giữ 401/403 flow; không đổi status account toàn bộ |
| Heartbeat/poll/result | Product key, loi | Quota per-machine sau auth, không limit tất cả NAT |
| GET trạng thái | Query machine_id, chưa auth | Nếu đổi: app/server/tests cùng contract, token không đưa URL |

## Tác vụ chặng G4

<a id="S01"></a>

### S01 · Ma trận route/auth và policy metadata

Đặc tả triển khai và yêu cầu team được chuyển tới [phase con chứa tác vụ](phases/identity/route-policy.md#S01). Trang này giữ nghiên cứu chuyên đề; kế hoạch thực thi có hai cấp phase lớn/phase con.

<a id="S02"></a>

### S02 · Phiên thu hồi và nhu cầu gom auth

Đặc tả triển khai và yêu cầu team được chuyển tới [phase con chứa tác vụ](phases/identity/session-revocation.md#S02). Trang này giữ nghiên cứu chuyên đề; kế hoạch thực thi có hai cấp phase lớn/phase con.

<a id="S03"></a>

### S03 · Limiter với NAT và bảng đầy

Đặc tả triển khai và yêu cầu team được chuyển tới [phase con chứa tác vụ](phases/identity/limiter-threat-model.md#S03). Trang này giữ nghiên cứu chuyên đề; kế hoạch thực thi có hai cấp phase lớn/phase con.

<a id="S04"></a>

### S04 · Quyền GET status và device threat model

Đặc tả triển khai và yêu cầu team được chuyển tới [phase con chứa tác vụ](phases/identity/authorization-transaction.md#S04). Trang này giữ nghiên cứu chuyên đề; kế hoạch thực thi có hai cấp phase lớn/phase con.

<a id="S05"></a>

### S05 · Threat model và log sạch secret

Đặc tả triển khai và yêu cầu team được chuyển tới [phase con chứa tác vụ](phases/identity/limiter-threat-model.md#S05). Trang này giữ nghiên cứu chuyên đề; kế hoạch thực thi có hai cấp phase lớn/phase con.
