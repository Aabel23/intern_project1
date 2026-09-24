import 'package:flutter/foundation.dart';

import '../../UI/dashboard/machine_api.dart';

// Một nguyên liệu, đọc từ kết quả lệnh dong_bo_nguyen_lieu.
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

  // ETag của bản đang hiển thị; máy trả 304 nếu dữ liệu chưa đổi.
  String? _etag;

  // Tăng khi đổi máy hoặc đóng dashboard để bỏ các kết quả trả về muộn.
  int _session = 0;
  bool _disposed = false;

  void reset() {
    _session++;
    ingredients = const [];
    _etag = null;
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
    ({String? etag, Object? data})? result;
    List<Ingredient>? parsed;
    String? failure;
    try {
      result = await api.sync(id, 'dong_bo_nguyen_lieu', _etag);
      // null: dữ liệu không đổi, giữ nguyên danh sách đang hiển thị.
      if (result != null) {
        final data = result.data;
        final rows = data is Map ? data['ingredients'] : null;
        if (rows is! List) {
          throw const MachineException('Máy trả kho không đúng định dạng.');
        }
        parsed = [
          for (final row in rows.whereType<Map<String, dynamic>>())
            Ingredient.fromJson(row),
        ];
      }
    } catch (caught) {
      failure = caught.toString();
    }
    if (session != _session) return;
    if (parsed != null) {
      ingredients = parsed;
      _etag = result?.etag;
    }
    error = failure;
    loading = false;
    notifyListeners();
  }

  @override
  void dispose() {
    _session++;
    _disposed = true;
    super.dispose();
  }
}
