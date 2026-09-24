import 'dart:convert';
import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:qr_flutter/qr_flutter.dart';
import 'package:simple_app/UI/dashboard/machine_api.dart';
import 'package:simple_app/feature/machine_share/machine_share.dart';

void main() {
  testWidgets('Chủ máy gửi token + mã máy, hiện QR mã mời', (tester) async {
    await tester.runAsync(() async {
      final previous = HttpOverrides.current;
      HttpOverrides.global = null;
      final server = await HttpServer.bind(InternetAddress.loopbackIPv4, 0);
      final bodies = <Object?>[];
      server.listen((request) async {
        expect(request.uri.path, '/app/tao-ma-chia-se');
        bodies.add(jsonDecode(await utf8.decoder.bind(request).join()));
        request.response.headers.contentType = ContentType.json;
        request.response.write(
          jsonEncode({'valid': true, 'code': 'c' * 32, 'expires_in': 300}),
        );
        await request.response.close();
      });
      try {
        await tester.pumpWidget(
          MaterialApp(
            home: DeviceSharePage(
              api: MachineApi(
                'http://127.0.0.1:${server.port}',
                token: 'owner-token',
              ),
              machineId: 'fm_test',
            ),
          ),
        );
        for (var i = 0; i < 100; i++) {
          await tester.pump();
          if (find.byType(QrImageView).evaluate().isNotEmpty) break;
          await Future<void>.delayed(const Duration(milliseconds: 20));
        }
        expect(bodies, [
          {'machine_id': 'fm_test', 'token': 'owner-token'},
        ]);
        final qr = tester.widget<QrImageView>(find.byType(QrImageView));
        expect(qr, isNotNull);
        expect(find.textContaining('Quét QR'), findsOneWidget);
        await tester.pumpWidget(const SizedBox());
      } finally {
        await server.close(force: true);
        HttpOverrides.global = previous;
      }
    });
  });
}
