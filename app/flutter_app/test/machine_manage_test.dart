import 'dart:convert';
import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:simple_app/UI/dashboard/dashboard/main_dashboard.dart';

void main() {
  testWidgets('Chủ máy đổi tên rồi gỡ máy khỏi quán', (tester) async {
    await tester.runAsync(() async {
      final previous = HttpOverrides.current;
      HttpOverrides.global = null;
      final server = await HttpServer.bind(InternetAddress.loopbackIPv4, 0);
      final bodies = <String, Map<String, dynamic>>{};
      var machines = [
        {'machine_id': 'fm_1', 'name': 'FlexMix-01', 'role': 'owner'},
      ];
      server.listen((request) async {
        final text = await utf8.decoder.bind(request).join();
        Object reply;
        if (request.uri.path == '/machine/trang-thai') {
          reply = {'machine_id': 'fm_1', 'online': false, 'last_seen': null};
        } else {
          final body = jsonDecode(text) as Map<String, dynamic>;
          bodies[request.uri.path] = body;
          reply = switch (request.uri.path) {
            '/app/may-cua-toi' => {'valid': true, 'machines': machines},
            '/app/doi-ten-may' => {'valid': true, 'name': body['name']},
            '/app/go-may' => {'valid': true, 'deleted': true},
            _ => {'valid': false, 'message': 'sai đường dẫn'},
          };
          if (request.uri.path == '/app/doi-ten-may') {
            machines = [
              {'machine_id': 'fm_1', 'name': body['name'], 'role': 'owner'},
            ];
          }
          if (request.uri.path == '/app/go-may') machines = [];
        }
        request.response.headers.contentType = ContentType.json;
        request.response.write(jsonEncode(reply));
        await request.response.close();
      });
      Future<void> waitFor(bool Function() done) async {
        for (var i = 0; i < 200 && !done(); i++) {
          await Future<void>.delayed(const Duration(milliseconds: 20));
          await tester.pump();
        }
      }

      Future<void> pumpUntil(Finder finder) =>
          waitFor(() => finder.evaluate().isNotEmpty);

      Future<void> openMenu() async {
        await tester.tap(
          find.descendant(
            of: find.byType(Card),
            matching: find.byType(PopupMenuButton<String>),
          ),
        );
        await tester.pump();
        await tester.pump(const Duration(milliseconds: 400));
      }

      try {
        await tester.pumpWidget(
          MaterialApp(
            home: MainDashboard(
              serverUrl: 'http://127.0.0.1:${server.port}',
              token: 'owner-token',
            ),
          ),
        );
        await tester.tap(find.text('Máy').last);
        await pumpUntil(find.text('FlexMix-01'));

        await openMenu();
        await tester.tap(find.text('Đổi tên'));
        await tester.pump(const Duration(milliseconds: 400));
        await tester.enterText(find.byType(TextField).last, 'FlexMix-Moi');
        await tester.tap(find.text('Lưu'));
        await waitFor(() => find.byType(TextField).evaluate().isEmpty);
        await pumpUntil(find.text('FlexMix-Moi'));
        expect(bodies['/app/doi-ten-may'], {
          'machine_id': 'fm_1',
          'name': 'FlexMix-Moi',
          'token': 'owner-token',
        });

        await openMenu();
        await tester.tap(find.text('Gỡ khỏi quán'));
        await tester.pump(const Duration(milliseconds: 400));
        await tester.tap(find.text('Gỡ máy'));
        await pumpUntil(find.text('Quán chưa có máy nào.'));
        expect(bodies['/app/go-may'], {
          'machine_id': 'fm_1',
          'token': 'owner-token',
        });
        expect(find.text('FlexMix-Moi'), findsNothing);
        expect(find.text('Chưa chọn máy'), findsWidgets);
        await tester.pumpWidget(const SizedBox());
      } finally {
        await server.close(force: true);
        HttpOverrides.global = previous;
      }
    });
  });
}
