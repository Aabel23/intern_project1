import 'package:simple_app/config/routing.dart';
import 'package:simple_app/core/server_client.dart';

extension MachineIngredientRequests on ServerClient {
  Future<Map<String, dynamic>> receiveIngredients(
    String machineId,
    int version,
  ) => machineData(Routes.receiveIngredients, {
    'machine_id': machineId,
    'version': version,
  });

  Future<Map<String, dynamic>> refill(
    String machineId,
    Object target, [
    Object value = 'full',
  ]) async {
    final result = await request(
      'POST',
      Routes.refill,
      body: {
        'machine_id': machineId,
        'target': target,
        'value': value,
        'token': ?token,
      },
    );
    if (result is! Map<String, dynamic>) {
      throw const ApiException('Máy trả kết quả nạp kho không hợp lệ.');
    }
    return result;
  }
}
