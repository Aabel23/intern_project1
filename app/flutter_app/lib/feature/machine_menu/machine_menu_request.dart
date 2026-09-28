import 'package:simple_app/config/routing.dart';
import 'package:simple_app/core/server_client.dart';

extension MachineMenuRequests on ServerClient {
  Future<Map<String, dynamic>> receiveMenu(String machineId, int menuVersion) =>
      machineData(Routes.receiveMenu, {
        'machine_id': machineId,
        'menu_version': menuVersion,
      });

  Future<Map<String, dynamic>> sendMenu(
    String machineId,
    int menuVersion,
    List<Map<String, dynamic>> changes,
  ) => machineData(Routes.sendMenu, {
    'machine_id': machineId,
    'menu_version': menuVersion,
    'thay_doi': changes,
  });
}
