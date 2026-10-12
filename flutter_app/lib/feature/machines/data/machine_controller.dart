import 'dart:convert';
import 'dart:io';

import 'package:flutter/foundation.dart';

import '../../../shared/cloud/cloud_error.dart';
import 'machine_service.dart';

/// Danh sách máy và máy đang chọn, dùng chung cho mọi tab của dashboard.
class MachineController extends ChangeNotifier {
  MachineController({required this.service});
  final MachineService service;

  List<Machine> machines = const [];
  String? selectedId;
  bool loading = false;
  String? error;

  Machine? get selected {
    for (final m in machines) {
      if (m.id == selectedId) return m;
    }
    return null;
  }

  Future<void> refresh() async {
    loading = true;
    error = null;
    notifyListeners();
    try {
      machines = await service.list();
      if (selected == null) {
        selectedId = machines.isEmpty ? null : machines.first.id;
      }
    } on CloudError catch (e) {
      error = e.code;
    } finally {
      loading = false;
      notifyListeners();
    }
  }

  void select(String id) {
    if (id == selectedId) return;
    // Đổi máy là bỏ mọi kết quả đang hiển thị của máy cũ (các tab theo dõi selectedId).
    selectedId = id;
    notifyListeners();
  }

  Future<void> remove(String id) async {
    await service.remove(id);
    if (selectedId == id) selectedId = null;
    await refresh();
  }

  Future<void> added(Machine machine) async {
    selectedId = machine.id;
    await refresh();
  }
}

/// Gói menu của version1.1: base64(zlib(JSON)) với fields + drinks dạng mảng.
List<Map<String, Object?>> decodeMenuPacket(String packet) {
  final raw = ZLibDecoder().convert(base64.decode(packet));
  final value = jsonDecode(utf8.decode(raw));
  if (value is! Map ||
      value['type'] != 'menu_sync' ||
      value['fields'] is! List ||
      value['drinks'] is! List) {
    throw const CloudError('INVALID_RESPONSE');
  }
  final fields = List<String>.from(value['fields'] as List);
  return [
    for (final row in value['drinks'] as List)
      if (row is List && row.length == fields.length)
        {for (var i = 0; i < fields.length; i++) fields[i]: row[i]}
      else
        throw const CloudError('INVALID_RESPONSE'),
  ];
}

/// Câu chữ cho người dùng theo mã lỗi relay hoặc lỗi máy.
String relayMessage(String code) => switch (code) {
  'MACHINE_OFFLINE' => 'Máy chưa kết nối cloud.',
  'MACHINE_TIMEOUT' => 'Máy không trả lời trong 15 giây.',
  'BUSY' => 'Máy đang xử lý yêu cầu khác, thử lại sau.',
  'FORBIDDEN' => 'Tài khoản không còn quyền với máy này.',
  'REQUEST_GONE' => 'Không xác định được kết quả lần trước; hãy làm mới.',
  'TIMEOUT' || 'TRANSPORT_ERROR' => 'Chưa nhận được câu trả lời (mạng).',
  'COMMAND_FAILED' => 'Máy từ chối yêu cầu.',
  'MACHINE_READ_FAILED' => 'Máy gặp lỗi khi đọc dữ liệu.',
  'COMMAND_EXPIRED' => 'Lệnh tới máy quá hạn.',
  _ => 'Không thể hoàn tất ($code).',
};
