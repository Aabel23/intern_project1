import 'package:simple_app/config/routing.dart';
import 'package:simple_app/core/http_json.dart';

Future<Map<String, dynamic>> requestRegistration(
  String serverUrl,
  Map<String, String> data,
) => postJson(serverUrl, Routes.userAccountRegister, data);

Future<Map<String, dynamic>> requestOtp(
  String serverUrl,
  Map<String, String> data,
) => postJson(serverUrl, Routes.userOtpSend, data);

Future<Map<String, dynamic>> verifyOtp(
  String serverUrl,
  Map<String, String> data,
) => postJson(serverUrl, Routes.userOtpVerify, data);
