import 'package:simple_app/config/routing.dart';
import 'package:simple_app/core/server_client.dart';

extension MachineListRequests on ServerClient {
  Future<Map<String, dynamic>> renameMachine(String machineId, String name) =>
      account(Routes.machineNameUpdate, {'machine_id': machineId, 'name': name});

  Future<Map<String, dynamic>> removeMachine(String machineId) =>
      account(Routes.userMachineRemove, {'machine_id': machineId});

  Future<List<Map<String, dynamic>>> myMachines() async {
    final result = await account(Routes.userMachineList, {});
    final rows = result['machines'];
    if (rows is! List) {
      throw const ApiException('Server trả danh sách máy không hợp lệ.');
    }
    return rows.whereType<Map<String, dynamic>>().toList();
  }

  Future<Map<String, dynamic>> status(String machineId) async {
    final result = await request(
      'GET',
      Routes.machineStatusGet,
      query: {'machine_id': machineId},
    );
    if (result is! Map<String, dynamic>) {
      throw const ApiException('Server trả dữ liệu trạng thái không hợp lệ.');
    }
    return result;
  }
}
