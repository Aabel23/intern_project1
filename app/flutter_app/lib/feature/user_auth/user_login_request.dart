import 'package:simple_app/config/routing.dart';

import 'package:simple_app/core/http_json.dart';

// Đăng nhập một bước: gửi username/password tới /app/user/session/login, server
// kiểm rồi trả token ngay trong cùng response.
Future<Map<String, dynamic>> requestLogin(
  String serverUrl, {
  required String username,
  required String password,
}) {
  return postJson(serverUrl, Routes.userSessionLogin, {
    'username': username,
    'password': password,
  });
}
