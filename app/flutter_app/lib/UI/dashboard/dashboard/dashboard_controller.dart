import 'package:flutter/foundation.dart';

import '../../../feature/data_sync/products_sync.dart';
import '../machine_api.dart';

// Một nguyên liệu, đọc từ kết quả lệnh xem_nguyen_lieu.
class Ingredient {
  const Ingredient({
    required this.id,
    required this.name,
    required this.amount,
    required this.inStock,
  });

  factory Ingredient.fromJson(Map<String, dynamic> json) => Ingredient(
    id: (json['id'] as num).toInt(),
    name: json['name']?.toString() ?? '',
    amount: (json['amount'] as num?)?.toDouble() ?? 0,
    inStock: json['in_stock'] == true,
  );

  final int id;
  final String name;
  final double amount;
  final bool inStock;
}

// Trạng thái chung của dashboard. Chỉ gọi những lệnh server đã có:
// trạng thái máy, xem menu, bật/tắt món và xem kho.
class DashboardController extends ChangeNotifier {
  DashboardController(this.api);
  final MachineApi api;

  // Máy lấy từ server theo tài khoản, cộng thêm máy nhập mã tay trong phiên.
  final List<String> machines = [];
  final Map<String, bool> online = {};
  final Map<String, String> names = {};
  // owner: chủ máy, được chia sẻ; manager: nhân viên được giao.
  final Map<String, String> roles = {};
  String? machinesError;
  String? machineId;
  bool checking = false;

  // Dữ liệu từng tab tách ra feature/data_sync.
  late final products = ProductsSync(api, () => machineId);

  List<Ingredient> ingredients = const [];
  String? ingredientError;
  bool loadingIngredients = false;

  // Tăng khi đổi máy hoặc đóng dashboard để bỏ các kết quả trả về muộn.
  int _session = 0;

  bool get hasMachine => machineId != null;

  Future<void> loadMyMachines() async {
    if (api.token == null) return;
    try {
      final rows = await api.myMachines();
      machinesError = null;
      for (final row in rows) {
        final id = row['machine_id'];
        if (id is! String || id.isEmpty) continue;
        if (!machines.contains(id)) machines.add(id);
        if (row['name'] is String) names[id] = row['name'] as String;
        if (row['role'] is String) roles[id] = row['role'] as String;
      }
    } on MachineException catch (error) {
      machinesError = error.message;
    }
    if (machineId == null && machines.isNotEmpty) {
      await selectMachine(machines.first);
    } else {
      await refreshStatuses();
    }
  }

  Future<void> addMachine(String id) async {
    if (!machines.contains(id)) machines.add(id);
    await selectMachine(id);
  }

  // Máy vừa bị gỡ: bỏ khỏi danh sách, đang chọn thì chuyển sang máy khác (nếu còn).
  Future<void> forgetMachine(String id) async {
    machines.remove(id);
    names.remove(id);
    roles.remove(id);
    online.remove(id);
    if (machineId == id) {
      _session++;
      machineId = null;
      products.reset();
      ingredients = const [];
      ingredientError = null;
      loadingIngredients = false;
    }
    notifyListeners();
    await loadMyMachines();
  }

  Future<void> selectMachine(String id) async {
    _session++;
    machineId = id;
    products.reset();
    ingredients = const [];
    ingredientError = null;
    loadingIngredients = false;
    notifyListeners();
    await refreshStatuses();
    if (online[id] == true) {
      await Future.wait([products.load(), loadIngredients()]);
    }
  }

  Future<void> refreshStatuses() async {
    final session = _session;
    checking = true;
    notifyListeners();
    for (final id in List.of(machines)) {
      try {
        online[id] = (await api.status(id))['online'] == true;
      } catch (_) {
        online[id] = false;
      }
    }
    if (session != _session) return;
    checking = false;
    notifyListeners();
  }

  Future<void> loadIngredients() => _load(
    start: () => loadingIngredients = true,
    end: () => loadingIngredients = false,
    command: 'xem_nguyen_lieu',
    apply: (result) {
      final rows = result is Map ? result['ingredients'] : null;
      if (rows is! List) {
        throw const MachineException('Máy trả kho không đúng định dạng.');
      }
      final parsed = [
        for (final row in rows.whereType<Map<String, dynamic>>())
          Ingredient.fromJson(row),
      ];
      return () {
        ingredients = parsed;
        ingredientError = null;
      };
    },
    fail: (message) => ingredientError = message,
  );

  @override
  void dispose() {
    _session++;
    products.dispose();
    super.dispose();
  }

  Future<void> _load({
    required VoidCallback start,
    required VoidCallback end,
    required String command,
    required VoidCallback Function(Object? result) apply,
    required void Function(String message) fail,
  }) async {
    final id = machineId;
    final session = _session;
    if (id == null) return;
    start();
    notifyListeners();
    VoidCallback update;
    try {
      update = apply(await api.send(id, command));
    } catch (error) {
      update = () => fail(error.toString());
    }
    if (session != _session) return;
    update();
    end();
    notifyListeners();
  }
}
