import 'package:flutter/services.dart';

import 'cloud_error.dart';

class CloudCrypto {
  static const _channel = MethodChannel('flexmix/crypto');
  Future<Map<String, dynamic>> sealRequest(Map<String, dynamic> args) =>
      _map('sealRequest', args);
  Future<Map<String, dynamic>> openResponse(Map<String, dynamic> args) =>
      _map('openResponse', args);
  Future<Map<String, dynamic>> _map(
    String method,
    Map<String, dynamic> args,
  ) async {
    try {
      final result = await _channel.invokeMapMethod<String, dynamic>(
        method,
        args,
      );
      if (result == null) throw const CloudError('INVALID_RESPONSE');
      return result;
    } on PlatformException catch (e) {
      throw CloudError(e.code);
    }
  }

  Future<void> clearContext(String handle) async {
    try {
      await _channel.invokeMethod<void>('clearContext', {'handle': handle});
    } on PlatformException catch (e) {
      throw CloudError(e.code);
    }
  }
}
