import 'dart:convert';
import 'dart:io';

// Lỗi đọc được cho người dùng: URL sai, server báo lỗi hoặc máy trả "loi".
class MachineException implements Exception {
  const MachineException(this.message);
  final String message;

  @override
  String toString() => message;
}

// Gọi server theo đúng giao thức hiện có: app gửi lệnh, server chuyển cho máy.
class MachineApi {
  MachineApi(this.serverUrl, {this.token});
  final String serverUrl;

  // Token phiên đăng nhập; server dùng để biết ai là chủ/nhân viên của máy.
  final String? token;

  Future<Map<String, dynamic>> registerMachine(
    Map<String, String> packet,
  ) async {
    final result = await _request(
      'POST',
      '/app/dang-ky-may',
      body: {...packet, 'token': ?token},
    );
    if (result is! Map<String, dynamic> ||
        result['valid'] != true ||
        result['machine_id'] is! String ||
        (result['machine_id'] as String).isEmpty) {
      throw const MachineException('Server chưa xác nhận đăng ký máy.');
    }
    return result;
  }

  // Chủ máy tạo mã mời dùng một lần để hiện QR cho nhân viên quét.
  Future<Map<String, dynamic>> createShare(String machineId) =>
      _account('/app/tao-ma-chia-se', {'machine_id': machineId});

  Future<Map<String, dynamic>> acceptShare(String code) =>
      _account('/app/nhan-chia-se', {'code': code});

  // Các máy tài khoản đang là chủ (owner) hoặc được giao quản lý (manager).
  Future<List<Map<String, dynamic>>> myMachines() async {
    final result = await _account('/app/may-cua-toi', {});
    final rows = result['machines'];
    if (rows is! List) {
      throw const MachineException('Server trả danh sách máy không hợp lệ.');
    }
    return rows.whereType<Map<String, dynamic>>().toList();
  }

  Future<Map<String, dynamic>> _account(
    String path,
    Map<String, dynamic> body,
  ) async {
    final result = await _request(
      'POST',
      path,
      body: {...body, 'token': ?token},
    );
    if (result is! Map<String, dynamic> || result['valid'] != true) {
      throw MachineException(
        result is Map && result['message'] is String
            ? result['message'] as String
            : 'Server không xác nhận yêu cầu.',
      );
    }
    return result;
  }

  Future<Map<String, dynamic>> status(String machineId) async {
    final result = await _request(
      'GET',
      '/machine/trang-thai',
      query: {'machine_id': machineId},
    );
    if (result is! Map<String, dynamic>) {
      throw const MachineException(
        'Server trả dữ liệu trạng thái không hợp lệ.',
      );
    }
    return result;
  }

  Future<Object?> send(
    String machineId,
    String command, [
    Map<String, dynamic> params = const {},
  ]) async {
    final result = await _request(
      'POST',
      '/app/gui-lenh',
      body: {'machine_id': machineId, 'ten': command, 'thamso': params},
    );
    if (result is Map && result['loi'] != null) {
      throw MachineException(result['loi'].toString());
    }
    return result;
  }

  Future<Object?> _request(
    String method,
    String path, {
    Map<String, String>? query,
    Map<String, dynamic>? body,
  }) async {
    final base = Uri.tryParse(serverUrl.trim());
    if (base == null ||
        !['http', 'https'].contains(base.scheme) ||
        base.host.isEmpty) {
      throw const MachineException('Địa chỉ server không hợp lệ.');
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
          // Các API tài khoản trả message tiếng Việt, hiện thẳng cho người dùng.
          try {
            final error = jsonDecode(text);
            if (error is Map && error['message'] is String) {
              throw MachineException(error['message'] as String);
            }
          } on FormatException {
            // Không phải JSON, dùng thông báo HTTP bên dưới.
          }
          throw MachineException('HTTP ${response.statusCode}: $text');
        }
        return jsonDecode(text);
      })().timeout(const Duration(seconds: 25));
    } on MachineException {
      rethrow;
    } catch (error) {
      throw MachineException('Không kết nối được server ($error).');
    } finally {
      client.close(force: true);
    }
  }
}
