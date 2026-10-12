import 'dart:convert';
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:simple_app/feature/user_auth/data/session_store.dart';
import 'package:simple_app/shared/cloud/cloud_client.dart';
import 'package:simple_app/shared/cloud/cloud_config.dart';
import 'package:simple_app/shared/cloud/cloud_crypto.dart';

// Keep real HTTP framing while replacing the native crypto channel for this test.
class TestCrypto extends CloudCrypto {
  @override
  Future<Map<String, dynamic>> sealRequest(Map<String, dynamic> args) async => {
    'handle': args['route'],
    'envelope': {'route': args['route'], 'ct': 'test-ciphertext'},
  };

  @override
  Future<Map<String, dynamic>> openResponse(Map<String, dynamic> args) async =>
      Map<String, dynamic>.from(args['envelope']);

  @override
  Future<void> clearContext(String handle) async {}
}

class LoopbackClient extends Fake implements HttpClient {
  LoopbackClient(this.port);
  final int port;
  final client = HttpClient();

  @override
  Future<HttpClientRequest> postUrl(Uri url) => client.postUrl(
    Uri(scheme: 'http', host: '127.0.0.1', port: port, path: url.path),
  );
}

void main() {
  test(
    'bootstrap and account requests use Content-Length instead of chunked',
    () async {
      final server = await HttpServer.bind(InternetAddress.loopbackIPv4, 0);
      final http = LoopbackClient(server.port);
      addTearDown(() async {
        http.client.close(force: true);
        await server.close(force: true);
      });
      final lengths = <int>[];
      final transfers = <String?>[];
      final sizes = <int>[];
      server.listen((request) async {
        lengths.add(request.contentLength);
        transfers.add(
          request.headers.value(HttpHeaders.transferEncodingHeader),
        );
        final bytes = await request.fold<List<int>>(
          [],
          (all, part) => all..addAll(part),
        );
        sizes.add(bytes.length);
        request.response.headers.contentType = ContentType.json;
        request.response.write(
          jsonEncode({
            'v': 1,
            'ok': true,
            'data': request.uri.path.endsWith('/bootstrap')
                ? {'server_time_ms': DateTime.now().millisecondsSinceEpoch}
                : {'message': 'CHECK_EMAIL'},
          }),
        );
        await request.response.close();
      });
      final client = CloudClient(
        config: CloudConfig(
          baseUrl: Uri.parse('https://example.invalid'),
          trust: {
            'v': 1,
            'hpke': {
              'kid': 'server-hpke-1',
              'public_key': base64Url
                  .encode(List.filled(32, 1))
                  .replaceAll('=', ''),
            },
            'signing': {
              'kid': 'server-sign-1',
              'public_key': base64Url
                  .encode([4, ...List.filled(64, 1)])
                  .replaceAll('=', ''),
            },
          },
        ),
        crypto: TestCrypto(),
        store: SessionStore(),
        httpClient: http,
      );
      expect(await client.post('/app/user/account/register', {'v': 1}), {
        'message': 'CHECK_EMAIL',
      });
      expect(lengths, hasLength(2));
      expect(lengths, sizes);
      expect(lengths.every((length) => length > 0), isTrue);
      expect(transfers, [null, null]);
    },
  );
}
