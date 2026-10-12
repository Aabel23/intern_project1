import "dart:async";
import 'dart:convert';
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:simple_app/shared/cloud/cloud_client.dart';
import 'package:simple_app/shared/cloud/cloud_crypto.dart';
import 'package:simple_app/shared/cloud/cloud_error.dart';

import 'auth_flow_test.dart' as fixture;

class FakeHeaders implements HttpHeaders {
  @override
  ContentType? contentType = ContentType.json;
  @override
  dynamic noSuchMethod(Invocation invocation) => null;
}

class FakeResponse extends Stream<List<int>> implements HttpClientResponse {
  FakeResponse(this.statusCode, [this.body = '{}']);
  final String body;
  @override
  final int statusCode;
  @override
  final HttpHeaders headers = FakeHeaders();
  @override
  StreamSubscription<List<int>> listen(
    void Function(List<int>)? onData, {
    Function? onError,
    void Function()? onDone,
    bool? cancelOnError,
  }) => Stream.value(utf8.encode(body)).listen(
    onData,
    onError: onError,
    onDone: onDone,
    cancelOnError: cancelOnError,
  );
  @override
  dynamic noSuchMethod(Invocation invocation) => null;
}

class FakeRequest implements HttpClientRequest {
  FakeRequest(this.status);
  final int status;
  @override
  final HttpHeaders headers = FakeHeaders();
  @override
  bool followRedirects = false;
  @override
  void add(List<int> data) {}
  @override
  Future<HttpClientResponse> close() async => FakeResponse(status);
  @override
  dynamic noSuchMethod(Invocation invocation) => null;
}

class FakeHttp implements HttpClient {
  FakeHttp(this.status);
  final int status;
  @override
  Future<HttpClientRequest> postUrl(Uri url) async =>
      FakeRequest(url.path.endsWith('bootstrap') ? 200 : status);
  @override
  dynamic noSuchMethod(Invocation invocation) => null;
}

class DecodedCrypto extends CloudCrypto {
  DecodedCrypto(this.result);
  final Map<String, dynamic> result;
  int opened = 0, cleared = 0;
  @override
  Future<Map<String, dynamic>> sealRequest(Map<String, dynamic> args) async => {
    'handle': 'test-handle',
    'envelope': {},
  };
  @override
  Future<Map<String, dynamic>> openResponse(Map<String, dynamic> args) async =>
      opened++ == 0
      ? {
          'v': 1,
          'ok': true,
          'data': {'server_time_ms': 1791763200000},
        }
      : result;
  @override
  Future<void> clearContext(String handle) async {
    cleared++;
  }
}

class MutableClock extends Stopwatch {
  int milliseconds = 0;
  @override
  int get elapsedMilliseconds => milliseconds;
  @override
  void start() {}
}

class PublicRequest extends FakeRequest {
  PublicRequest(super.status, this.body);
  final String body;
  @override
  Future<HttpClientResponse> close() async => FakeResponse(status, body);
}

class RecordingHttp extends FakeHttp {
  RecordingHttp() : super(200);
  final routes = <String>[];
  bool invalid = false;
  @override
  Future<HttpClientRequest> postUrl(Uri url) async {
    routes.add(url.path);
    if (invalid && !url.path.endsWith('bootstrap')) {
      invalid = false;
      return PublicRequest(400, '{"pv":1,"error":{"code":"INVALID_ENVELOPE"}}');
    }
    return FakeRequest(200);
  }
}

class RoutedCrypto extends CloudCrypto {
  @override
  Future<Map<String, dynamic>> sealRequest(Map<String, dynamic> args) async => {
    'handle': args['route'],
    'envelope': {},
  };
  @override
  Future<Map<String, dynamic>> openResponse(Map<String, dynamic> args) async =>
      {
        'v': 1,
        'ok': true,
        'data': args['handle'].endsWith('bootstrap')
            ? {'server_time_ms': 1791763200000}
            : {'done': true},
      };
  @override
  Future<void> clearContext(String handle) async {}
}

void main() {
  test('INVALID_ENVELOPE clears time cache without replaying write', () async {
    final store = fixture.MemoryStore();
    final http = RecordingHttp()..invalid = true;
    final c = CloudClient(
      config: fixture.client(store).config,
      crypto: RoutedCrypto(),
      store: store,
      httpClient: http,
    );
    await expectLater(
      c.post('/write', {'v': 1}),
      throwsA(
        isA<CloudError>().having((e) => e.code, 'code', 'INVALID_ENVELOPE'),
      ),
    );
    expect(http.routes, ['/app/user/session/bootstrap', '/write']);
    await c.post('/write', {'v': 1});
    expect(http.routes, [
      '/app/user/session/bootstrap',
      '/write',
      '/app/user/session/bootstrap',
      '/write',
    ]);
  });
  test('time cache expires at monotonic 300 seconds', () async {
    final store = fixture.MemoryStore();
    final http = RecordingHttp();
    final clock = MutableClock();
    final c = CloudClient(
      config: fixture.client(store).config,
      crypto: RoutedCrypto(),
      store: store,
      httpClient: http,
      clock: clock,
    );
    await c.post('/read', {'v': 1});
    clock.milliseconds = 299999;
    await c.post('/read', {'v': 1});
    expect(http.routes.where((r) => r.endsWith('bootstrap')).length, 1);
    clock.milliseconds = 300000;
    await c.post('/read', {'v': 1});
    expect(http.routes.where((r) => r.endsWith('bootstrap')).length, 2);
  });
  for (final code in ['OTP_LOCKED', 'RATE_LIMITED']) {
    for (final retry in [null, 0, '900']) {
      test('$code rejects missing or invalid retry $retry', () async {
        final crypto = DecodedCrypto({
          'v': 1,
          'ok': false,
          'error': {'code': code, 'retry_after_seconds': ?retry},
        });
        final store = fixture.MemoryStore();
        final c = CloudClient(
          config: fixture.client(store).config,
          crypto: crypto,
          store: store,
          httpClient: FakeHttp(429),
        );
        await expectLater(
          c.post('/app/user/otp/verify', {'v': 1}),
          throwsA(
            isA<CloudError>().having((e) => e.code, 'code', 'INVALID_RESPONSE'),
          ),
        );
        expect(crypto.cleared, 2);
      });
    }
  }
  test('error HTTP status must match code', () async {
    final crypto = DecodedCrypto({
      'v': 1,
      'ok': false,
      'error': {'code': 'MAIL_UNAVAILABLE'},
    });
    final store = fixture.MemoryStore();
    final c = CloudClient(
      config: fixture.client(store).config,
      crypto: crypto,
      store: store,
      httpClient: FakeHttp(401),
    );
    await expectLater(
      c.post('/app/user/account/register', {'v': 1}),
      throwsA(
        isA<CloudError>().having((e) => e.code, 'code', 'INVALID_RESPONSE'),
      ),
    );
  });
  test('OTP lock preserves valid retry metadata', () async {
    final crypto = DecodedCrypto({
      'v': 1,
      'ok': false,
      'error': {'code': 'OTP_LOCKED', 'retry_after_seconds': 900},
    });
    final store = fixture.MemoryStore();
    final c = CloudClient(
      config: fixture.client(store).config,
      crypto: crypto,
      store: store,
      httpClient: FakeHttp(429),
    );
    await expectLater(
      c.post('/app/user/otp/verify', {'v': 1}),
      throwsA(
        isA<CloudError>().having((e) => e.retryAfterSeconds, 'retry', 900),
      ),
    );
  });
}
