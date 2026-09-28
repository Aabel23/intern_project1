import 'dart:convert';
import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:simple_app/UI/dashboard/dashboard/main_dashboard.dart';
import 'package:simple_app/UI/dashboard/machine_api.dart';
import 'package:simple_app/feature/data_sync/ingredients_sync.dart';
import 'package:simple_app/UI/login/auth_page.dart';
import 'package:simple_app/feature/machine_register/machine_register_qr.dart';

// Kho máy giả, cùng dạng máy trả qua /app/nhan-kho.
const _kho = {
  'status': 'ok',
  'version': 7,
  'ingredients': [
    {
      'ingredient_id': 1,
      'name': 'Sữa',
      'amount': 500,
      'max_gram': 1000,
      'max_set': true,
      'pump_no': 1,
      'in_stock': true,
    },
    {
      'ingredient_id': 2,
      'name': 'Đào',
      'amount': 0,
      'max_gram': 1500,
      'max_set': false,
      'pump_no': null,
      'in_stock': false,
    },
  ],
};

// Gói menu giả, cùng dạng menu_sync_packet.py của máy: base64(zlib(JSON)).
final _menuPacket = base64Encode(
  ZLibCodec().encode(
    utf8.encode(
      jsonEncode({
        'type': 'menu_sync',
        'v': 1,
        'menu_version': 42,
        'generated_at': '2026-09-28T17:30:00',
        'fields': ['drink_id', 'drink_name', 'price', 'available', 'in_stock'],
        'drinks': [
          [1, 'Cà phê sữa', 25000.0, 1, 1],
          [2, 'Trà đào', 30000.0, 1, 0],
        ],
      }),
    ),
  ),
);

// /app/nhan-kho giả: app gửi đúng version đang có thì up_to_date, khác thì cả danh sách.
Object _replyKho(Map<String, dynamic> body) =>
    body['version'] == _kho['version']
    ? {'status': 'up_to_date', 'version': _kho['version']}
    : _kho;

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
      reply = request.uri.path == '/app/may-cua-toi'
          ? {
              'valid': true,
              'machines': [
                {'machine_id': 'MAY-TEST', 'name': 'MAY-TEST', 'role': 'owner'},
              ],
            }
          : request.uri.path == '/app/nhan-menu'
          ? {'status': 'ok', 'menu_version': 42, 'packet': _menuPacket}
          : request.uri.path == '/app/nhan-kho'
          ? _replyKho(body)
          : {'ok': true};
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
  testWidgets(
    'Máy của tài khoản tự được chọn, đọc menu, kho và hiện ở các tab',
    (tester) async {
      await tester.runAsync(() async {
        final previous = HttpOverrides.current;
        HttpOverrides.global = null;
        final received = <Map<String, dynamic>>[];
        final server = await _fakeServer(received);
        try {
          await tester.pumpWidget(
            MaterialApp(
              home: MainDashboard(
                serverUrl: 'http://127.0.0.1:${server.port}',
                token: 'token-1',
              ),
            ),
          );
          await tester.tap(find.text('Máy').last);
          await _pumpUntil(tester, find.text('Online · Chủ máy · MAY-TEST'));
          expect(find.text('Máy: MAY-TEST'), findsOneWidget);

          // Chờ theo nội dung hiển thị: request đã gửi chưa chắc đã có phản hồi.
          await tester.tap(find.text('Sản phẩm').last);
          await _pumpUntil(tester, find.text('Cà phê sữa'));
          expect(find.textContaining('Thiếu nguyên liệu'), findsOneWidget);

          await tester.tap(find.text('Kho').last);
          await _pumpUntil(tester, find.text('0 / 1500 g'));
          expect(find.text('500 / 1000 g'), findsOneWidget);
          expect(find.text('Bơm 1'), findsOneWidget);
          expect(
            find.text('Mức tối đa đang dùng giá trị mặc định.'),
            findsOneWidget,
          );

          await tester.tap(find.text('Tổng quan').last);
          await tester.pumpAndSettle();
          expect(find.text('Cần xử lý'), findsOneWidget);

          final menus = received.where((r) => r['menu_version'] != null);
          expect(menus, isNotEmpty);
          expect(received.where((r) => r['ten'] != null), isEmpty);
          final khos = received.where((r) => r['version'] != null).toList();
          expect(khos, isNotEmpty);
          expect(khos.every((r) => r['token'] == 'token-1'), isTrue);
          // Relay chỉ nhận lệnh kèm token của người quản lý máy.
          expect(menus.every((r) => r['token'] == 'token-1'), isTrue);
          expect(menus.first['machine_id'], 'MAY-TEST');
          expect(tester.takeException(), isNull);
        } finally {
          await server.close(force: true);
          HttpOverrides.global = previous;
        }
      });
    },
  );

  test(
    'Đồng bộ kho gửi lại version, máy trả up_to_date thì giữ danh sách cũ',
    () async {
      final previous = HttpOverrides.current;
      HttpOverrides.global = null;
      final received = <Map<String, dynamic>>[];
      final server = await _fakeServer(received);
      final inventory = IngredientsSync(
        MachineApi('http://127.0.0.1:${server.port}', token: 'token-1'),
        () => 'MAY-TEST',
      );
      try {
        await inventory.load();
        expect(inventory.error, isNull);
        expect(inventory.ingredients.map((i) => i.name), ['Sữa', 'Đào']);
        expect(inventory.ingredients.first.pumpNumber, 1);
        expect(inventory.ingredients.last.maxSet, isFalse);

        await inventory.load();
        expect(inventory.error, isNull);
        expect(inventory.ingredients.length, 2);
        expect(received.map((r) => r['version']), [0, 7]);

        // Đổi máy thì bỏ version cũ, tải lại toàn bộ.
        inventory.reset();
        await inventory.load();
        expect(received.last['version'], 0);
        expect(inventory.ingredients.length, 2);
      } finally {
        inventory.dispose();
        await server.close(force: true);
        HttpOverrides.global = previous;
      }
    },
  );

  testWidgets('Token hết hạn thì quay về màn hình đăng nhập', (tester) async {
    await tester.runAsync(() async {
      final previous = HttpOverrides.current;
      HttpOverrides.global = null;
      final server = await HttpServer.bind(InternetAddress.loopbackIPv4, 0);
      server.listen((request) async {
        await utf8.decoder.bind(request).join();
        request.response.statusCode = 400;
        request.response.headers.contentType = ContentType.json;
        request.response.write(
          jsonEncode({
            'valid': false,
            'login_required': true,
            'message': 'Phiên đăng nhập hết hạn, hãy đăng nhập lại',
          }),
        );
        await request.response.close();
      });
      try {
        await tester.pumpWidget(
          MaterialApp(
            home: MainDashboard(
              serverUrl: 'http://127.0.0.1:${server.port}',
              token: 'token-cu',
            ),
          ),
        );
        await _pumpUntil(tester, find.byType(AuthPage));
        // Chờ hiệu ứng chuyển trang xong thì dashboard mới bị gỡ khỏi cây.
        for (var i = 0; i < 20; i++) {
          await tester.pump(const Duration(milliseconds: 50));
        }
        expect(find.byType(AuthPage), findsOneWidget);
        expect(find.byType(MainDashboard), findsNothing);
        expect(
          find.text('Phiên đăng nhập hết hạn, hãy đăng nhập lại.'),
          findsOneWidget,
        );
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
