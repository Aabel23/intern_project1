import 'package:flutter/foundation.dart';

import '../../UI/dashboard/machine_api.dart';

// Một món trong menu, đọc từ kết quả lệnh xem_menu.
class Drink {
  const Drink({
    required this.id,
    required this.name,
    required this.price,
    required this.available,
    required this.inStock,
  });

  factory Drink.fromJson(Map<String, dynamic> json) => Drink(
    id: (json['drinkId'] as num).toInt(),
    name: json['name']?.toString() ?? '',
    price: (json['price'] as num?)?.toDouble() ?? 0,
    available: json['available'] == true,
    inStock: json['inStock'] != false,
  );

  final int id;
  final String name;
  final double price;
  final bool available;
  final bool inStock;
}

// Đồng bộ menu của máy đang chọn; tab Sản phẩm chỉ đọc drinks/loading/error để vẽ.
class ProductsSync extends ChangeNotifier {
  ProductsSync(this.api, this.machineId);
  final MachineApi api;
  // Đọc máy đang chọn từ DashboardController, không giữ bản riêng.
  final String? Function() machineId;

  List<Drink> drinks = const [];
  String? error;
  bool loading = false;

  // Tăng khi đổi máy hoặc đóng dashboard để bỏ các kết quả trả về muộn.
  int _session = 0;
  bool _disposed = false;

  void reset() {
    _session++;
    drinks = const [];
    error = null;
    loading = false;
    notifyListeners();
  }

  Future<void> load() async {
    final id = machineId();
    final session = _session;
    // Bật/tắt món xong mà dashboard đã đóng thì không tải lại.
    if (id == null || _disposed) return;
    loading = true;
    notifyListeners();
    List<Drink>? parsed;
    String? failure;
    try {
      final result = await api.send(id, 'xem_menu');
      final rows = result is Map ? result['drinks'] : null;
      if (rows is! List) {
        throw const MachineException('Máy trả menu không đúng định dạng.');
      }
      parsed = [
        for (final row in rows.whereType<Map<String, dynamic>>())
          Drink.fromJson(row),
      ];
    } catch (caught) {
      failure = caught.toString();
    }
    if (session != _session) return;
    if (parsed != null) drinks = parsed;
    error = failure;
    loading = false;
    notifyListeners();
  }

  // Ném lỗi ra ngoài để tab hiển thị SnackBar.
  Future<void> setAvailable(Drink drink, bool available) async {
    final id = machineId();
    if (id == null) throw const MachineException('Chưa chọn máy.');
    await api.send(id, 'doi_trang_thai_mon', {
      'drink_id': drink.id,
      'available': available,
    });
    await load();
  }

  @override
  void dispose() {
    _session++;
    _disposed = true;
    super.dispose();
  }
}
