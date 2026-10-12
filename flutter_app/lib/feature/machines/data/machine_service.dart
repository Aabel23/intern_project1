import 'dart:math';

import '../../../shared/cloud/cloud_client.dart';
import '../../../shared/cloud/cloud_error.dart';

/// Một máy trong danh sách của tài khoản. `online` là "Kết nối cloud" (máy đang poll),
/// không phải câu trả lời của máy.
class Machine {
  const Machine({
    required this.id,
    required this.serial,
    required this.name,
    required this.role,
    required this.online,
    this.lastSeenAt,
  });
  final String id;
  final String serial;
  final String name;
  final String role;
  final bool online;
  final int? lastSeenAt;

  static Machine fromMap(Map<String, dynamic> map, {bool? online}) {
    if (map['id'] is! String ||
        map['serial'] is! String ||
        map['name'] is! String ||
        map['role'] != 'owner') {
      throw const CloudError('INVALID_RESPONSE');
    }
    return Machine(
      id: map['id'],
      serial: map['serial'],
      name: map['name'],
      role: map['role'],
      online: online ?? map['online'] == true,
      lastSeenAt: map['last_seen_at'] is int ? map['last_seen_at'] : null,
    );
  }
}

class ClaimChallenge {
  const ClaimChallenge({
    required this.claimId,
    required this.machineId,
    required this.challenge,
    required this.signature,
  });
  final String claimId;
  final String machineId;
  final Map<String, dynamic> challenge;
  final String signature;
}

/// Câu trả lời của chính máy qua relay; `ok=false` là máy báo lỗi, khác lỗi relay (CloudError).
class MachineAnswer {
  const MachineAnswer({
    required this.requestId,
    required this.receivedAt,
    required this.ok,
    this.data,
    this.errorCode,
    this.message,
  });
  final String requestId;
  final int receivedAt;
  final bool ok;
  final Map<String, dynamic>? data;
  final String? errorCode;
  final String? message;
}

String newRequestId([Random? random]) {
  final r = random ?? Random.secure();
  final b = List<int>.generate(16, (_) => r.nextInt(256));
  b[6] = (b[6] & 0x0f) | 0x40;
  b[8] = (b[8] & 0x3f) | 0x80;
  final h = b.map((x) => x.toRadixString(16).padLeft(2, '0')).join();
  return '${h.substring(0, 8)}-${h.substring(8, 12)}-${h.substring(12, 16)}-'
      '${h.substring(16, 20)}-${h.substring(20)}';
}

class MachineService {
  MachineService({required this.client});
  final CloudClient client;

  static const _relayTimeout = Duration(seconds: 20);

  Future<List<Machine>> list() async {
    final data = await client.authenticatedPost('/app/user/machine/list', {
      'v': 1,
    }, retryAfterRefresh: true);
    final machines = data['machines'];
    if (machines is! List) throw const CloudError('INVALID_RESPONSE');
    return [
      for (final m in machines)
        if (m is Map)
          Machine.fromMap(Map<String, dynamic>.from(m))
        else
          throw const CloudError('INVALID_RESPONSE'),
    ];
  }

  Future<void> remove(String machineId) async {
    final data = await client.authenticatedPost('/app/user/machine/remove', {
      'v': 1,
      'machine_id': machineId,
    });
    if (data['removed'] != true) throw const CloudError('INVALID_RESPONSE');
  }

  Future<ClaimChallenge> beginClaim(String serial) async {
    final data = await client.authenticatedPost('/app/user/machine/activate', {
      'v': 1,
      'step': 'begin',
      'serial': serial,
    }, retryAfterRefresh: true);
    final challenge = data['challenge'];
    if (data['claim_id'] is! String ||
        data['machine_id'] is! String ||
        challenge is! Map ||
        data['server_challenge_signature'] is! String) {
      throw const CloudError('INVALID_RESPONSE');
    }
    return ClaimChallenge(
      claimId: data['claim_id'],
      machineId: data['machine_id'],
      challenge: Map<String, dynamic>.from(challenge),
      signature: data['server_challenge_signature'],
    );
  }

  /// Gửi lại cùng claim_id là an toàn: server trả lại kết quả đã commit.
  Future<Machine> completeClaim({
    required String claimId,
    required String machineProof,
    required String localSessionBinding,
  }) async {
    final data = await client.authenticatedPost('/app/user/machine/activate', {
      'v': 1,
      'step': 'complete',
      'claim_id': claimId,
      'machine_proof': machineProof,
      'local_session_binding': localSessionBinding,
    }, retryAfterRefresh: true);
    final machine = data['machine'];
    if (machine is! Map) throw const CloudError('INVALID_RESPONSE');
    return Machine.fromMap(Map<String, dynamic>.from(machine), online: false);
  }

  /// Một lượt hỏi máy. Mỗi bấm "Làm mới" tạo request_id mới; retry sau lỗi mạng
  /// giữ request_id và đặt retry=true để server không chạy lại lệnh ghi.
  Future<MachineAnswer> ask(
    String machineId,
    String instruction,
    Map<String, dynamic> data, {
    String? requestId,
    bool retry = false,
  }) async {
    final id = requestId ?? newRequestId();
    final body = <String, dynamic>{
      'v': 1,
      'request_id': id,
      'machine_id': machineId,
      'instruction': instruction,
      'data': data,
    };
    if (retry) body['retry'] = true;
    final out = await client.authenticatedPost(
      '/app/machine/command/send',
      body,
      retryAfterRefresh: true,
      timeout: _relayTimeout,
    );
    final result = out['result'];
    if (out['request_id'] != id ||
        out['machine_id'] != machineId ||
        out['source'] != 'machine' ||
        out['received_at'] is! int ||
        result is! Map ||
        result['ok'] is! bool) {
      throw const CloudError('INVALID_RESPONSE');
    }
    if (result['ok'] == true) {
      if (result['data'] is! Map) throw const CloudError('INVALID_RESPONSE');
      return MachineAnswer(
        requestId: id,
        receivedAt: out['received_at'],
        ok: true,
        data: Map<String, dynamic>.from(result['data']),
      );
    }
    final error = result['error'];
    if (error is! Map || error['code'] is! String) {
      throw const CloudError('INVALID_RESPONSE');
    }
    return MachineAnswer(
      requestId: id,
      receivedAt: out['received_at'],
      ok: false,
      errorCode: error['code'],
      message: error['message'] is String ? error['message'] : null,
    );
  }
}
