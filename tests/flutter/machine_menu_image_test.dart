import 'dart:convert';
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:simple_app/core/server_client.dart';
import 'package:simple_app/feature/machine_menu/machine_menu_image.dart';

// Máy giả: trả ảnh theo bảng images (drink_id → byte); món trong `later` để con_lai.
Future<({HttpServer server, List<List<int>> asked})> fakeMachine(
  Map<int, List<int>> images, {
  Set<int> later = const {},
  bool wrongHash = false,
}) async {
  final asked = <List<int>>[];
  final server = await HttpServer.bind(InternetAddress.loopbackIPv4, 0);
  server.listen((request) async {
    final body = jsonDecode(await utf8.decoder.bind(request).join()) as Map;
    final ids = [
      for (final item in body['anh'] as List) item['drink_id'] as int,
    ];
    asked.add(ids);
    final rest = ids.where(later.contains).toList();
    later = later.difference(rest.toSet());
    request.response
      ..headers.contentType = ContentType.json
      ..write(
        jsonEncode({
          'status': 'ok',
          'con_lai': rest,
          'anh': [
            for (final id in ids.where((id) => !rest.contains(id)))
              images.containsKey(id)
                  ? {
                      'drink_id': id,
                      'image_hash': crc32(images[id]!) + (wrongHash ? 1 : 0),
                      'mime': 'image/webp',
                      'data': base64Encode(images[id]!),
                    }
                  : {'drink_id': id, 'loi': 'không có ảnh'},
          ],
        }),
      );
    await request.response.close();
  });
  return (server: server, asked: asked);
}

void main() {
  test('crc32 matches zlib.crc32', () {
    expect(crc32(utf8.encode('123456789')), 0xCBF43926);
  });

  test('downloads missing images once, then reads them from disk', () async {
    final root = await Directory.systemTemp.createTemp('menu_image_test');
    addTearDown(() => root.delete(recursive: true));
    final images = {1: utf8.encode('peach'), 2: utf8.encode('milk tea')};
    final machine = await fakeMachine(images);
    addTearDown(() => machine.server.close(force: true));
    final api = ServerClient('http://127.0.0.1:${machine.server.port}');
    final drinks = [
      (id: 1, imageHash: crc32(images[1]!)),
      (id: 2, imageHash: crc32(images[2]!)),
      (id: 3, imageHash: 0),
    ];

    final cache = MenuImageCache(api, () => 'fm_1', root: root);
    addTearDown(cache.dispose);
    await cache.sync(drinks);
    expect(machine.asked, [
      [1, 2],
    ]);
    expect(await cache.fileOf(1)!.readAsBytes(), images[1]);
    expect(cache.fileOf(3), isNull);

    // App mở lại: cache mới, cùng thư mục, không hỏi máy nữa.
    final reopened = MenuImageCache(api, () => 'fm_1', root: root);
    addTearDown(reopened.dispose);
    await reopened.sync(drinks);
    expect(machine.asked, hasLength(1));
    expect(await reopened.fileOf(2)!.readAsBytes(), images[2]);

    // Đổi ảnh món 1: hash mới nên chỉ xin lại món đó.
    images[1] = utf8.encode('peach v2');
    await reopened.sync([(id: 1, imageHash: crc32(images[1]!)), drinks[1]]);
    expect(machine.asked.last, [1]);
    expect(await reopened.fileOf(1)!.readAsBytes(), images[1]);
  });

  test('follows con_lai and skips images that fail the hash check', () async {
    final root = await Directory.systemTemp.createTemp('menu_image_test');
    addTearDown(() => root.delete(recursive: true));
    final images = {for (var i = 1; i <= 25; i++) i: utf8.encode('drink $i')};
    final machine = await fakeMachine(images, later: {2, 21});
    addTearDown(() => machine.server.close(force: true));
    final cache = MenuImageCache(
      ServerClient('http://127.0.0.1:${machine.server.port}'),
      () => 'fm_1',
      root: root,
    );
    addTearDown(cache.dispose);
    await cache.sync([
      for (final e in images.entries) (id: e.key, imageHash: crc32(e.value)),
    ]);
    // Lượt 1: 20 món, món 2 vào con_lai; lượt 2: 5 + món 2, món 21 vào con_lai; lượt 3: món 21.
    expect(machine.asked.map((ids) => ids.length), [20, 6, 1]);
    expect([
      for (var i = 1; i <= 25; i++) cache.fileOf(i),
    ], everyElement(isNotNull));

    final bad = await fakeMachine({1: utf8.encode('x')}, wrongHash: true);
    addTearDown(() => bad.server.close(force: true));
    final strict = MenuImageCache(
      ServerClient('http://127.0.0.1:${bad.server.port}'),
      () => 'fm_2',
      root: root,
    );
    addTearDown(strict.dispose);
    await strict.sync([(id: 1, imageHash: crc32(utf8.encode('x')))]);
    expect(strict.fileOf(1), isNull);
  });
}
