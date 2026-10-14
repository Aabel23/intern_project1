# Review lớn module tài khoản · 12/10/2026

> **Cập nhật (hợp đồng v2):** finding 1 (quota login đồng thời) đã sửa bằng giữ chỗ nguyên tử, có test `test_concurrent_wrong_logins_never_exceed_limit`. Kèm theo: login email không tồn tại cùng chi phí Argon2, mật khẩu ≥15 ký tự, phát hiện refresh token dùng lại, hạn phiên tuyệt đối 90 ngày. Finding 2 (ô nhập lại mật khẩu) vẫn giữ nguyên theo quyết định user.

**Một lần review lớn sau review nhỏ S-01/A-01: đã thực hiện.** Hai task qua review nhỏ vòng 2; server 32 tests (gồm MySQL cô lập), app 20 Flutter tests, AndroidTest APK build. Đây chưa phải nghiệm thu Phase 1 trên Android thật.

## Findings và quyết định user

1. **Quota login đồng thời.** `server/src/account.py` kiểm số lần sai trước DB rồi ghi nhận sau DB trong critical section khác. Reviewer seed 9 lần sai cho một IP, cho 2 login sai chạy đồng thời: cả hai trả `AUTH_FAILED`, counter lên 11 dù ngưỡng 10/600s. Hướng sửa đề xuất: check và append failure nguyên tử; nếu muốn chặn cả password verification đồng thời cần Planner khóa admission theo IP. **User chốt ghi nhận, chưa sửa.**
2. **Ô xác nhận mật khẩu còn giá trị khi quay lại từ OTP.** `flutter_app/lib/feature/user_auth/ui/auth_page.dart` chỉ clear ô password; ô confirmation không có controller/reset nên còn mật khẩu cũ khi chọn “Sai email? Quay lại”. Hướng sửa đề xuất: clear/reset cả hai ô tại boundary và test widget. **User chốt ghi nhận, chưa sửa.**
3. **Lỗi nội bộ 500:** server có thể trả `INTERNAL_ERROR` đã mã hóa, app parser đổi thành `INVALID_RESPONSE`. **User chốt giữ hiện trạng**, không sửa mapping.

Review đối chiếu contracts/architect/phiếu/Phase1 thấy các luồng còn lại phù hợp phạm vi tài khoản skeleton; claim/relay/Bluetooth thuộc phase sau. Không tự kích hoạt code fix sau review lớn.

## Gate nghiệm thu còn mở

- Android instrumentation/Keystore/restore/restart và luồng app↔server thật chưa chạy; thiết bị có thể kết nối nhưng user chọn để sau.
- Runtime HTTPS domain/cert/server keys/public pins chưa có; asset app `{}` cố ý fail startup, không là pin thật.
- Gmail SMTP nhận OTP thật và MySQL production chưa kiểm. Chỉ test SMTP stub và DB test cô lập.

Hai finding đầu là lỗi có bằng chứng nhưng được user tạm chấp nhận, không được diễn giải là đã sửa hoặc đã qua nghiệm thu sản phẩm.
