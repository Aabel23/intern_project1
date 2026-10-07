> Hồ sơ nội bộ cho agent. Chuyển từ tài liệu HTML ngày 06/10/2026; nội dung và bằng chứng cũ được giữ, chưa kiểm lại sản phẩm. Sơ đồ gốc giữ dưới dạng mã SVG trong khối XML.

KẾ HOẠCH PHÁT TRIỂN / 05.10.2026

# Sức chứa, timeout và độ tin cậy

Giới hạn tải phải cho hệ thống tiến triển: app chờ không chặn heartbeat/result cần để hoàn tất chính request đó.

Tài liệu thiết kế và kế hoạch · Offline / In đượcTrang này là nghiên cứu chuyên đề. Kế hoạch thực thi chính thức đi theo phase lớn → phase con; xem [bản đồ chương trình](index.md). Task chi tiết đã chuyển tới phase con liên kết bên dưới.

## Admission và fairness

Hiện trạngĐề xuấtKho dữ liệuLỗi / điều kiện cần chốt

Hai tầng sức chứa và đường hoàn tất command

```xml
<svg aria-label="Hai tầng sức chứa và đường hoàn tất command" role="img" viewbox="0 0 1080 365" xmlns="http://www.w3.org/2000/svg"><title>Hai tầng sức chứa và đường hoàn tất command</title><defs><marker id="arrow-43568" markerheight="7" markerwidth="7" orient="auto" refx="9" refy="5" viewbox="0 0 10 10"><path d="M0 0L10 5L0 10z" fill="#667b8d"></path></marker></defs><path d="M270 80L420 80" fill="none" marker-end="url(#arrow-43568)" stroke="#667b8d" stroke-width="2"></path><rect fill="white" height="22" rx="3" width="50" x="320.0" y="58.0"></rect><text fill="#4b6072" font-size="13" text-anchor="middle" x="345.0" y="74.0">bounded</text><path d="M660 80L810 80" fill="none" marker-end="url(#arrow-43568)" stroke="#667b8d" stroke-width="2"></path><rect fill="white" height="22" rx="3" width="88.39999999999999" x="690.8" y="58.0"></rect><text fill="#4b6072" font-size="13" text-anchor="middle" x="735.0" y="74.0">đọc đúng body</text><path d="M810 80L270 285" fill="none" marker-end="url(#arrow-43568)" stroke="#667b8d" stroke-width="2"></path><rect fill="white" height="22" rx="3" width="68.0" x="506.0" y="160.5"></rect><text fill="#4b6072" font-size="13" text-anchor="middle" x="540.0" y="176.5">app hợp lệ</text><path d="M810 80L660 285" fill="none" marker-end="url(#arrow-43568)" stroke="#667b8d" stroke-width="2"></path><rect fill="white" height="22" rx="3" width="68.0" x="701.0" y="160.5"></rect><text fill="#4b6072" font-size="13" text-anchor="middle" x="735.0" y="176.5">máy hợp lệ</text><path d="M930 130L930 235" fill="none" marker-end="url(#arrow-43568)" stroke="#667b8d" stroke-width="2"></path><rect fill="white" height="22" rx="3" width="68.0" x="896.0" y="160.5"></rect><text fill="#4b6072" font-size="13" text-anchor="middle" x="930.0" y="176.5">máy hợp lệ</text><rect fill="#e4f3f0" height="100" rx="10" stroke="#218777" stroke-width="1.8" width="240" x="30" y="30"></rect><text fill="#254154" font-size="17" font-weight="600" text-anchor="middle" x="150" y="58">Kết nối chưa auth</text><text fill="#254154" font-size="13.5" font-weight="400" text-anchor="middle" x="150" y="84">Hard cap connection/thread</text><text fill="#254154" font-size="13.5" font-weight="400" text-anchor="middle" x="150" y="105">Deadline header/body</text><rect fill="#e4f3f0" height="100" rx="10" stroke="#218777" stroke-width="1.8" width="240" x="420" y="30"></rect><text fill="#254154" font-size="17" font-weight="600" text-anchor="middle" x="540" y="58">Admission thô + parse</text><text fill="#254154" font-size="13.5" font-weight="400" text-anchor="middle" x="540" y="84">Route chỉ phân loại</text><text fill="#254154" font-size="13.5" font-weight="400" text-anchor="middle" x="540" y="105">URL máy chưa là máy thật</text><rect fill="#edf2f6" height="100" rx="10" stroke="#59748a" stroke-width="1.8" width="240" x="810" y="30"></rect><text fill="#254154" font-size="17" font-weight="600" text-anchor="middle" x="930" y="58">Xác minh identity</text><text fill="#254154" font-size="13.5" font-weight="400" text-anchor="middle" x="930" y="84">Token / product_key</text><text fill="#254154" font-size="13.5" font-weight="400" text-anchor="middle" x="930" y="105">Quota sau xác thực</text><rect fill="#e4f3f0" height="100" rx="10" stroke="#218777" stroke-width="1.8" width="240" x="30" y="235"></rect><text fill="#254154" font-size="17" font-weight="600" text-anchor="middle" x="150" y="263">App chờ command</text><text fill="#254154" font-size="13.5" font-weight="400" text-anchor="middle" x="150" y="289">Sức chứa app riêng</text><text fill="#254154" font-size="13.5" font-weight="400" text-anchor="middle" x="150" y="310">Bound queue mỗi máy</text><rect fill="#e4f3f0" height="100" rx="10" stroke="#218777" stroke-width="1.8" width="240" x="420" y="235"></rect><text fill="#254154" font-size="17" font-weight="600" text-anchor="middle" x="540" y="263">Máy poll</text><text fill="#254154" font-size="13.5" font-weight="400" text-anchor="middle" x="540" y="289">Sức chứa poll riêng</text><text fill="#254154" font-size="13.5" font-weight="400" text-anchor="middle" x="540" y="310">Chờ 8s hiện tại</text><rect fill="#e4f3f0" height="100" rx="10" stroke="#218777" stroke-width="1.8" width="240" x="810" y="235"></rect><text fill="#254154" font-size="17" font-weight="600" text-anchor="middle" x="930" y="263">Heartbeat / result</text><text fill="#254154" font-size="13.5" font-weight="400" text-anchor="middle" x="930" y="289">Budget để hoàn tất lệnh</text><text fill="#254154" font-size="13.5" font-weight="400" text-anchor="middle" x="930" y="310">Auth vẫn bắt buộc</text></svg>
```

