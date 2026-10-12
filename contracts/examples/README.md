# Ví dụ skeleton

Các tên/file valid là payload nghiệp vụ sau giải mã, không body Internet/BT. Dữ liệu .invalid và EXAMPLE_ONLY là giả lập, không secret thật. OTP không có trong examples.

| File | Kỳ vọng |
|---|---|
| auth-register-valid.json | Định dạng register hợp lệ, CHECK_EMAIL |
| auth-login-success.json | Shape success; token placeholder không được dùng auth thật |
| auth-error-mail.json | 502 MAIL_UNAVAILABLE |
| claim-begin-valid.json | Chỉ begin; chưa có owner |
| claim-error-owned.json | 409 ALREADY_OWNED |
| relay-status-valid.json → relay-poll-valid.json → relay-result-valid.json → relay-response-valid.json | Cùng request_id/machine; source machine; server received_at |
| relay-error-timeout.json | 504; muộn không đổi lỗi |
| invalid-version.json | 400 UNSUPPORTED_VERSION, không handler |
| invalid-status-data.json | 400 INVALID_REQUEST ở server, không dispatch |

Không fixture claim proof/HPKE ciphertext trước chốt wire. Phiếu coder crypto phải tạo vector hợp lệ và hỏng có expected output độc lập, không tự round-trip rồi gọi tương thích.
