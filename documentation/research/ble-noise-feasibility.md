# Phiên Bluetooth nhận máy · kiểm chứng Noise (12/10/2026)

**Trạng thái: lưu nghiên cứu phương án Noise đã bỏ. User ngày12/10/2026 chốt HPKE PSK + review phiên, không Noise adapter. Không phát coder từ tài liệu này; profile hiện hành và gate ở `contracts/messages/bt-claim.md`.** Mục tiêu là bảo vệ Wi-Fi và bằng chứng nhận máy trong phiên Bluetooth đầu tiên khi mã niêm phong dài 32 byte nằm trên máy và QR.

## Kết quả đã chạy

- `noiseprotocol==0.3.1` Python và [`jchambers/java-noise` commit `4de5aef`](https://github.com/jchambers/java-noise/tree/4de5aefbf2bb19bf2efcfbe97d3d13231e693488) JVM chạy liên thông pattern `Noise_NNpsk0_25519_ChaChaPoly_SHA256` với PSK raw 32 byte. Java gửi M1/Python đọc, Python gửi M2/Java đọc; hai chiều transport giải được thông điệp và từ chối phát lại. Hai thư viện riêng đều khớp 6 ciphertext của vector Cacophony. Script thử nằm trong `/tmp/BleNoise.java`, `/tmp/ble-interop.py`, `/tmp/ble-vector.py` (tạm, không phải test sản phẩm).
- Theo [đặc tả Noise](https://noiseprotocol.org/noise.html#pre-shared-symmetric-keys), M1 có thể phát lại. Máy không được đổi Wi-Fi, ký claim hay lưu chủ ở M1. Cần app kiểm M2 rồi gửi xác nhận qua transport M3; máy chỉ cho hành động nhạy cảm sau khi giải và kiểm M3.

## Chặn Android

Thư viện Java này dùng `HexFormat` (Android API 34), `XECKey`/`NamedParameterSpec` (API 33) và JCA factory tên `X25519`, đồng thời yêu cầu public key kiểu `XECKey`. [AOSP Conscrypt Android 14](https://android.googlesource.com/platform/external/conscrypt/+/refs/heads/android14-release/common/src/main/java/org/conscrypt/OpenSSLProvider.java) đăng ký các factory dưới `XDH`; [public key](https://android.googlesource.com/platform/external/conscrypt/+/refs/heads/android14-release/common/src/main/java/org/conscrypt/OpenSSLX25519PublicKey.java) của nó không implement `XECKey`. Vì vậy không thể đưa nguyên trạng thư viện JVM vào app Android và coi là đã đạt. Chưa có Android device/emulator nối để chạy gate.

[`rweather/noise-java`](https://github.com/rweather/noise-java/blob/master/src/main/java/com/southernstorm/noise/protocol/HandshakeState.java) dùng prefix NoisePSK cũ, không phải cặp `NNpsk0` nguyên trạng với Python ở trên. Chưa có cặp Noise Android/Python đã kiểm liên thông và tương thích runtime mà không fork/adapter crypto.

## Việc phải quyết trước code nhận máy

1. Đánh giá adapter/provider hoặc thư viện khác bằng spike Android riêng; hoặc kiểm khả năng HPKE PSK hiện có trong hợp đồng, kèm xác nhận khóa và chống replay đầy đủ. Không tự ghép AES/HMAC thành phiên bảo vệ.
2. Chốt protocol cùng thứ tự M1/M2/M3, prologue/nonce/session binding và framing Bluetooth dựa trên kết quả Android thật.
3. Khi đủ bằng chứng, Architect/Planner cập nhật `contracts/messages/bt-claim.md` rồi mới mở cổng M-01/A-02/S-02. Hiện máy là SPP JSON newline/product_key, hợp đồng đề xuất BLE GATT; phần transport này cũng phải được nghiệm thu trên thiết bị thật.
