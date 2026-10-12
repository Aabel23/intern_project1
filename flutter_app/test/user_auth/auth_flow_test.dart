import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:simple_app/feature/user_auth/data/auth_service.dart';
import 'package:simple_app/feature/user_auth/data/session_store.dart';
import 'package:simple_app/feature/user_auth/ui/auth_page.dart';
import 'package:simple_app/feature/user_auth/ui/otp_page.dart';
import 'package:simple_app/shared/cloud/cloud_client.dart';
import 'package:simple_app/shared/cloud/cloud_config.dart';
import 'package:simple_app/shared/cloud/cloud_crypto.dart';
import 'package:simple_app/shared/cloud/cloud_error.dart';

import 'dart:convert';

class MemoryStore extends SessionStore {
  SessionData? value;
  @override
  Future<SessionData?> load() async => value;
  @override
  Future<void> save(SessionData data) async {
    value = data;
  }

  @override
  Future<void> clear() async {
    value = null;
  }
}

CloudClient client(SessionStore store) => CloudClient(
  config: CloudConfig(
    baseUrl: Uri.parse('https://example.invalid'),
    trust: {
      'v': 1,
      'hpke': {
        'kid': 'server-hpke-1',
        'public_key': base64Url.encode(List.filled(32, 1)).replaceAll('=', ''),
      },
      'signing': {
        'kid': 'server-sign-1',
        'public_key': base64Url
            .encode([4, ...List.filled(64, 1)])
            .replaceAll('=', ''),
      },
    },
  ),
  crypto: CloudCrypto(),
  store: store,
);
const session = SessionData(
  accessToken: 'test-access',
  accessExpiresAt: '2026-10-12T00:00:00.000000Z',
  refreshToken: 'test-refresh',
  refreshExpiresAt: '2026-11-12T00:00:00.000000Z',
  userId: 'test-user',
  email: 'a@example.invalid',
);

class FakeAuth extends AuthService {
  FakeAuth() : super(client: client(MemoryStore()), store: MemoryStore());
  CloudError? registerError, verifyError;
  Completer<SessionData>? pendingLogin;
  String? registered, resent, verified;
  int verifyCalls = 0;
  @override
  Future<int> register({
    required String email,
    required String password,
  }) async {
    registered = email;
    if (registerError != null) throw registerError!;
    return 0;
  }

  @override
  Future<int> sendOtp({required String email}) async {
    resent = email;
    return 0;
  }

  @override
  Future<void> verifyOtp({required String email, required String otp}) async {
    verified = email;
    verifyCalls++;
    if (verifyError != null) throw verifyError!;
  }

  @override
  Future<SessionData> login({
    required String email,
    required String password,
  }) => pendingLogin!.future;
}

Future<void> registerForm(WidgetTester t, FakeAuth service) async {
  await t.pumpWidget(
    MaterialApp(
      home: AuthPage(authService: service, onAuthenticated: (_) {}),
    ),
  );
  await t.ensureVisible(find.text('Đăng ký ngay'));
  await t.tap(find.text('Đăng ký ngay'));
  await t.pumpAndSettle();
  await t.enterText(find.byKey(const ValueKey('email')), ' A@Example.Invalid ');
  await t.enterText(find.byKey(const ValueKey('password')), 'password-long-15');
  await t.enterText(
    find.byKey(const ValueKey('confirmation')),
    'password-long-15',
  );
  await t.ensureVisible(find.byType(FilledButton));
  await t.tap(find.byType(FilledButton));
  await t.pumpAndSettle();
}

