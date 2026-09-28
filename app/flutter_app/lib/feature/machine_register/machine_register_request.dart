import 'package:simple_app/config/routing.dart';
import 'package:simple_app/core/server_client.dart';

extension MachineRegisterRequests on ServerClient {
  Future<Map<String, dynamic>> registerMachine(
    Map<String, String> packet,
  ) async {
    final result = await request(
      'POST',
      Routes.machineRegister,
      body: {...packet, 'token': ?token},
    );
    if (result is! Map<String, dynamic> ||
        result['valid'] != true ||
        result['machine_id'] is! String ||
        (result['machine_id'] as String).isEmpty) {
      throw const ApiException('Server chưa xác nhận đăng ký máy.');
    }
    return result;
  }
}
