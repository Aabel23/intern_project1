import 'dart:convert';
import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:simple_app/UI/dashboard/dashboard/main_dashboard.dart';
import 'package:simple_app/feature/machine_register/machine_register_qr.dart';

// Server giả trả trạng thái online, menu và kho theo đúng giao thức thật.
Future<HttpServer> _fakeServer(List<Map<String, dynamic>> received) async {
  final server = await HttpServer.bind(InternetAddress.loopbackIPv4, 0);
  server.listen((request) async {
    Object? reply;
    if (request.uri.path == '/machine/trang-thai') {
      reply = {
        'machine_id': request.uri.queryParameters['machine_id'],
        'online': true,
        'last_seen': 1700000000.0,
      };
    } else {
      final body = jsonDecode(await utf8.decoder.bind(request).join());
      received.add(body as Map<String, dynamic>);
      reply = switch (body['ten']) {
        'xem_menu' => {
          'drinks': [
            {
              'drinkId': 1,
              'name': 'Cà phê sữa',
              'price': 25000.0,
              'category': 'Cà phê',
              'available': true,
              'inStock': true,
            },
            {
              'drinkId': 2,
              'name': 'Trà đào',
              'price': 30000.0,
              'category': 'Trà',
              'available': true,
              'inStock': false,
              'unavailableReason': 'Hết đào',
            },
          ],
        },
        'xem_nguyen_lieu' => {
          'ingredients': [
            {'id': 1, 'name': 'Sữa', 'amount': 500, 'in_stock': true},
            {'id': 2, 'name': 'Đào', 'amount': 0, 'in_stock': false},
          ],
        },
        _ => {'ok': true},
      };
    }
    request.response.headers.contentType = ContentType.json;
    request.response.write(jsonEncode(reply));
    await request.response.close();
  });
  return server;
}

Future<void> _pumpUntil(WidgetTester tester, Finder finder) async {
  for (var i = 0; i < 500 && finder.evaluate().isEmpty; i++) {
    await Future<void>.delayed(const Duration(milliseconds: 20));
    await tester.pump();
  }
}

void main() {
  testWidgets('Nhập mã máy rồi đọc menu, kho và hiện ở các tab', (
    tester,
  ) async {
    await tester.runAsync(() async {
      final previous = HttpOverrides.current;
      HttpOverrides.global = null;
      final received = <Map<String, dynamic>>[];
      final server = await _fakeServer(received);
      try {
        await tester.pumpWidget(
          MaterialApp(
            home: MainDashboard(serverUrl: 'http://127.0.0.1:${server.port}'),
          ),
        );
        expect(find.text('Chưa chọn máy'), findsWidgets);

        await tester.tap(find.text('Máy').last);
        await tester.pumpAndSettle();
        expect(find.text('Quán chưa có máy nào.'), findsOneWidget);
        await tester.tap(find.text('Nhập mã máy'));
        await tester.pumpAndSettle();
        await tester.enterText(find.byType(TextField).last, 'MAY-TEST');
        await tester.tap(find.text('Thêm'));
        await _pumpUntil(tester, find.text('Online · MAY-TEST'));
        expect(find.text('Máy: MAY-TEST'), findsOneWidget);

        // Chờ theo nội dung hiển thị: request đã gửi chưa chắc đã có phản hồi.
        await tester.tap(find.text('Sản phẩm').last);
        await _pumpUntil(tester, find.text('Cà phê sữa'));
        expect(find.textContaining('Thiếu nguyên liệu'), findsOneWidget);

        await tester.tap(find.text('Kho').last);
        await _pumpUntil(tester, find.text('0 g · Hết hàng'));
        expect(find.text('500 g · Còn hàng'), findsOneWidget);

        await tester.tap(find.text('Tổng quan').last);
        await tester.pumpAndSettle();
        expect(find.text('Cần xử lý'), findsOneWidget);

        expect(received.map((r) => r['ten']).toSet(), {
          'xem_menu',
          'xem_nguyen_lieu',
        });
        expect(received.first['machine_id'], 'MAY-TEST');
        expect(tester.takeException(), isNull);
      } finally {
        await server.close(force: true);
        HttpOverrides.global = previous;
      }
    });
  });

  testWidgets('Nút Quét QR mở màn hình đăng ký máy', (tester) async {
    await tester.pumpWidget(
      const MaterialApp(home: MainDashboard(serverUrl: 'http://127.0.0.1:1')),
    );
    await tester.tap(find.text('Máy').last);
    await tester.pumpAndSettle();
    await tester.tap(find.text('Quét QR'));
    await tester.pump();
    await tester.pumpAndSettle();
    expect(find.byType(MachineQrPage), findsOneWidget);
    expect(find.text('Thêm máy bằng QR'), findsOneWidget);
    await tester.pumpWidget(const SizedBox());
    await tester.pumpAndSettle();
  });
}
