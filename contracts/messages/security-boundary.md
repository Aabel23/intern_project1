# Cổng C-05 và trạng thái phiếu

## Quyết định hiện tại

User ngày12/10/2026 chốt serial+verifier niêm phong đăng ký trước bán, máy tự sinh khóa bật đầu, kiểm mã trước bind; không khóa/chứng chỉ xưởng, không PAKE mã dài. User chốt giữ **TLS + phong bì mã hóa trong ngay skeleton** theo cryptography.html; không TLS-only. `cloud-protection.md` thay phần mTLS/chứng chỉ xưởng của HTML cũ bằng HTTPS + chữ ký ứng dụng máy bound. Server mở lớp trong từng chặng theo ranh giới HTML user vừa chọn. Không lấy nội dung cũ về một token30 ngày.

Planner chọn thông số kỹ thuật tại COMPATIBILITY; B-04 cũ đã đóng, không đòi user duyệt từng số. Cloud chọn BC Kotlin ↔ PyHPKE, P256 ký máy, HPKE exporter cho response, như API primary sources kiểm được. Build/vector và Android thật là cổng nghiệm thu implementation; lỗi thư viện phải báo Planner, không bỏ lớp trong.

## Cổng thật còn mở: BT nhận máy

B-03: User ngày12/10/2026 đã chốt **HPKE PSK + review phiên**, không Noise adapter. `bt-claim.md` khóa profile hello→probe→authenticated→app confirm→machine confirmed ACK trước Wi-Fi/claim, transcript/role/serial/session/nonces và context/exporter một lần. Đây vẫn là profile custom cần review độc lập, không được coi RFC9180/API PSK là chứng nhận toàn phiên. Research evidence từng thư viện đã có: PyHPKE0.6.5 official mode_psk enc+257ct+3 exports và BC1.86 recipient3ct+3 exports/API. Chưa gate complete. Cổng còn thiếu: BC sender↔PyHPKE interop/profile + exporter/AEAD, Android actual artifact/runtime, BLE Android+Pi thật, chốt Wi-Fi OS implementation M-01. M-01/S-02/A-02 giữ BLOCKED. Không tự fork/adapter crypto, PAKE/TLS-only hoặc mở READY khi chỉ có docs. Noise research là bằng chứng phương án đã bỏ, không còn là lựa chọn coder.

| Phiếu | Trạng thái phát | Phụ thuộc |
|---|---|---|
| S-01 | READY đặc tả, có thể giao coder | cloud-protection/auth/COMPATIBILITY; crypto vectors và SMTP thật là gate review/nghiệm thu |
| A-01 | READY đặc tả, có thể giao coder | S-01 API contract; BC Kotlin/secure storage implementation gates |
| M-01 | BLOCKED | BT cổng B-03 |
| S-02 | BLOCKED | BT local-session binding chứng minh được; S-01 review |
| A-02 | BLOCKED | BT cổng B-03; A-01 review |
| M-02 | WAIT DEPENDENCY | M-01 review, danh tính bound; wire cloud đã định nghĩa |
| S-03 | WAIT DEPENDENCY | S-02 review; wire cloud/relay đã định nghĩa |
| M-03 | WAIT DEPENDENCY | M-02 review; handler/fields đã xác định |
| A-03 | WAIT DEPENDENCY | A-02 review, S-03/M-03 |
| I-01 | WAIT DEPENDENCY | mọi slot qua review, BT thật, Android/Pi/Gmail thật |

C-05 còn chưa hoàn tất BT/claim. Các phiếu BLOCKED là tài liệu phân công dự kiến, không lệnh bắt đầu. Không gọi coder nhận máy bằng bảng slots chung. Không tự sửa app/server/máy trong C-05.
