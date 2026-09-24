import 'dart:convert';
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:simple_app/UI/dashboard/machine_api.dart';

void main() {
  test('Gửi nguyên gói pairing đến route đăng ký và nhận ID', () async {
    final server = await HttpServer.bind(InternetAddress.loopbackIPv4, 0);
    final packet = {
      'type': 'pairing',
      'machine_name': 'FlexMix-01',
      'product_key': 'test-key',
    };
    final received = server.first.then((request) async {
      expect(request.method, 'POST');
      expect(request.uri.path, '/app/dang-ky-may');
      final body = await utf8.decoder.bind(request).join();
      expect(jsonDecode(body), packet);
      request.response.headers.contentType = ContentType.json;
      request.response.write(
        jsonEncode({'valid': true, 'machine_id': 'fm_test', 'message': 'OK'}),
      );
      await request.response.close();
    });
    try {
      final api = MachineApi('http://127.0.0.1:${server.port}');
      final result = await api.registerMachine(packet);
      expect(result['machine_id'], 'fm_test');
      await received;
    } finally {
      await server.close(force: true);
    }
  });
}
