// Định dạng nội dung QR giữa app và máy.
// Hiện là JSON thô; sau này mã hóa/giải mã tập trung tại file này,
// nơi tạo và nơi quét QR không phải sửa.
import 'dart:convert';

// Nội dung QR chủ máy hiện để nhân viên quét nhận quản lý máy.
String encodeShareQr(String code) =>
    jsonEncode({'type': 'share', 'code': code});

// Hai loại QR: tem trên máy (pairing) và mã chủ máy chia sẻ cho nhân viên (share).
Map<String, String> parseMachineQr(String raw) {
  // QR chứa JSON như gói Bluetooth, không chứa URL server.
  if (utf8.encode(raw).length > 4096) {
    throw const FormatException('QR quá lớn.');
  }
  final data = jsonDecode(raw);
  if (data is Map<String, dynamic> && data['type'] == 'share') {
    final code = data['code'];
    if (code is! String || code.length < 20 || code.length > 100) {
      throw const FormatException('QR chia sẻ thiếu mã hợp lệ.');
    }
    return {'type': 'share', 'code': code};
  }
  if (data is! Map<String, dynamic> || data['type'] != 'pairing') {
    throw const FormatException('Đây không phải QR pairing của máy.');
  }
  final name = data['machine_name'];
  final key = data['product_key'];
  if (name is! String ||
      name.trim().isEmpty ||
      name.length > 150 ||
      key is! String ||
      key.trim().isEmpty ||
      key.length > 1024) {
    throw const FormatException('QR thiếu tên máy hoặc product key hợp lệ.');
  }
  return {'type': 'pairing', 'machine_name': name, 'product_key': key};
}
