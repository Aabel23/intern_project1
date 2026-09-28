import 'dart:convert';
import 'dart:io';

import 'package:flutter/foundation.dart';

import '../../UI/dashboard/machine_api.dart';

// Một món trong menu, đọc từ gói menu_sync máy gửi lên.
class Drink {
  const Drink({
    required this.id,
    required this.name,
    required this.price,
    required this.available,
    required this.inStock,
  });

  factory Drink.fromRow(Map<String, Object?> row) => Drink(
    id: (row['drink_id'] as num).toInt(),
    name: row['drink_name']?.toString() ?? '',
    price: (row['price'] as num?)?.toDouble() ?? 0,
    available: row['available'] == 1 || row['available'] == true,
    inStock: row['in_stock'] != 0 && row['in_stock'] != false,
  );

  final int id;
  final String name;
  final double price;
  final bool available;
  final bool inStock;
}

// Gói menu: base64(zlib(JSON)) với "fields" là tên cột và mỗi món là một mảng
// theo đúng thứ tự đó (xem machine/menu_sync/menu_sync_packet.py).
({int version, List<Drink> drinks}) decodeMenuPacket(String packet) {
  final json = jsonDecode(
    utf8.decode(ZLibCodec().decode(base64Decode(packet))),
  );
  if (json is! Map ||
      json['type'] != 'menu_sync' ||
      json['v'] != 1 ||
      json['fields'] is! List ||
      json['drinks'] is! List) {
    throw const MachineException(
      'Gói menu không đúng loại hoặc sai phiên bản.',
    );
  }
  final fields = (json['fields'] as List).cast<String>();
  return (
    version: (json['menu_version'] as num).toInt(),
    drinks: [
      for (final row in (json['drinks'] as List).whereType<List>())
        Drink.fromRow(Map.fromIterables(fields, row)),
    ],
  );
}

// Tab Menu: nhận gói menu và gửi thay đổi món; tab chỉ đọc drinks/loading/error để vẽ.
class ProductsSync extends ChangeNotifier {
  ProductsSync(this.api, this.machineId);
  final MachineApi api;
  // Đọc máy đang chọn từ DashboardController, không giữ bản riêng.
  final String? Function() machineId;

  List<Drink> drinks = const [];
  String? error;
  bool loading = false;
  // Bản menu đang giữ (CRC32 do máy tính); 0 = chưa có, máy sẽ gửi nguyên gói.
  int menuVersion = 0;
  // Tăng khi đổi máy hoặc đóng dashboard để bỏ các kết quả trả về muộn.
  int _session = 0;
  bool _disposed = false;

  void reset() {
    _session++;
    drinks = const [];
    menuVersion = 0;
    error = null;
    loading = false;
    notifyListeners();
  }

  Future<void> load() async {
    final id = machineId();
    final session = _session;
    if (id == null || _disposed) return;
    loading = true;
    notifyListeners();
    String? failure;
    try {
      final reply = await api.receiveMenu(id, menuVersion);
      if (session != _session) return;
      // up_to_date: máy không gửi lại gói, giữ danh sách đang có.
      if (reply['status'] == 'ok') _apply(reply);
    } catch (caught) {
      failure = caught.toString();
    }
    if (session != _session) return;
    error = failure;
    loading = false;
    notifyListeners();
  }

  // Ném lỗi ra ngoài để tab hiển thị SnackBar.
  Future<void> setAvailable(Drink drink, bool available) => _send([
    {'drink_id': drink.id, 'available': available},
  ]);

  Future<void> _send(List<Map<String, dynamic>> changes) async {
    final id = machineId();
    if (id == null) throw const MachineException('Chưa chọn máy.');
    final session = _session;
    final reply = await api.sendMenu(id, menuVersion, changes);
    if (session != _session || _disposed) return;
    // Máy luôn trả menu mới nhất; conflict nghĩa là thay đổi chưa được ghi.
    _apply(reply);
    error = null;
    notifyListeners();
    if (reply['status'] == 'conflict') {
      throw const MachineException(
        'Menu trên máy vừa thay đổi, đã tải bản mới. Hãy thử lại.',
      );
    }
  }

  void _apply(Map<String, dynamic> reply) {
    final packet = reply['packet'];
    if (packet is! String) {
      throw const MachineException('Máy trả menu không đúng định dạng.');
    }
    final menu = decodeMenuPacket(packet);
    drinks = menu.drinks;
    menuVersion = menu.version;
  }

  @override
  void dispose() {
    _session++;
    _disposed = true;
    super.dispose();
  }
}
