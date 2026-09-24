import 'package:flutter/foundation.dart';

import '../machine_api.dart';

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

  List<Drink> drinks = const [];
  String? menuError;
  bool loadingMenu = false;

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

  Future<void> selectMachine(String id) async {
    _session++;
    machineId = id;
    drinks = const [];
    ingredients = const [];
    menuError = ingredientError = null;
    loadingMenu = loadingIngredients = false;
    notifyListeners();
    await refreshStatuses();
    if (online[id] == true) {
      await Future.wait([loadMenu(), loadIngredients()]);
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

  Future<void> loadMenu() => _load(
    start: () => loadingMenu = true,
    end: () => loadingMenu = false,
    command: 'xem_menu',
    apply: (result) {
      final rows = result is Map ? result['drinks'] : null;
      if (rows is! List) {
        throw const MachineException('Máy trả menu không đúng định dạng.');
      }
      final parsed = [
        for (final row in rows.whereType<Map<String, dynamic>>())
          Drink.fromJson(row),
      ];
      return () {
        drinks = parsed;
        menuError = null;
      };
    },
    fail: (message) => menuError = message,
  );

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

  // Ném lỗi ra ngoài để tab hiển thị SnackBar.
  Future<void> setDrinkAvailable(Drink drink, bool available) async {
    final id = machineId;
    if (id == null) throw const MachineException('Chưa chọn máy.');
    await api.send(id, 'doi_trang_thai_mon', {
      'drink_id': drink.id,
      'available': available,
    });
    await loadMenu();
  }

  @override
  void dispose() {
    _session++;
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
