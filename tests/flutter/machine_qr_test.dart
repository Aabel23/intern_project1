import 'dart:async';
import 'dart:convert';
import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mobile_scanner/mobile_scanner.dart';
import 'package:simple_app/feature/dashboard/ui/machine_qr_page.dart';
import 'package:simple_app/core/machine_packet.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  const camera = MethodChannel('dev.steenbakker.mobile_scanner/scanner/method');
  const events = MethodChannel('dev.steenbakker.mobile_scanner/scanner/event');
  const orientation = MethodChannel(
    'dev.steenbakker.mobile_scanner/scanner/deviceOrientation',
  );
  setUp(() {
    final messenger =
        TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger;
    messenger.setMockMethodCallHandler(camera, (call) async {
      if (call.method == 'state') return 1;
      if (call.method == 'start') {
        return {
          'textureId': 1,
          'cameraDirection': 1,
          'numberOfCameras': 1,
          'size': {'width': 640.0, 'height': 480.0},
        };
      }
      return null;
    });
    messenger.setMockMethodCallHandler(events, (_) async => null);
    messenger.setMockMethodCallHandler(orientation, (_) async => null);
  });
  tearDown(() {
    final messenger =
        TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger;
    messenger.setMockMethodCallHandler(camera, null);
    messenger.setMockMethodCallHandler(events, null);
    messenger.setMockMethodCallHandler(orientation, null);
  });
  test('QR hợp lệ lấy đúng gói pairing, bỏ trường không liên quan', () {
    final result = parseMachineQr(
      jsonEncode({
        'type': 'pairing',
        'machine_name': 'FlexMix-01',
        'product_key': 'test-key',
        'server_url': 'http://untrusted.example',
      }),
    );
    expect(result, {
      'type': 'pairing',
      'machine_name': 'FlexMix-01',
      'product_key': 'test-key',
    });
  });

  test('QR chia sẻ từ chủ máy chỉ lấy mã mời', () {
    final code = 'a' * 32;
    expect(parseMachineQr(jsonEncode({'type': 'share', 'code': code})), {
      'type': 'share',
      'code': code,
    });
    expect(
      () => parseMachineQr('{"type":"share","code":"short"}'),
      throwsFormatException,
    );
  });

  test('Từ chối QR hỏng, sai loại, thiếu key hoặc quá lớn', () {
    for (final raw in [
      'https://example.com',
      '[]',
      '{}',
      '{"type":"pairing","machine_name":"FlexMix-01","product_key":123}',
      '{"type":"pairing","machine_name":"FlexMix-01","product_key":" "}',
      'x' * 4097,
    ]) {
      expect(() => parseMachineQr(raw), throwsFormatException);
    }
  });

  test('QR share validates code types and exact length boundaries', () {
    for (final code in [null, true, 123, [], {}, 'a' * 19, 'a' * 101]) {
      expect(
        () => parseMachineQr(jsonEncode({'type': 'share', 'code': code})),
        throwsFormatException,
      );
    }
    for (final length in [20, 100]) {
      final code = 'a' * length;
      expect(
        parseMachineQr(
          jsonEncode({
            'type': 'share',
            'code': code,
            'server_url': 'https://untrusted.example',
            'token': 'injected',
          }),
        ),
        {'type': 'share', 'code': code},
      );
    }
  });

  test(
    'QR size limit measures UTF-8 bytes and rejects oversized pairing fields',
    () {
      expect(
        () => parseMachineQr(
          jsonEncode({
            'type': 'share',
            'code': 'a' * 32,
            'padding': '😀' * 1024,
          }),
        ),
        throwsFormatException,
      );
      for (final packet in [
        {'type': 'pairing', 'machine_name': 'x' * 151, 'product_key': 'key'},
        {'type': 'pairing', 'machine_name': 'valid', 'product_key': 'x' * 1025},
        {'type': 'pairing', 'machine_name': {}, 'product_key': 'key'},
      ]) {
        expect(() => parseMachineQr(jsonEncode(packet)), throwsFormatException);
      }
    },
  );

  testWidgets('Nhận QR lặp chỉ gửi một POST và hiển thị ID server', (
    tester,
  ) async {
    await tester.runAsync(() async {
      final previous = HttpOverrides.current;
      HttpOverrides.global = null;
      final server = await HttpServer.bind(InternetAddress.loopbackIPv4, 0);
      var count = 0;
      final received = Completer<void>();
      final packet = {
        'type': 'pairing',
        'machine_name': 'FlexMix-QR',
        'product_key': 'qr-test-key',
      };
      server.listen((request) async {
        count++;
        expect(request.method, 'POST');
        expect(request.uri.path, '/app/dang-ky-may');
        final body = await utf8.decoder.bind(request).join();
        expect(jsonDecode(body), packet);
        request.response.headers.contentType = ContentType.json;
        request.response.write(
          jsonEncode({
            'valid': true,
            'machine_id': 'fm_qr_test',
            'message': 'Đăng ký máy thành công',
          }),
        );
        await request.response.close();
        if (!received.isCompleted) received.complete();
      });
      try {
        await tester.pumpWidget(
          MaterialApp(
            home: MachineQrPage(serverUrl: 'http://127.0.0.1:${server.port}'),
          ),
        );
        await tester.pump();
        // Cho plugin hoàn tất khởi tạo trước khi mô phỏng camera đọc QR.
        await Future<void>.delayed(const Duration(milliseconds: 100));
        await tester.pump();
        final scanner = tester.widget<MobileScanner>(
          find.byType(MobileScanner),
        );
        final capture = BarcodeCapture(
          barcodes: [
            Barcode(format: BarcodeFormat.qrCode, rawValue: jsonEncode(packet)),
          ],
        );
        scanner.onDetect!(capture);
        scanner.onDetect!(capture);
        await received.future.timeout(const Duration(seconds: 5));
        for (var i = 0; i < 100; i++) {
          await tester.pump();
          if (find.textContaining('fm_qr_test').evaluate().isNotEmpty) break;
          await Future<void>.delayed(const Duration(milliseconds: 20));
        }
        expect(count, 1);
        expect(find.textContaining('fm_qr_test'), findsOneWidget);
        expect(find.byType(MobileScanner), findsNothing);
        await tester.pumpWidget(const SizedBox());
        await tester.pump();
      } finally {
        await server.close(force: true);
        HttpOverrides.global = previous;
      }
    });
  });
}
