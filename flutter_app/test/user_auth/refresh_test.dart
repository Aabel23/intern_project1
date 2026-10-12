import 'dart:async';

import 'package:flutter_test/flutter_test.dart';
import 'package:simple_app/shared/cloud/cloud_client.dart';
import 'package:simple_app/shared/cloud/cloud_crypto.dart';
import 'package:simple_app/shared/cloud/cloud_error.dart';
import 'package:simple_app/feature/user_auth/data/session_store.dart';

import 'auth_flow_test.dart' as fixture;

class UnauthorizedClient extends CloudClient {
  UnauthorizedClient(SessionStore store)
    : super(
        config: fixture.client(store).config,
        crypto: CloudCrypto(),
        store: store,
      );
  int attempts = 0;
  @override
  Future<Map<String, dynamic>> post(
    String route,
    Map<String, dynamic> body, {
    String? accessToken,
    Duration timeout = const Duration(seconds: 10),
  }) async {
    attempts++;
    if (accessToken == fixture.session.accessToken) {
      throw const CloudError('SESSION_EXPIRED', status: 401);
    }
    return {'answer': true};
  }
}

void main() {
  test('concurrent 401 has one refresh and write is not replayed', () async {
    final store = fixture.MemoryStore()..value = fixture.session;
    final c = UnauthorizedClient(store);
    final pending = Completer<SessionData>();
    int refreshes = 0;
    c.refreshSession = (_) {
      refreshes++;
      return pending.future;
    };
    final a = c.authenticatedPost('/write', {'v': 1});
    final b = c.authenticatedPost('/write', {'v': 1});
    final expectedA = expectLater(a, throwsA(isA<CloudError>()));
    final expectedB = expectLater(b, throwsA(isA<CloudError>()));
    await Future<void>.delayed(Duration.zero);
    expect(refreshes, 1);
    pending.complete(fixture.session);
    await Future.wait([expectedA, expectedB]);
    expect(c.attempts, 2);
  });
  test('refresh 401 clears session and reports expiration', () async {
    final store = fixture.MemoryStore()..value = fixture.session;
    final c = UnauthorizedClient(store);
    int expired = 0;
    c.onSessionExpired = () => expired++;
    c.refreshSession = (_) async =>
        throw const CloudError('SESSION_EXPIRED', status: 401);
    await expectLater(
      c.authenticatedPost('/read', {'v': 1}, retryAfterRefresh: true),
      throwsA(isA<CloudError>()),
    );
    expect(store.value, isNull);
    expect(expired, 1);
  });
  test('refresh network failure keeps session', () async {
    final store = fixture.MemoryStore()..value = fixture.session;
    final c = UnauthorizedClient(store);
    c.refreshSession = (_) async => throw const CloudError('TIMEOUT');
    await expectLater(
      c.authenticatedPost('/read', {'v': 1}),
      throwsA(isA<CloudError>()),
    );
    expect(store.value, same(fixture.session));
  });
}
