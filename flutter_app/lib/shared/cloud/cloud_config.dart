import 'dart:convert';
import 'dart:io';

import 'cloud_error.dart';

class CloudConfig {
  CloudConfig({required this.baseUrl, required this.trust}) {
    if ((baseUrl.scheme != 'https' &&
            !(baseUrl.scheme == 'http' && _localIpv4(baseUrl.host))) ||
        baseUrl.host.isEmpty ||
        baseUrl.userInfo.isNotEmpty ||
        baseUrl.hasQuery ||
        baseUrl.hasFragment ||
        !{'', '/'}.contains(baseUrl.path)) {
      throw const CloudError('INVALID_TRUST');
    }
    if (trust.length != 3 || trust['v'] != 1) {
      throw const CloudError('INVALID_TRUST');
    }
    for (final entry in [
      ('hpke', 'server-hpke-1', 32),
      ('signing', 'server-sign-1', 65),
    ]) {
      final p = trust[entry.$1];
      if (p is! Map ||
          p.length != 2 ||
          p['kid'] != entry.$2 ||
          p['public_key'] is! String) {
        throw const CloudError('INVALID_TRUST');
      }
      try {
        final s = p['public_key'] as String;
        final bytes = base64Url.decode(base64Url.normalize(s));
        if (bytes.length != entry.$3 ||
            base64Url.encode(bytes).replaceAll('=', '') != s ||
            (entry.$1 == 'signing' && bytes.first != 4)) {
          throw const FormatException();
        }
      } catch (_) {
        throw const CloudError('INVALID_TRUST');
      }
    }
  }
  final Uri baseUrl;
  final Map<String, Object?> trust;

  static bool _localIpv4(String host) {
    final address = InternetAddress.tryParse(host);
    if (address == null || address.type != InternetAddressType.IPv4) {
      return false;
    }
    final parts = address.rawAddress;
    return parts[0] == 10 ||
        parts[0] == 127 ||
        (parts[0] == 172 && parts[1] >= 16 && parts[1] <= 31) ||
        (parts[0] == 192 && parts[1] == 168);
  }
}