Đề xuất chưa chọn ngưỡng. Hard cap đầy trước handler thì không biết token trong JSON: cần ingress budget đủ, giới hạn body/deadline và kiểm máy giả; reserve handler không tự bảo đảm DDoS availability.

Semaphore trong do_POST không phải thread cap vì thread đã được tạo. Ưu tiên theo URL máy chưa xác thực có thể bị giả; phải tách trần ingress và quota danh tính.

## Ngân sách thời gian hiện tại

| Khối | Giá trị code | Hệ quả |
| --- | --- | --- |
| Handler socket | 10s | Idle I/O, không tổng deadline |
| Máy urlopen | 10s | Poll 8s còn budget I/O/queue hẹp, phải đo |
| App request | 25s tổng, connect 5s | Command 20s không được cộng hàng đợi dài |
| Heartbeat TTL | 15s | Admission chậm có thể báo offline sai |
| Command wait | 20s | Timeout không nói máy chưa thực thi |
| Poll | 8s | Slot chờ cần tách khỏi result/heartbeat |

## Tác vụ chặng G3

<a id="C01"></a>

### C01 · Bound kết nối trước tạo thread

Đặc tả triển khai và yêu cầu team được chuyển tới [phase con chứa tác vụ](phases/capacity/ingress-bound.md#C01). Trang này giữ nghiên cứu chuyên đề; kế hoạch thực thi có hai cấp phase lớn/phase con.

<a id="C02"></a>

### C02 · Tách sức chứa các nhóm công việc

Đặc tả triển khai và yêu cầu team được chuyển tới [phase con chứa tác vụ](phases/capacity/workload-lanes.md#C02). Trang này giữ nghiên cứu chuyên đề; kế hoạch thực thi có hai cấp phase lớn/phase con.

<a id="C03"></a>

### C03 · Bound command queue theo máy và tổng

Đặc tả triển khai và yêu cầu team được chuyển tới [phase con chứa tác vụ](phases/capacity/queue-invariants.md#C03). Trang này giữ nghiên cứu chuyên đề; kế hoạch thực thi có hai cấp phase lớn/phase con.

<a id="C04"></a>

### C04 · Deadline tổng và hủy đúng nghĩa

Đặc tả triển khai và yêu cầu team được chuyển tới [phase con chứa tác vụ](phases/capacity/budgets-recovery.md#C04). Trang này giữ nghiên cứu chuyên đề; kế hoạch thực thi có hai cấp phase lớn/phase con.

<a id="C05"></a>

### C05 · Bão hòa rồi phục hồi

Đặc tả triển khai và yêu cầu team được chuyển tới [phase con chứa tác vụ](phases/capacity/budgets-recovery.md#C05). Trang này giữ nghiên cứu chuyên đề; kế hoạch thực thi có hai cấp phase lớn/phase con.
