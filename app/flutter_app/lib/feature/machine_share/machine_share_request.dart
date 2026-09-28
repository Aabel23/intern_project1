import 'package:simple_app/config/routing.dart';
import 'package:simple_app/core/server_client.dart';

extension MachineShareRequests on ServerClient {
  Future<Map<String, dynamic>> createShare(String machineId) =>
      account(Routes.createShare, {'machine_id': machineId});

  Future<Map<String, dynamic>> acceptShare(String code) =>
      account(Routes.acceptShare, {'code': code});

  Future<List<Map<String, dynamic>>> listStaff(String machineId) async {
    final result = await account(Routes.listStaff, {'machine_id': machineId});
    final rows = result['staff'];
    if (rows is! List) {
      throw const ApiException('Server trả danh sách nhân viên không hợp lệ.');
    }
    return rows.whereType<Map<String, dynamic>>().toList();
  }

  Future<Map<String, dynamic>> revokeStaff(String machineId, int userId) =>
      account(Routes.revokeStaff, {'machine_id': machineId, 'user_id': userId});
}
