import 'package:simple_app/feature/machine_list/machine_list_request.dart';
import 'package:flutter/foundation.dart';

import 'package:simple_app/feature/machine_ingredient/machine_ingredient_sync.dart';
import 'package:simple_app/feature/machine_menu/machine_menu_sync.dart';
import 'package:simple_app/core/server_client.dart';

// Trạng thái chung của dashboard. Chỉ gọi những lệnh server đã có:
// trạng thái máy, xem menu, bật/tắt món và đồng bộ kho.
class DashboardController extends ChangeNotifier {
  DashboardController(this.api);
  final ServerClient api;

  // Máy lấy từ server theo tài khoản (chủ hoặc được giao).
  final List<String> machines = [];
  final Map<String, bool> online = {};
  final Map<String, String> names = {};
  // owner: chủ máy, được chia sẻ; manager: nhân viên được giao.
  final Map<String, String> roles = {};
  String? machinesError;
  String? machineId;
  bool checking = false;

  // Dữ liệu Menu/Kho do feature machine_menu và machine_ingredient giữ.
  late final products = ProductsSync(api, () => machineId);
  late final inventory = IngredientsSync(api, () => machineId);

  // Tăng khi đổi máy hoặc đóng dashboard để bỏ các kết quả trả về muộn.
  int _session = 0;
  int _statusRequest = 0;
  int _listRequest = 0;

  bool get hasMachine => machineId != null;

  Future<void> loadMyMachines() async {
    if (api.token == null) return;
    final request = ++_listRequest;
    try {
      final rows = await api.myMachines();
      // Lượt tải cũ trả về sau lượt mới hoặc sau khi đóng dashboard thì bỏ.
      if (request != _listRequest) return;
      machinesError = null;
      // Danh sách server là bản đúng: máy bị thu hồi/gỡ ở nơi khác cũng biến mất.
      final ids = <String>[];
      for (final row in rows) {
        final id = row['machine_id'];
        if (id is! String || id.isEmpty || ids.contains(id)) continue;
        ids.add(id);
        if (row['name'] is String) names[id] = row['name'] as String;
        if (row['role'] is String) roles[id] = row['role'] as String;
      }
      for (final id in List.of(machines)) {
        if (!ids.contains(id)) {
          names.remove(id);
          roles.remove(id);
          online.remove(id);
        }
      }
      machines
        ..clear()
        ..addAll(ids);
      if (machineId != null && !ids.contains(machineId)) {
        _session++;
        machineId = null;
        products.reset();
        inventory.reset();
      }
    } on ApiException catch (error) {
      if (request != _listRequest) return;
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
    // Tải luôn cả khi máy offline: server trả "Máy đang offline" ngay và các tab
    // hiện lỗi đó thay vì báo "Máy chưa có món nào".
    await Future.wait([refreshStatuses(), products.load(), inventory.load()]);
  }

  Future<void> refreshStatuses() async {
    final session = _session;
    final request = ++_statusRequest;
    bool isCurrent() => session == _session && request == _statusRequest;
    checking = true;
    notifyListeners();
    // Hỏi mọi máy cùng lúc thay vì lần lượt từng máy.
    await Future.wait([
      for (final id in List.of(machines))
        api
            .status(id)
            .then((result) {
              if (isCurrent() && machines.contains(id)) {
                online[id] = result['online'] == true;
              }
            })
            .catchError((Object _) {
              if (isCurrent() && machines.contains(id)) online[id] = false;
            }),
    ]);
    if (!isCurrent()) return;
    checking = false;
    notifyListeners();
  }

  @override
  void dispose() {
    _session++;
    _listRequest++;
    products.dispose();
    inventory.dispose();
    super.dispose();
  }
}
