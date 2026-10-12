import 'package:flutter/services.dart';

import '../../../shared/cloud/cloud_error.dart';

class SessionData {
  const SessionData({
    required this.accessToken,
    required this.accessExpiresAt,
    required this.refreshToken,
    required this.refreshExpiresAt,
    required this.userId,
    required this.email,
  });
  final String accessToken,
      accessExpiresAt,
      refreshToken,
      refreshExpiresAt,
      userId,
      email;
  factory SessionData.fromMap(Map<String, dynamic> m) {
    if (m.keys.toSet().difference({
          'access_token',
          'access_expires_at',
          'refresh_token',
          'refresh_expires_at',
          'user',
        }).isNotEmpty ||
        m.length != 5 ||
        m['user'] is! Map) {
      throw const CloudError('INVALID_RESPONSE');
    }
    final u = Map<String, dynamic>.from(m['user'] as Map);
    if (u.length != 2 ||
        u['id'] is! String ||
        u['email'] is! String ||
        [
          'access_token',
          'access_expires_at',
          'refresh_token',
          'refresh_expires_at',
        ].any((k) => m[k] is! String || (m[k] as String).isEmpty)) {
      throw const CloudError('INVALID_RESPONSE');
    }
    final expiry = RegExp(r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{6}Z$');
    for (final key in ['access_expires_at', 'refresh_expires_at']) {
      if (!expiry.hasMatch(m[key]) || DateTime.tryParse(m[key]) == null) {
        throw const CloudError('INVALID_RESPONSE');
      }
    }
    return SessionData(
      accessToken: m['access_token'],
      accessExpiresAt: m['access_expires_at'],
      refreshToken: m['refresh_token'],
      refreshExpiresAt: m['refresh_expires_at'],
      userId: u['id'],
      email: u['email'],
    );
  }
  Map<String, dynamic> toMap() => {
    'access_token': accessToken,
    'access_expires_at': accessExpiresAt,
    'refresh_token': refreshToken,
    'refresh_expires_at': refreshExpiresAt,
    'user': {'id': userId, 'email': email},
  };
}

class SessionStore {
  static const _channel = MethodChannel('flexmix/session');
  Future<SessionData?> load() async {
    try {
      final m = await _channel.invokeMapMethod<String, dynamic>('loadSession');
      return m == null ? null : SessionData.fromMap(m);
    } on PlatformException {
      throw const CloudError('SESSION_STORAGE_ERROR');
    }
  }

  Future<void> save(SessionData value) async {
    try {
      await _channel.invokeMethod<void>('saveSession', value.toMap());
    } on PlatformException {
      throw const CloudError('SESSION_STORAGE_ERROR');
    }
  }

  Future<void> clear() async {
    try {
      await _channel.invokeMethod<void>('clearSession');
    } on PlatformException {
      throw const CloudError('SESSION_STORAGE_ERROR');
    }
  }
}
