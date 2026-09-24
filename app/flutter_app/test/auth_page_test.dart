import 'dart:convert';
import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:simple_app/main.dart';
import 'package:simple_app/UI/dashboard/dashboard/main_dashboard.dart';
import 'package:simple_app/UI/login/auth_page.dart';
import 'package:simple_app/UI/login/otp_page.dart';

void main() {
  testWidgets('Nút gửi lại mã chỉ bật sau 60 giây', (tester) async {
    await tester.pumpWidget(
      const MaterialApp(
        home: OtpPage(
          email: 'an@example.com',
          registrationId: 'test-session',
          serverUrl: 'http://127.0.0.1:8000',
        ),
      ),
    );
    expect(find.text('Gửi lại mã sau 60s'), findsOneWidget);
    await tester.pump(const Duration(seconds: 59));
    expect(
      tester.widget<TextButton>(find.byType(TextButton)).onPressed,
      isNull,
    );
    await tester.pump(const Duration(seconds: 1));
    expect(
      tester.widget<TextButton>(find.byType(TextButton)).onPressed,
      isNotNull,
    );
    expect(find.text('Gửi lại mã'), findsOneWidget);
  });

  testWidgets('Gửi JSON đăng ký và hiển thị kết quả server', (tester) async {
    await tester.runAsync(() async {
      final previous = HttpOverrides.current;
      HttpOverrides.global = null;
      final server = await HttpServer.bind(InternetAddress.loopbackIPv4, 0);
      Map<String, dynamic>? received;
      Map<String, dynamic>? otpRequest;
      final paths = <String>[];
      int? contentLength;
      int? bodyLength;
      server.listen((request) async {
        paths.add(request.uri.path);
        contentLength = request.contentLength;
        final body = await utf8.decoder.bind(request).join();
        bodyLength = utf8.encode(body).length;
        if (request.uri.path == '/app/dang-ky-nguoi-dung') {
          received = jsonDecode(body);
        }
        if (request.uri.path == '/app/xac-minh-otp') {
          otpRequest = jsonDecode(body);
        }
        request.response.headers.contentType = ContentType.json;
        request.response.write(
          jsonEncode({
            'valid': true,
            'registration_id': 'test-session',
            'message': request.uri.path == '/app/xac-minh-otp'
                ? 'Tạo tài khoản thành công'
                : 'Đã gửi mã xác minh tới email',
          }),
        );
        await request.response.close();
      });
      try {
        await tester.pumpWidget(
          MaterialApp(
            home: AuthPage(serverUrl: 'http://127.0.0.1:${server.port}'),
          ),
        );
        await tester.ensureVisible(find.text('Đăng ký ngay'));
        await tester.tap(find.text('Đăng ký ngay'));
        await tester.pumpAndSettle();
        for (final field in {
          'name': 'Ngọc Trân',
          'username': 'an',
          'email': 'an@example.com',
          'password': 'password123',
          'confirmation': 'password123',
        }.entries) {
          await tester.enterText(find.byKey(ValueKey(field.key)), field.value);
        }
        await tester.ensureVisible(find.byType(FilledButton));
        await tester.tap(find.byType(FilledButton));
        for (var i = 0; i < 100; i++) {
          await Future<void>.delayed(const Duration(milliseconds: 20));
          await tester.pump();
          if (find.text('Xác minh email').evaluate().isNotEmpty) {
            break;
          }
        }
        expect(paths, ['/app/dang-ky-nguoi-dung']);
        expect(contentLength, bodyLength);
        expect(contentLength, greaterThan(0));
        expect(received!['request_id'], matches(RegExp(r'^[a-f0-9]{32}$')));
        received!.remove('request_id');
        expect(received, {
          'full_name': 'Ngọc Trân',
          'username': 'an',
          'email': 'an@example.com',
          'password': 'password123',
        });
        expect(find.text('Xác minh email'), findsOneWidget);
        expect(find.text('Nhập mã OTP cho an@example.com'), findsOneWidget);
        expect(find.byKey(const ValueKey('otp')), findsOneWidget);
        await tester.enterText(find.byKey(const ValueKey('otp')), '012345');
        await tester.tap(find.text('Xác minh'));
        for (var i = 0; i < 100; i++) {
          await Future<void>.delayed(const Duration(milliseconds: 20));
          await tester.pump();
          if (find.text('Tạo tài khoản thành công').evaluate().isNotEmpty) {
            break;
          }
        }
        expect(paths, ['/app/dang-ky-nguoi-dung', '/app/xac-minh-otp']);
        expect(otpRequest, {
          'registration_id': 'test-session',
          'code': '012345',
        });
        expect(find.text('Tạo tài khoản thành công'), findsWidgets);
        expect(
          tester
              .widget<FilledButton>(
                find.widgetWithText(FilledButton, 'Tài khoản đã tạo'),
              )
              .onPressed,
          isNull,
        );
        expect(
          tester.widget<TextButton>(find.byType(TextButton).last).onPressed,
          isNull,
        );
      } finally {
        await server.close(force: true);
        HttpOverrides.global = previous;
      }
    });
  });
  testWidgets('Đăng ký kiểm tra mật khẩu và chuyển về đăng nhập', (
    tester,
  ) async {
    await tester.pumpWidget(const MainApp());
    await tester.ensureVisible(find.text('Đăng ký ngay'));
    await tester.tap(find.text('Đăng ký ngay'));
    await tester.pumpAndSettle();

    await tester.enterText(find.byKey(const ValueKey('name')), 'Ngọc Trân');
    await tester.enterText(find.byKey(const ValueKey('username')), 'tran');
    await tester.enterText(
      find.byKey(const ValueKey('email')),
      'tran@example.com',
    );
    await tester.enterText(
      find.byKey(const ValueKey('password')),
      'password123',
    );
    await tester.enterText(
      find.byKey(const ValueKey('confirmation')),
      'different',
    );
    final submit = find.byType(FilledButton);
    await tester.ensureVisible(submit);
    await tester.tap(submit);
    await tester.pumpAndSettle();
    expect(find.text('Mật khẩu chưa khớp.'), findsOneWidget);

    await tester.ensureVisible(find.text('Đăng nhập'));
    await tester.tap(find.text('Đăng nhập'));
    await tester.pumpAndSettle();
    expect(find.byKey(const ValueKey('confirmation')), findsNothing);
    expect(find.byKey(const ValueKey('name')), findsNothing);
    expect(tester.takeException(), isNull);
  });

  testWidgets('Đăng nhập gửi username/password rồi hỏi kết quả xác minh', (
    tester,
  ) async {
    await tester.runAsync(() async {
      final previous = HttpOverrides.current;
      HttpOverrides.global = null;
      final server = await HttpServer.bind(InternetAddress.loopbackIPv4, 0);
      final received = <String, Map<String, dynamic>>{};
      var accept = false;
      server.listen((request) async {
        final body = jsonDecode(await utf8.decoder.bind(request).join());
        received[request.uri.path] = body as Map<String, dynamic>;
        final reply = request.uri.path == '/app/dang-nhap'
            ? {'valid': true, 'login_id': 'phien-1'}
            : accept
            ? {'valid': true, 'message': 'Đăng nhập thành công'}
            : {'valid': false, 'message': 'Sai mật khẩu'};
        request.response.headers.contentType = ContentType.json;
        request.response.write(jsonEncode(reply));
        await request.response.close();
      });
      Future<void> submit() async {
        final button = find.byType(FilledButton);
        await tester.ensureVisible(button);
        await tester.tap(button);
        for (var i = 0; i < 100; i++) {
          await Future<void>.delayed(const Duration(milliseconds: 20));
          await tester.pump();
        }
      }

      try {
        await tester.pumpWidget(
          MaterialApp(
            home: AuthPage(serverUrl: 'http://127.0.0.1:${server.port}'),
          ),
        );
        expect(find.byKey(const ValueKey('email')), findsNothing);
        await tester.enterText(find.byKey(const ValueKey('username')), 'an');
        await tester.enterText(
          find.byKey(const ValueKey('password')),
          'matkhau',
        );

        await submit();
        expect(received['/app/dang-nhap']!['username'], 'an');
        expect(received['/app/dang-nhap']!['password'], 'matkhau');
        final verify = received['/app/xac-minh-dang-nhap']!;
        expect(verify['request_id'], received['/app/dang-nhap']!['request_id']);
        expect(verify['login_id'], 'phien-1');
        expect(find.text('Sai mật khẩu'), findsOneWidget);
        expect(find.byType(AuthPage), findsOneWidget);

        accept = true;
        await submit();
        await tester.pumpAndSettle();
        expect(find.byType(MainDashboard), findsOneWidget);
      } finally {
        await server.close(force: true);
        HttpOverrides.global = previous;
      }
    });
  });
}
