import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:simple_app/shared/cloud/cloud_config.dart';
import 'package:simple_app/shared/cloud/cloud_error.dart';

void main() {
  final trust = <String, Object?>{
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
  };

  test('LAN HTTP and HTTPS use the same pinned trust', () {
    expect(
      CloudConfig(
        baseUrl: Uri.parse('http://192.168.1.10:8080'),
        trust: trust,
      ).baseUrl.scheme,
      'http',
    );
    expect(
      CloudConfig(
        baseUrl: Uri.parse('https://example.invalid'),
        trust: trust,
      ).baseUrl.scheme,
      'https',
    );
    for (final url in [
      'http://example.invalid',
      'http://8.8.8.8',
      'http://192.168.1.10/path',
    ]) {
      expect(
        () => CloudConfig(baseUrl: Uri.parse(url), trust: trust),
        throwsA(isA<CloudError>()),
      );
    }
  });
}
