// Địa chỉ server mặc định — đổi IP ở đây khi đổi Wi-Fi.
// Khi chuyển lên máy chủ riêng: 'http://100.127.250.88:8000' (Tailscale).
// --dart-define=SERVER_URL=... (test.ps1 dùng) vẫn được ưu tiên hơn giá trị này.
const String kDefaultServerUrl = 'http://192.168.1.158:8000';

const kServerUrl = String.fromEnvironment(
  'SERVER_URL',
  defaultValue: kDefaultServerUrl,
);
