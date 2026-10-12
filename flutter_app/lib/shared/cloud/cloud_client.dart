import 'dart:async';
import 'dart:convert';
import 'dart:io';

import 'package:flutter/foundation.dart';

import '../../feature/user_auth/data/session_store.dart';
import 'cloud_config.dart';
import 'cloud_crypto.dart';
import 'cloud_error.dart';

class CloudClient {
  CloudClient({
    required this.config,
    required this.crypto,
    required this.store,
    HttpClient? httpClient,
    Stopwatch? clock,
  }) : _http = httpClient ?? HttpClient(),
       _clock = clock ?? Stopwatch() {
    _clock.start();
  }
  final CloudConfig config;
  final CloudCrypto crypto;
  final SessionStore store;
  final HttpClient _http;
  final Stopwatch _clock;
  Future<SessionData> Function(String)? refreshSession;
  VoidCallback? onSessionExpired;
  Future<SessionData>? _refreshing;
  Future<void>? _bootstrapping;
  int? _serverTime;
  int _receipt = 0;
  Future<void> _bootstrap() async {
    if (_serverTime != null && _clock.elapsedMilliseconds - _receipt < 300000) {
      return;
    }
    if (_bootstrapping != null) return _bootstrapping;
    _bootstrapping = () async {
      final data = await _send(
        '/app/user/session/bootstrap',
        {'v': 1},
        null,
        0,
        const Duration(seconds: 5),
      );
      if (data.length != 1 || data['server_time_ms'] is! int) {
        throw const CloudError('INVALID_RESPONSE');
      }
      _serverTime = data['server_time_ms'];
      _receipt = _clock.elapsedMilliseconds;
    }();
    try {
      await _bootstrapping;
    } finally {
      _bootstrapping = null;
    }
  }

  Future<Map<String, dynamic>> post(
    String route,
    Map<String, dynamic> body, {
    String? accessToken,
    Duration timeout = const Duration(seconds: 10),
  }) async {
    await _bootstrap();
    return _send(
      route,
      body,
      accessToken,
      _serverTime! + _clock.elapsedMilliseconds - _receipt,
      timeout,
    );
  }

