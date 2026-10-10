import 'package:simple_app/config/routing.dart';
import 'package:simple_app/core/server_client.dart';

extension MachineMenuRequests on ServerClient {
  Future<Map<String, dynamic>> receiveMenu(String machineId, int menuVersion) =>
      machineData(Routes.machineMenuGet, {
        'machine_id': machineId,
        'menu_version': menuVersion,
      });

  Future<Map<String, dynamic>> updateMenu(
    String machineId,
    int menuVersion,
    List<Map<String, dynamic>> changes,
  ) => machineData(Routes.machineMenuUpdate, {
    'machine_id': machineId,
    'menu_version': menuVersion,
    'thay_doi': changes,
  });

  // anh: [{drink_id, image_hash}], tối đa 20 dòng; máy trả {status, anh, con_lai}.
  Future<Map<String, dynamic>> receiveImages(
    String machineId,
    List<Map<String, int>> images,
  ) => machineData(Routes.machineImageGet, {
    'machine_id': machineId,
    'anh': images,
  });
}
