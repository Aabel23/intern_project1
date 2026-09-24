import 'dart:math';

import 'registration_request.dart';

// Đăng nhập hai bước: gửi username/password tới /app/dang-nhap, rồi hỏi
// kết quả xác minh của server tại /app/xac-minh-dang-nhap.
Future<Map<String, dynamic>> requestLogin(
  String serverUrl, {
  required String username,
  required String password,
}) async {
  final random = Random.secure();
  final requestId = List.generate(
    16,
    (_) => random.nextInt(256).toRadixString(16).padLeft(2, '0'),
  ).join();
  final sent = await postRegistrationJson(serverUrl, '/app/dang-nhap', {
    'request_id': requestId,
    'username': username,
    'password': password,
  });
  if (sent['valid'] == false) return sent;
  return postRegistrationJson(serverUrl, '/app/xac-minh-dang-nhap', {
    'request_id': requestId,
    if (sent['login_id'] is String) 'login_id': sent['login_id'] as String,
  });
}
