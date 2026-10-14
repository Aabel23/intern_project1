# I-01 · Nghiệm thu skeleton trên Android, Pi, server và Gmail thật

**Trạng thái:** chờ S-01..S-03, M-01..M-03, A-01..A-03 qua review nhỏ và cổng crypto. Tester/Operator; không sửa code sản phẩm.

## Input, file và quyền

Đọc contracts/**, từng phiếu coder và assignments.md. Tạo `tests/integration/skeleton_acceptance.py` với hàm `register_email`, `send_otp`, `verify_otp`, `login`, `claim_machine`, `ask_status`, `cleanup_test_rows`, và `documentation/plan/skeleton-acceptance.md` biên bản. Không tool tự đọc mailbox: OTP nhận từ user và chỉ nhập RAM/stdin ẩn, không argv/env/file/log; không SMTP App Password trong test. Không thêm dependency ngoài client crypto chuẩn đã được coder triển khai. Factory registration chỉ Operator với serial thật và bí mật provision; tester không sửa routing/schema/identity.

## Trước khi chạy

1. Chốt các phiếu READY và kiểm phiên bản cùng contracts/v1. Backup DB thử và ghi thời gian/run_id UUID; chọn server test một instance, HTTPS và HPKE thật, Gmail chủ dự án, To allowlist hai địa chỉ dưới đây. Không mock ở nghiệm thu.
2. Xác minh hai email chưa có tài khoản user thật; nếu đã có bản ghi không do run thử này tạo ra thì **dừng email đó, báo Operator**, không đổi password/xóa để chạy thử. Xác minh máy thử CPU serial/model/key fingerprint; ghi machine_id nếu có; owner phải null. Nếu máy có chủ ngoài thử, dừng; không gỡ máy/reset hộ.
3. Ghi manifest test chỉ id/timestamp/type: user ids, otp generation ids, session ids, access token row ids, claim ids, test device id (mới tạo hay đã tồn tại), owner id trước thử. Không OTP/password/token/private key/verifier/mã QR trong manifest. Không đánh dấu mọi hàng cùng email là được phép xóa nếu không do run này tạo.

## Gửi và xác minh mail thật

4. Qua API sản phẩm USER_ACCOUNT_REGISTER tới `nguyenhoanganh15112005@gmail.com` với password thử do user/Operator chọn không ghi file. Kiểm CHECK_EMAIL; tự kích hoạt gửi SMTP bằng luồng register, không gửi bằng script SMTP rời để thay nghiệm thu. Chờ user báo OTP của đúng email đó; nhập RAM rồi USER_OTP_VERIFY. Ghi thư đã đến/verify đạt, không ghi OTP. Nếu Gmail fail kiểm log nội bộ MAIL_AUTH/MAIL_SEND, API CHECK_EMAIL và dừng nhánh thành công, không fake mã.
5. USER_SESSION_LOGIN email này, xác minh phiên access 1h/refresh 30 ngày metadata; OTP cũ thử lại không tạo phiên; unverified login ca riêng trước verify. Thử USER_OTP_SEND theo thời hạn thực để thư gửi lại đúng To và mã trước vô hiệu; nếu gửi lại, user cung cấp mã mới, giữ tài khoản cho ca nhận máy.
6. Lặp register→mail thật→user OTP→verify→login cho `23200002@student.hcmus.edu.vn`. Không CC/BCC/copy OTP người khác tới hai địa chỉ. Chỉ bắt đầu xác minh sau user đưa mã đúng lượt; hết thời gian không thay cho mã. Ghi kết quả từng email riêng.

## Nhận máy và kết nối thật

7. Trên Android account thứ nhất, quét QR niêm phong của máy thật; sai mã thử phải không gửi wifi/không bind owner. QR đúng mở kênh BT được bảo vệ, gửi wifi, máy lên server kiểm mã và bind public key tự sinh. Ghi fingerprint/id, không QR raw. Begin claim→máy ký bằng chứng tại chỗ→complete; list đúng máy với role owner. Không nạp account/máy mẫu cho đạt.
8. Account thứ hai thử nhận cùng máy, kể cả đồng thời complete test có kiểm soát: chỉ account thứ nhất owner, account thứ hai ALREADY_OWNED; không đọc status máy không thuộc mình. Proof đổi account/serial/nonce/hạn/phiên BT bị từ chối bằng ca tích hợp API nếu hợp đồng có fixture tạo bằng chứng xấu; không thay code để chạy ca. Restart máy giữ serial/key; local reset không xóa owner DB. Không thực hiện bán lại/gỡ máy trong skeleton.
9. Android chọn máy→Làm mới: quan sát request_id Q xuyên app/server/poll/result; machine handler read_sequence thay đổi sau mỗi Q mới; nguồn machine, received_at server, uptime đọc mới. Logs dùng ID/fingerprint/result không bí mật. Server online từ poll không được dùng thay kết quả trực tiếp. Đối chiếu app UI với máy/server trace đã lọc.
10. Ngắt mạng máy trước hỏi→MACHINE_OFFLINE trong ngưỡng; ngắt sau server nhận Q→timeout hữu hạn và không stale success. Kết quả Q cũ/late/duplicate/wrong machine không gắn Q mới. Chọn máy khác/đăng xuất lúc pending không hiển thị response cũ. Reconnect→Q mới đọc thật. Restart server lúc pending→mất connection/REQUEST_GONE khi retry, không claim đọc đã thành công. Ghi thời gian timeout thực theo cấu hình.
11. Logout→access/refresh cũ không dùng được. Kiểm Android restart storage/session đúng hợp đồng; không đưa bí mật vào report. Nếu test fail ghi vấn đề/bằng chứng và trả Operator bàn, không tự sửa code.

## Dọn đúng dữ liệu sau khi các ca dùng chúng đạt

12. Chưa cleanup nếu còn ca cần account/owner. Sau đạt, ngắt app/máy/test writer; query read-only quan hệ toàn bộ IDs trong manifest, xác nhận ownership hàng và trước/sau. Chỉ user ids do hai email thử tạo trong run được phép xóa. Nếu có liên kết/user/máy ngoài manifest, rollback và báo Operator, không CASCADE mù.
13. Transaction: lock hai user rows/claim/device rows liên quan; kiểm user ids/email trùng manifest + created_at phạm vi run. Xóa access_tokens theo sessions manifest→sessions→otp_generations theo IDs→claim_challenges test; gỡ owner_user_id thử trên đúng device bằng điều kiện owner==test_user_id; xóa users test. Với device **đã đăng ký hãng từ trước**, giữ serial/verifier/public_key/key_id, chỉ dọn owner/claim do thử tạo; với device **chỉ tạo cho run thử**, chỉ xóa khi không còn reference ngoài manifest, đã được xác minh là thiết bị thử. Không xóa/seeding toàn DB. Verify số hàng affected trùng manifest rồi commit; sai số rollback.
14. Query lại IDs không còn hàng thử đã nêu; kiểm account/máy ngoài manifest không đổi. Máy vẫn giữ key/mã định danh: không xóa identity file hoặc factory code để 'dọn DB'. Biên bản nêu chính xác record IDs/counts được dọn, device nào giữ registry, thời điểm, ca đạt/chưa đạt; không copy OTP hay secret.

## Cách kiểm / output

Automation client chỉ gọi API thật để điều phối và ghi manifest; người dùng/Operator cung cấp OTP và thao tác thiết bị thật. Kiểm unit timing 1h/30 ngày bằng S-01 clock injection, I-01 không chờ 30 ngày hoặc đổi production clock. Biên bản phải phân biệt ca thật, ca unit, ca chưa chạy; không ký nghiệm thu nếu SMTP/Bluetooth/machine proof/relay thật chưa đủ. Mốc đạt = cả hai thư thật + login + owner thật duy nhất + status máy thật + offline/timeout + cleanup đúng scope. Không triển khai feature ngoài skeleton hoặc tổng review module thay user.
