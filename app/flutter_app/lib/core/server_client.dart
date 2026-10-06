import 'dart:convert';
import 'dart:io';

// Lỗi đọc được cho người dùng: URL sai, server báo lỗi hoặc máy trả "loi".
class ApiException implements Exception {
  const ApiException(this.message);
  final String message;

  @override
  String toString() => message;
}

// Server báo phiên đăng nhập hết hạn hoặc đã đăng xuất (login_required).
class LoginRequiredException extends ApiException {
  const LoginRequiredException(super.message);
}

// Gọi server theo đúng giao thức hiện có: app gửi lệnh, server chuyển cho máy.
class ServerClient {
  ServerClient(this.serverUrl, {this.token, this.onLoginRequired});
  final String serverUrl;

  // Token phiên đăng nhập; server dùng để biết ai là chủ/nhân viên của máy.
  final String? token;

  // Dashboard truyền vào để quay về màn hình đăng nhập khi token hết hạn.
  final void Function()? onLoginRequired;

  Future<Map<String, dynamic>> account(
    String path,
    Map<String, dynamic> body,
  ) async {
    final result = await request(
      'POST',
      path,
      body: {...body, 'token': ?token},
    );
    if (result is! Map<String, dynamic> || result['valid'] != true) {
      throw ApiException(
        result is Map && result['message'] is String
            ? result['message'] as String
            : 'Server không xác nhận yêu cầu.',
      );
    }
    return result;
  }

  Future<Map<String, dynamic>> machineData(
    String path,
    Map<String, dynamic> body,
  ) async {
    final result = await request(
      'POST',
      path,
      body: {...body, 'token': ?token},
    );
    if (result is! Map<String, dynamic> || result['status'] is! String) {
      throw const ApiException('Máy trả dữ liệu không đúng định dạng.');
    }
    return result;
  }

  Future<Object?> request(
    String method,
    String path, {
    Map<String, String>? query,
    Map<String, dynamic>? body,
  }) async {
    final base = Uri.tryParse(serverUrl.trim());
    if (base == null ||
        !['http', 'https'].contains(base.scheme) ||
        base.host.isEmpty) {
      throw const ApiException('Địa chỉ server không hợp lệ.');
    }
    final uri = base.replace(path: path, queryParameters: query, fragment: '');
    final client = HttpClient()..connectionTimeout = const Duration(seconds: 5);
    try {
      return await (() async {
        final request = await client.openUrl(method, uri);
        if (body != null) {
          final payload = utf8.encode(jsonEncode(body));
          request.headers.contentType = ContentType.json;
          request.contentLength = payload.length;
          request.add(payload);
        }
        final response = await request.close();
        final text = await utf8.decoder.bind(response).join();
        if (response.statusCode < 200 || response.statusCode >= 300) {
          // API tài khoản trả "message", relay trả "loi"; hiện thẳng cho người dùng.
          Object? error;
          try {
            error = jsonDecode(text);
          } on FormatException {
            // Không phải JSON, dùng thông báo HTTP bên dưới.
          }
          if (error is Map) {
            final message = error['message'] ?? error['loi'];
            if (error['login_required'] == true) {
              onLoginRequired?.call();
              throw LoginRequiredException(
                message is String
                    ? message
                    : 'Phiên đăng nhập hết hạn, hãy đăng nhập lại.',
              );
            }
            if (message is String) throw ApiException(message);
          }
          throw ApiException('HTTP ${response.statusCode}: $text');
        }
        return jsonDecode(text);
      })().timeout(const Duration(seconds: 25));
    } on ApiException {
      rethrow;
    } catch (error) {
      throw ApiException('Không kết nối được server ($error).');
    } finally {
      client.close(force: true);
    }
  }
}