void main() {
  testWidgets('login success navigates once', (t) async {
    final s = FakeAuth()..pendingLogin = Completer();
    int navigated = 0;
    await t.pumpWidget(
      MaterialApp(
        home: AuthPage(authService: s, onAuthenticated: (_) => navigated++),
      ),
    );
    await t.enterText(find.byKey(const ValueKey('email')), 'a@example.invalid');
    await t.enterText(
      find.byKey(const ValueKey('password')),
      'password-long-15',
    );
    await t.ensureVisible(find.byType(FilledButton));
    await t.tap(find.byType(FilledButton));
    await t.pump();
    expect(navigated, 0);
    s.pendingLogin!.complete(session);
    await t.pump();
    expect(navigated, 1);
  });
  testWidgets('verify returns to login without logging in', (t) async {
    final s = FakeAuth();
    await registerForm(t, s);
    await t.enterText(find.byKey(const ValueKey('otp')), '123456');
    await t.tap(find.text('Xác minh'));
    await t.pumpAndSettle();
    expect(find.byType(OtpPage), findsNothing);
    expect(find.text('Email đã xác minh. Vui lòng đăng nhập.'), findsOneWidget);
    expect(find.byKey(const ValueKey('confirmation')), findsNothing);
  });
  testWidgets('one second lock expires without automatic verification', (
    t,
  ) async {
    final s = FakeAuth()
      ..verifyError = const CloudError('OTP_LOCKED', retryAfterSeconds: 1);
    await t.pumpWidget(
      MaterialApp(
        home: OtpPage(
          email: 'a@example.invalid',
          retryAfterSeconds: 0,
          authService: s,
        ),
      ),
    );
    await t.enterText(find.byKey(const ValueKey('otp')), '123456');
    await t.tap(find.text('Xác minh'));
    await t.pump();
    expect(t.widget<FilledButton>(find.byType(FilledButton)).onPressed, isNull);
    await t.runAsync(
      () => Future<void>.delayed(const Duration(milliseconds: 1100)),
    );
    await t.pump(const Duration(seconds: 1));
    expect(
      t.widget<FilledButton>(find.byType(FilledButton)).onPressed,
      isNotNull,
    );
    expect(s.verifyCalls, 1);
    await t.pumpWidget(const SizedBox());
  });

  testWidgets('MAIL_UNAVAILABLE stays on form and offers retry', (t) async {
    final s = FakeAuth()..registerError = const CloudError('MAIL_UNAVAILABLE');
    await registerForm(t, s);
    expect(find.byType(OtpPage), findsNothing);
    expect(find.textContaining('Dịch vụ gửi thư đang lỗi'), findsOneWidget);
    expect(s.registered, 'a@example.invalid');
  });
  testWidgets('login waits for success and ignores disposed response', (
    t,
  ) async {
    final s = FakeAuth()..pendingLogin = Completer();
    int navigated = 0;
    await t.pumpWidget(
      MaterialApp(
        home: AuthPage(authService: s, onAuthenticated: (_) => navigated++),
      ),
    );
    await t.enterText(find.byKey(const ValueKey('email')), 'a@example.invalid');
    await t.enterText(
      find.byKey(const ValueKey('password')),
      'password-long-15',
    );
    await t.ensureVisible(find.text('Đăng nhập').first);
    await t.tap(find.text('Đăng nhập').first);
    await t.pump();
    expect(navigated, 0);
    await t.pumpWidget(const SizedBox());
    s.pendingLogin!.complete(session);
    await t.pump();
    expect(navigated, 0);
    expect(t.takeException(), isNull);
  });
  testWidgets('register email survives resend and OTP failure', (t) async {
    final s = FakeAuth()..verifyError = const CloudError('OTP_INVALID');
    await registerForm(t, s);
    expect(find.textContaining('kiểm tra thư rác'), findsOneWidget);
    await t.tap(find.text('Gửi lại mã'));
    await t.pump();
    expect(s.resent, 'a@example.invalid');
    expect(
      find.textContaining('Nếu địa chỉ email có yêu cầu đăng ký'),
      findsOneWidget,
    );
    await t.enterText(find.byKey(const ValueKey('otp')), '123456');
    await t.tap(find.text('Xác minh'));
    await t.pump();
    expect(s.verified, 'a@example.invalid');
    expect(find.byType(OtpPage), findsOneWidget);
    expect(find.text('Mã OTP không đúng.'), findsOneWidget);
    await t.tap(find.text('Sai email? Quay lại'));
    await t.pumpAndSettle();
    expect(find.byType(OtpPage), findsNothing);
  });
  testWidgets(
    'OTP lock is independent of resend and success never unlocks it',
    (t) async {
      final s = FakeAuth()
        ..verifyError = const CloudError('OTP_LOCKED', retryAfterSeconds: 900);
      await t.pumpWidget(
        MaterialApp(
          home: OtpPage(
            email: 'a@example.invalid',
            retryAfterSeconds: 0,
            authService: s,
          ),
        ),
      );
      await t.enterText(find.byKey(const ValueKey('otp')), '123456');
      await t.tap(find.text('Xác minh'));
      await t.pump();
      expect(
        t.widget<FilledButton>(find.byType(FilledButton)).onPressed,
        isNull,
      );
      await t.tap(find.text('Gửi lại mã'));
      await t.pump();
      expect(s.resent, 'a@example.invalid');
      expect(
        t.widget<FilledButton>(find.byType(FilledButton)).onPressed,
        isNull,
      );
      expect(s.verifyCalls, 1);
      await t.pumpWidget(const SizedBox());
      await t.pump(const Duration(seconds: 2));
      expect(t.takeException(), isNull);
    },
  );
}
