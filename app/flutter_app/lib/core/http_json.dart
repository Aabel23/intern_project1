import 'dart:convert';
import 'dart:io';

Future<Map<String, dynamic>> postJson(
  String serverUrl,
  String path,
  Map<String, String> data,
) async {
  final client = HttpClient()..connectionTimeout = const Duration(seconds: 5);
  try {
    return await (() async {
      final request = await client.postUrl(Uri.parse('$serverUrl$path'));
      final payload = utf8.encode(jsonEncode(data));
      request.headers.contentType = ContentType.json;
      request.contentLength = payload.length;
      request.add(payload);
      final response = await request.close();
      final body = await utf8.decoder.bind(response).join();
      return jsonDecode(body) as Map<String, dynamic>;
    })().timeout(const Duration(seconds: 25));
  } finally {
    client.close(force: true);
  }
}