  Future<Map<String, dynamic>> _send(
    String route,
    Map<String, dynamic> body,
    String? accessToken,
    int timestamp,
    Duration timeout,
  ) async {
    String? handle;
    HttpClientRequest? request;
    bool active = true;
    try {
      return await (() async {
        final pin = config.trust['hpke'] as Map;
        final sealed = await crypto.sealRequest({
          'route': route,
          'body': body,
          'access_token': accessToken,
          'sent_at_ms': timestamp,
          'kid': pin['kid'],
          'public_key': pin['public_key'],
        });
        handle = sealed['handle'] as String;
        if (!active) {
          await crypto.clearContext(handle!);
          throw const CloudError('TIMEOUT');
        }
        request = await _http.postUrl(config.baseUrl.resolve(route));
        if (!active) {
          request!.abort();
          throw const CloudError('TIMEOUT');
        }
        request!.followRedirects = false;
        request!.headers.contentType = ContentType.json;
        request!.add(utf8.encode(jsonEncode(sealed['envelope'])));
        final response = await request!.close();
        if (response.statusCode >= 300 && response.statusCode < 400) {
          throw const CloudError('TRANSPORT_ERROR');
        }
        if (response.headers.contentType?.mimeType != 'application/json') {
          throw const CloudError('INVALID_RESPONSE');
        }
        final bytes = <int>[];
        await for (final chunk in response) {
          bytes.addAll(chunk);
          if (bytes.length > 65536) throw const CloudError('INVALID_RESPONSE');
        }
        final outer = jsonDecode(utf8.decode(bytes));
        if (outer is! Map) throw const CloudError('INVALID_RESPONSE');
        if (outer.keys.toSet().contains('error')) {
          final error = outer['error'];
          const publicStatus = {
            'INVALID_ENVELOPE': 400,
            'UNSUPPORTED_VERSION': 400,
            'UNKNOWN_KEY': 400,
            'RATE_LIMITED': 429,
          };
          if (outer.length != 2 ||
              outer['pv'] != 1 ||
              error is! Map ||
              error.length != 1 ||
              publicStatus[error['code']] != response.statusCode) {
            throw const CloudError('INVALID_RESPONSE');
          }
          if (error['code'] == 'INVALID_ENVELOPE') _serverTime = null;
          throw CloudError(error['code'], status: response.statusCode);
        }
        final decoded = await crypto.openResponse({
          'handle': handle,
          'http_status': response.statusCode,
          'envelope': Map<String, dynamic>.from(outer),
        });
        if (decoded.length != 3 ||
            decoded['v'] != 1 ||
            decoded['ok'] is! bool) {
          throw const CloudError('INVALID_RESPONSE');
        }
        if (decoded['ok'] == true) {
          if (response.statusCode != 200 || decoded['data'] is! Map) {
            throw const CloudError('INVALID_RESPONSE');
          }
          return Map<String, dynamic>.from(decoded['data']);
        }
        final e = decoded['error'];
        if (e is! Map ||
            e['code'] is! String ||
            e.keys.any((k) => k != 'code' && k != 'retry_after_seconds')) {
          throw const CloudError('INVALID_RESPONSE');
        }
        const statuses = {
          'INVALID_REQUEST': 400,
          'UNSUPPORTED_VERSION': 400,
          'AUTH_FAILED': 401,
          'SESSION_EXPIRED': 401,
          'OTP_INVALID': 409,
          'OTP_EXPIRED': 410,
          'OTP_LOCKED': 429,
          'RATE_LIMITED': 429,
          'MAIL_UNAVAILABLE': 502,
          'SERVICE_UNAVAILABLE': 503,
          'TEST_RECIPIENT_NOT_ALLOWED': 403,
          'FORBIDDEN': 403,
          'MACHINE_UNTRUSTED': 401,
          'ALREADY_OWNED': 409,
          'CLAIM_ACCOUNT_MISMATCH': 403,
          'CLAIM_PROOF_INVALID': 401,
          'CLAIM_EXPIRED': 410,
          'MACHINE_OFFLINE': 503,
          'MACHINE_TIMEOUT': 504,
          'BUSY': 409,
          'REQUEST_CONFLICT': 409,
          'REQUEST_GONE': 410,
        };
        final code = e['code'];
        final retry = e['retry_after_seconds'];
        final needsRetry = {'RATE_LIMITED', 'OTP_LOCKED'}.contains(code);
        if (statuses[code] != response.statusCode ||
            (needsRetry && (retry is! int || retry < 1)) ||
            (!needsRetry && e.containsKey('retry_after_seconds'))) {
          throw const CloudError('INVALID_RESPONSE');
        }
        throw CloudError(
          e['code'],
          status: response.statusCode,
          retryAfterSeconds: retry,
        );
      })().timeout(timeout);
    } on CloudError {
      rethrow;
    } on TimeoutException {
      request?.abort();
      throw const CloudError('TIMEOUT');
    } catch (_) {
      throw const CloudError('TRANSPORT_ERROR');
    } finally {
      active = false;
      if (handle != null) await crypto.clearContext(handle!);
    }
  }

  Future<Map<String, dynamic>> authenticatedPost(
    String route,
    Map<String, dynamic> body, {
    bool retryAfterRefresh = false,
    Duration timeout = const Duration(seconds: 10),
  }) async {
    final session = await store.load();
    if (session == null) {
      onSessionExpired?.call();
      throw const CloudError('SESSION_EXPIRED', status: 401);
    }
    try {
      return await post(
        route,
        body,
        accessToken: session.accessToken,
        timeout: timeout,
      );
    } on CloudError catch (e) {
      // Other 401 codes (claim proof, untrusted machine) are business errors, not an expired session.
      if (e.code != 'SESSION_EXPIRED') rethrow;
      // A request arriving after rotation reuses the new session instead of refreshing again.
      final current = await store.load();
      SessionData restored;
      if (current != null && current.accessToken != session.accessToken) {
        restored = current;
      } else {
        _refreshing ??= refreshSession!(session.refreshToken);
        try {
          restored = await _refreshing!;
        } on CloudError catch (refreshError) {
          if (refreshError.status == 401) {
            await store.clear();
            onSessionExpired?.call();
          }
          rethrow;
        } finally {
          _refreshing = null;
        }
      }
      if (!retryAfterRefresh) rethrow;
      return post(
        route,
        body,
        accessToken: restored.accessToken,
        timeout: timeout,
      );
    }
  }
}
