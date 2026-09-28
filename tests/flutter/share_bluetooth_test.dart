import 'dart:convert';
import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:simple_app/feature/machine_share/machine_share_bluetooth.dart';
import 'package:simple_app/feature/machine_share/machine_share_qr.dart';

void main() {
  const channel = MethodChannel('flexmix/bluetooth_pairing');
  TestWidgetsFlutterBinding.ensureInitialized();
  final code = 'c' * 32;

  tearDown(() {
    TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger
        .setMockMethodCallHandler(channel, null);
  });

  testWidgets('Chủ máy gửi đúng nội dung QR tới điện thoại được chọn', (
    tester,
  ) async {
    Map<Object?, Object?>? sent;
    TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger
        .setMockMethodCallHandler(channel, (call) async {
          if (call.method == 'scan') {
            return [
              {'name': 'Galaxy A25', 'address': 'AA:BB:CC:DD:EE:01'},
              {'name': 'Pixel 7', 'address': 'AA:BB:CC:DD:EE:02'},
            ];
          }
          if (call.method == 'sendShare') {
            sent = call.arguments as Map<Object?, Object?>;
          }
          return null;
        });

    await tester.pumpWidget(
      MaterialApp(home: ShareBluetoothSendPage(payload: encodeShareQr(code))),
    );
    await tester.pumpAndSettle();
    await tester.tap(find.text('Pixel 7'));
    await tester.pumpAndSettle();
    expect(sent, {
      'address': 'AA:BB:CC:DD:EE:02',
      'payload': jsonEncode({'type': 'share', 'code': code}),
    });
    expect(find.textContaining('Đã gửi mã cho Pixel 7'), findsOneWidget);
    await tester.pumpWidget(const SizedBox());
    await tester.pumpAndSettle();
  });

  testWidgets('Nhân viên nhận mã qua Bluetooth rồi gửi lên server', (
    tester,
  ) async {
    TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger
        .setMockMethodCallHandler(channel, (call) async {
          if (call.method == 'receiveShare') return encodeShareQr(code);
          return null;
        });
    await tester.runAsync(() async {
      final previous = HttpOverrides.current;
      HttpOverrides.global = null;
      final server = await HttpServer.bind(InternetAddress.loopbackIPv4, 0);
      final bodies = <Object?>[];
      server.listen((request) async {
        expect(request.uri.path, '/app/nhan-chia-se');
        bodies.add(jsonDecode(await utf8.decoder.bind(request).join()));
        request.response.headers.contentType = ContentType.json;
        request.response.write(
          jsonEncode({
            'valid': true,
            'machine_id': 'fm_test',
            'machine_name': 'FlexMix-01',
            'message': 'Đã nhận quản lý máy',
          }),
        );
        await request.response.close();
      });
      try {
        await tester.pumpWidget(
          MaterialApp(
            home: ShareBluetoothReceivePage(
              serverUrl: 'http://127.0.0.1:${server.port}',
              token: 'staff-token',
            ),
          ),
        );
        final done = find.textContaining('FlexMix-01');
        for (var i = 0; i < 100; i++) {
          await tester.pump();
          if (done.evaluate().isNotEmpty) break;
          await Future<void>.delayed(const Duration(milliseconds: 20));
        }
        expect(bodies, [
          {'code': code, 'token': 'staff-token'},
        ]);
        expect(done, findsOneWidget);
        await tester.pumpWidget(const SizedBox());
      } finally {
        await server.close(force: true);
        HttpOverrides.global = previous;
      }
    });
  });

  testWidgets('Gói Bluetooth không phải mã chia sẻ thì không gọi server', (
    tester,
  ) async {
    TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger
        .setMockMethodCallHandler(channel, (call) async {
          if (call.method == 'receiveShare') {
            return jsonEncode({
              'type': 'pairing',
              'machine_name': 'FlexMix-01',
              'product_key': 'key',
            });
          }
          return null;
        });
    await tester.pumpWidget(
      const MaterialApp(
        home: ShareBluetoothReceivePage(serverUrl: 'http://127.0.0.1:1'),
      ),
    );
    await tester.pumpAndSettle();
    expect(find.text('Gói nhận được không phải mã chia sẻ.'), findsOneWidget);
    await tester.pumpWidget(const SizedBox());
    await tester.pumpAndSettle();
  });
}
