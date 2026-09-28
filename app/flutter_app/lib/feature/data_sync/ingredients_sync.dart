import 'package:flutter/foundation.dart';

import '../../UI/dashboard/machine_api.dart';

// Một nguyên liệu, đọc từ danh sách kho máy trả qua /app/nhan-kho.
class Ingredient {
  const Ingredient({
    required this.id,
    required this.name,
    required this.amount,
    required this.maxGram,
    required this.maxSet,
    required this.inStock,
    this.pumpNumber,
  });

  factory Ingredient.fromJson(Map<String, dynamic> json) => Ingredient(
    id: (json['ingredient_id'] as num).toInt(),
    name: json['name']?.toString() ?? '',
    amount: (json['amount'] as num?)?.toDouble() ?? 0,
    maxGram: (json['max_gram'] as num?)?.toDouble() ?? 0,
    maxSet: json['max_set'] == true,
    inStock: json['in_stock'] == true,
    pumpNumber: (json['pump_no'] as num?)?.toInt(),
  );

  final int id;
  final String name;
  final double amount;
  // Mức đầy của bình; maxSet = false nghĩa là máy dùng mức mặc định (ước tính).
  final double maxGram;
  final bool maxSet;
  final bool inStock;
  // Số bơm; null với nguyên liệu ở bảng thủ công.
  final int? pumpNumber;
}

// Đồng bộ kho của máy đang chọn; tab Kho chỉ đọc ingredients/loading/error để vẽ.
class IngredientsSync extends ChangeNotifier {
  IngredientsSync(this.api, this.machineId);
  final MachineApi api;
  // Đọc máy đang chọn từ DashboardController, không giữ bản riêng.
  final String? Function() machineId;

  List<Ingredient> ingredients = const [];
  String? error;
  bool loading = false;
  // Bản kho đang giữ (CRC32 do máy tính); 0 = chưa có, máy sẽ gửi nguyên danh sách.
  int version = 0;

  // Tăng khi đổi máy hoặc đóng dashboard để bỏ các kết quả trả về muộn.
  int _session = 0;
  bool _disposed = false;

  void reset() {
    _session++;
    ingredients = const [];
    version = 0;
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
      final reply = await api.receiveIngredients(id, version);
      if (session != _session) return;
      // up_to_date: máy không gửi lại danh sách, giữ bản đang hiển thị.
      if (reply['status'] == 'ok') _apply(reply);
    } catch (caught) {
      failure = caught.toString();
    }
    if (session != _session) return;
    error = failure;
    loading = false;
    notifyListeners();
  }

  void _apply(Map<String, dynamic> reply) {
    final rows = reply['ingredients'];
    if (rows is! List) {
      throw const MachineException('Máy trả kho không đúng định dạng.');
    }
    ingredients = [
      for (final row in rows.whereType<Map<String, dynamic>>())
        Ingredient.fromJson(row),
    ];
    version = (reply['version'] as num).toInt();
  }

  // Nạp kho rồi đọc lại danh sách; target là id nguyên liệu hoặc 'all'.
  // Lỗi (offline, không đủ quyền...) ném ra cho tab hiện thông báo.
  Future<void> refill(Object target) async {
    final id = machineId();
    if (id == null) return;
    await api.refill(id, target);
    await load();
  }

  @override
  void dispose() {
    _session++;
    _disposed = true;
    super.dispose();
  }
}
