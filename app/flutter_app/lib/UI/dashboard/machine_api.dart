import 'dart:convert';
import 'dart:io';

// Lỗi đọc được cho người dùng: URL sai, server báo lỗi hoặc máy trả "loi".
class MachineException implements Exception {
  const MachineException(this.message);
  final String message;

  @override
  String toString() => message;
}

// Server báo phiên đăng nhập hết hạn hoặc đã đăng xuất (login_required).
class LoginRequiredException extends MachineException {
  const LoginRequiredException(super.message);
}

// Gọi server theo đúng giao thức hiện có: app gửi lệnh, server chuyển cho máy.
class MachineApi {
  MachineApi(this.serverUrl, {this.token, this.onLoginRequired});
  final String serverUrl;

  // Token phiên đăng nhập; server dùng để biết ai là chủ/nhân viên của máy.
  final String? token;

  // Dashboard truyền vào để quay về màn hình đăng nhập khi token hết hạn.
  final void Function()? onLoginRequired;

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

  // Chủ máy xem nhân viên đang được giao máy.
  Future<List<Map<String, dynamic>>> listStaff(String machineId) async {
    final result = await _account('/app/nhan-vien-may', {
      'machine_id': machineId,
    });
    final rows = result['staff'];
    if (rows is! List) {
      throw const MachineException(
        'Server trả danh sách nhân viên không hợp lệ.',
      );
    }
    return rows.whereType<Map<String, dynamic>>().toList();
  }

  // Chủ máy thu hồi quyền của một nhân viên.
  Future<Map<String, dynamic>> revokeStaff(String machineId, int userId) =>
      _account('/app/thu-hoi-quyen', {
        'machine_id': machineId,
        'user_id': userId,
      });

  // Chủ máy đổi tên hiển thị của máy.
  Future<Map<String, dynamic>> renameMachine(String machineId, String name) =>
      _account('/app/doi-ten-may', {'machine_id': machineId, 'name': name});

  // Chủ: xóa máy khỏi quán. Nhân viên: bỏ quyền quản lý của mình.
  Future<Map<String, dynamic>> removeMachine(String machineId) =>
      _account('/app/go-may', {'machine_id': machineId});

  // Xóa token trên server; mất mạng thì app vẫn đăng xuất tại chỗ.
  Future<void> logout() async {
    if (token == null) return;
    try {
      await _request('POST', '/app/dang-xuat', body: {'token': token});
    } on MachineException {
      // Token cũ sẽ tự hết hạn trên server.
    }
  }

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
      body: {
        'machine_id': machineId,
        'ten': command,
        'thamso': params,
        'token': ?token,
      },
    );
    if (result is Map && result['loi'] != null) {
      throw MachineException(result['loi'].toString());
    }
    return result;
  }

  // Nạp kho qua /machine/refill. target: id nguyên liệu hoặc 'all';
  // value: 'full' (đổ đầy tới mức tối đa) hoặc số gram (chỉ với một nguyên liệu).
  Future<Map<String, dynamic>> refill(
    String machineId,
    Object target, [
    Object value = 'full',
  ]) async {
    final result = await _request(
      'POST',
      '/machine/refill',
      body: {
        'machine_id': machineId,
        'target': target,
        'value': value,
        'token': ?token,
      },
    );
    if (result is! Map<String, dynamic>) {
      throw const MachineException('Máy trả kết quả nạp kho không hợp lệ.');
    }
    return result;
  }

  // Đọc dữ liệu dashboard qua /app/dong-bo, gửi kèm ETag đang giữ.
  // Trả null khi dữ liệu trên máy không đổi (server trả 304), app giữ bản cũ.
  // Máy gửi JSON nén gzip; HttpClient tự giải nén.
  Future<({String? etag, Object? data})?> sync(
    String machineId,
    String command,
    String? etag,
  ) async {
    final response = await _send(
      'POST',
      '/app/dong-bo',
      body: {'machine_id': machineId, 'lenh': command, 'token': ?token},
      etag: etag,
    );
    if (response.status == HttpStatus.notModified) return null;
    return (etag: response.etag, data: response.data);
  }

  Future<Object?> _request(
    String method,
    String path, {
    Map<String, String>? query,
    Map<String, dynamic>? body,
  }) async => (await _send(method, path, query: query, body: body)).data;

  Future<({int status, String? etag, Object? data})> _send(
    String method,
    String path, {
    Map<String, String>? query,
    Map<String, dynamic>? body,
    String? etag,
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
        if (etag != null) {
          request.headers.set(HttpHeaders.ifNoneMatchHeader, etag);
        }
        if (body != null) {
          final payload = utf8.encode(jsonEncode(body));
          request.headers.contentType = ContentType.json;
          request.contentLength = payload.length;
          request.add(payload);
        }
        final response = await request.close();
        final text = await utf8.decoder.bind(response).join();
        final responseEtag = response.headers.value(HttpHeaders.etagHeader);
        if (response.statusCode == HttpStatus.notModified) {
          return (status: response.statusCode, etag: responseEtag, data: null);
        }
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
            if (message is String) throw MachineException(message);
          }
          throw MachineException('HTTP ${response.statusCode}: $text');
        }
        return (
          status: response.statusCode,
          etag: responseEtag,
          data: jsonDecode(text),
        );
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
