import 'package:simple_app/config/routing.dart';
import 'package:simple_app/core/server_client.dart';

extension UserAuthRequests on ServerClient {
  Future<void> logout() async {
    if (token == null) return;
    try {
      await request('POST', Routes.logout, body: {'token': token});
    } on ApiException {
      // Token cũ sẽ tự hết hạn trên server.
    }
  }
}
