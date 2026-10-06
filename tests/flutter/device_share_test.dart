import 'dart:convert';
import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:qr_flutter/qr_flutter.dart';
import 'package:simple_app/core/server_client.dart';
import 'package:simple_app/feature/machine_share/ui/machine_share_page.dart';

void main() {
  testWidgets('Chủ máy hiện QR mã mời, xem và thu hồi nhân viên', (
    tester,
  ) async {
    // Màn hình cao để danh sách nhân viên cuối trang cũng được dựng.
    tester.view.physicalSize = const Size(1080, 2400);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.reset);
    await tester.runAsync(() async {
      final previous = HttpOverrides.current;
      HttpOverrides.global = null;
      final server = await HttpServer.bind(InternetAddress.loopbackIPv4, 0);
      final bodies = <String, List<Object?>>{};
      var staff = [
        {'user_id': 7, 'username': 'nv1', 'full_name': 'Nhân viên Một'},
      ];
      server.listen((request) async {
        final body = jsonDecode(await utf8.decoder.bind(request).join());
        bodies.putIfAbsent(request.uri.path, () => []).add(body);
        final reply = switch (request.uri.path) {
          '/app/tao-ma-chia-se' => {
            'valid': true,
            'code': 'c' * 32,
            'expires_in': 300,
          },
          '/app/nhan-vien-may' => {'valid': true, 'staff': staff},
          '/app/thu-hoi-quyen' => {'valid': true},
          _ => {'valid': false, 'message': 'sai đường dẫn'},
        };
        if (request.uri.path == '/app/thu-hoi-quyen') staff = [];
        request.response.headers.contentType = ContentType.json;
        request.response.write(jsonEncode(reply));
        await request.response.close();
      });
      Future<void> pumpUntil(Finder finder) async {
        for (var i = 0; i < 100 && finder.evaluate().isEmpty; i++) {
          await tester.pump();
          await Future<void>.delayed(const Duration(milliseconds: 20));
        }
      }

      try {
        await tester.pumpWidget(
          MaterialApp(
            home: DeviceSharePage(
              api: ServerClient(
                'http://127.0.0.1:${server.port}',
                token: 'owner-token',
              ),
              machineId: 'fm_test',
            ),
          ),
        );
        await pumpUntil(find.byType(QrImageView));
        await pumpUntil(find.text('Nhân viên Một'));
        expect(bodies['/app/tao-ma-chia-se'], [
          {'machine_id': 'fm_test', 'token': 'owner-token'},
        ]);
        expect(find.byType(QrImageView), findsOneWidget);
        expect(find.textContaining('Quét QR'), findsOneWidget);
        expect(find.text('Nhân viên Một'), findsOneWidget);

        await tester.ensureVisible(find.byTooltip('Thu hồi quyền'));
        await tester.tap(find.byTooltip('Thu hồi quyền'));
        await tester.pump();
        await tester.pump(const Duration(milliseconds: 300));
        await tester.tap(find.text('Thu hồi'));
        await pumpUntil(find.text('Chưa giao máy cho nhân viên nào.'));
        expect(bodies['/app/thu-hoi-quyen'], [
          {'machine_id': 'fm_test', 'user_id': 7, 'token': 'owner-token'},
        ]);
        expect(find.text('Nhân viên Một'), findsNothing);
        await tester.pumpWidget(const SizedBox());
      } finally {
        await server.close(force: true);
        HttpOverrides.global = previous;
      }
    });
  });
}
