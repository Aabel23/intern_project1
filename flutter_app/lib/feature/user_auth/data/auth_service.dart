import '../../../shared/cloud/cloud_client.dart';
import '../../../shared/cloud/cloud_error.dart';
import 'session_store.dart';

class AuthService {
  AuthService({required this.client, required this.store});
  final CloudClient client;
  final SessionStore store;
  String _email(String value) => value.trim().toLowerCase();
  Future<int> register({
    required String email,
    required String password,
  }) async => _mail(
    await client.post('/app/user/account/register', {
      'v': 1,
      'email': _email(email),
      'password': password,
    }),
  );
  Future<int> sendOtp({required String email}) async => _mail(
    await client.post('/app/user/otp/send', {'v': 1, 'email': _email(email)}),
  );
  int _mail(Map<String, dynamic> data) {
    if (data.length != 2 ||
        data['message'] != 'CHECK_EMAIL' ||
        data['retry_after_seconds'] is! int ||
        data['retry_after_seconds'] < 0) {
      throw const CloudError('INVALID_RESPONSE');
    }
    return data['retry_after_seconds'];
  }

  Future<void> verifyOtp({required String email, required String otp}) async {
    final data = await client.post('/app/user/otp/verify', {
      'v': 1,
      'email': _email(email),
      'otp': otp,
    });
    if (data.length != 1 || data['verified'] != true) {
      throw const CloudError('INVALID_RESPONSE');
    }
  }

  Future<SessionData> login({
    required String email,
    required String password,
  }) async => _save(
    await client.post('/app/user/session/login', {
      'v': 1,
      'email': _email(email),
      'password': password,
    }),
  );
  Future<SessionData> refresh({required String refreshToken}) async => _save(
    await client.post('/app/user/session/refresh', {
      'v': 1,
      'refresh_token': refreshToken,
    }),
  );
  Future<SessionData> _save(Map<String, dynamic> map) async {
    final session = SessionData.fromMap(map);
    await store.save(session);
    return session;
  }

  Future<bool> logout() async {
    try {
      final session = await store.load();
      if (session == null) return true;
      final data = await client.post('/app/user/session/logout', {
        'v': 1,
        'refresh_token': session.refreshToken,
      });
      if (data.length != 1 || data['logged_out'] != true) {
        throw const CloudError('INVALID_RESPONSE');
      }
      return true;
    } on CloudError {
      return false;
    } finally {
      await store.clear();
    }
  }
}
