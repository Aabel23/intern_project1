import 'package:flutter/foundation.dart';

import '../../../feature/data_sync/ingredients_sync.dart';
import '../../../feature/data_sync/products_sync.dart';
import '../machine_api.dart';

// Trạng thái chung của dashboard. Chỉ gọi những lệnh server đã có:
// trạng thái máy, xem menu, bật/tắt món và đồng bộ kho.
class DashboardController extends ChangeNotifier {
  DashboardController(this.api);
  final MachineApi api;

  // Máy lấy từ server theo tài khoản (chủ hoặc được giao).
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
  late final inventory = IngredientsSync(api, () => machineId);

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
      inventory.reset();
    }
    notifyListeners();
    await loadMyMachines();
  }

  Future<void> selectMachine(String id) async {
    _session++;
    machineId = id;
    products.reset();
    inventory.reset();
    notifyListeners();
    await refreshStatuses();
    if (online[id] == true) {
      await Future.wait([products.load(), inventory.load()]);
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

  @override
  void dispose() {
    _session++;
    products.dispose();
    inventory.dispose();
    super.dispose();
  }
}
