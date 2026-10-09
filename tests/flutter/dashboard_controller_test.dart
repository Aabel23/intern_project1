import 'dart:async';
import 'dart:convert';
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:simple_app/feature/dashboard/dashboard_controller.dart';
import 'package:simple_app/core/server_client.dart';

// Server giả: /app/user/machine/list trả danh sách máy đang giữ trong [machines];
// máy offline nên lệnh xem menu/đồng bộ kho trả lỗi offline như server thật.
Future<HttpServer> _fakeServer(List<Map<String, String>> machines) async {
  final server = await HttpServer.bind(InternetAddress.loopbackIPv4, 0);
  server.listen((request) async {
    await utf8.decoder.bind(request).join();
    Object reply;
    var status = 200;
    switch (request.uri.path) {
      case '/app/user/machine/list':
        reply = {'valid': true, 'machines': machines};
      case '/app/machine/status/get':
        reply = {'online': false};
      default:
        // Menu, kho: server thật trả 503 khi máy offline.
        status = 503;
        reply = {'loi': 'Máy đang offline'};
    }
    request.response
      ..statusCode = status
      ..headers.contentType = ContentType.json
      ..write(jsonEncode(reply));
    await request.response.close();
  });
  return server;
}

// Server giả giữ các request /app/user/machine/list để test tự chọn thứ tự trả lời;
// các route khác trả ngay như máy offline.
Future<(HttpServer, StreamIterator<HttpRequest>)> _heldListServer() async {
  final server = await HttpServer.bind(InternetAddress.loopbackIPv4, 0);
  final lists = StreamController<HttpRequest>();
  server.listen((request) async {
    await utf8.decoder.bind(request).join();
    if (request.uri.path == '/app/user/machine/list') {
      lists.add(request);
      return;
    }
    final status = request.uri.path == '/app/machine/status/get' ? 200 : 503;
    request.response
      ..statusCode = status
      ..headers.contentType = ContentType.json
      ..write(
        jsonEncode(status == 200 ? {'online': false} : {'loi': 'offline'}),
      );
    await request.response.close();
  });
  return (server, StreamIterator(lists.stream));
}

Future<void> _replyMachines(HttpRequest request, List<String> ids) async {
  request.response
    ..headers.contentType = ContentType.json
    ..write(
      jsonEncode({
        'valid': true,
        'machines': [
          for (final id in ids) {'machine_id': id, 'name': id, 'role': 'owner'},
        ],
      }),
    );
  await request.response.close();
}

void main() {
  test('Late machine list cannot overwrite a newer list', () async {
    final (server, lists) = await _heldListServer();
    addTearDown(() => server.close(force: true));
    final controller = DashboardController(
      ServerClient('http://127.0.0.1:${server.port}', token: 'x' * 43),
    );
    addTearDown(controller.dispose);

    // Kéo làm mới (bản cũ còn máy A) rồi gỡ máy A: lượt sau trả trước.
    final oldLoad = controller.loadMyMachines();
    await lists.moveNext();
    final oldRequest = lists.current;
    final newLoad = controller.loadMyMachines();
    await lists.moveNext();
    await _replyMachines(lists.current, ['fm_b']);
    await newLoad;
    await _replyMachines(oldRequest, ['fm_a', 'fm_b']);
    await oldLoad;
    expect(controller.machines, ['fm_b']);
    expect(controller.names.containsKey('fm_a'), isFalse);
    expect(controller.machineId, 'fm_b');
  });

  test('Disposed dashboard ignores a late machine list', () async {
    final (server, lists) = await _heldListServer();
    addTearDown(() => server.close(force: true));
    final controller = DashboardController(
      ServerClient('http://127.0.0.1:${server.port}', token: 'x' * 43),
    );
    final pending = controller.loadMyMachines();
    await lists.moveNext();
    controller.dispose();
    await _replyMachines(lists.current, ['fm_a']);
    await pending;
    expect(controller.machines, isEmpty);
    expect(controller.machineId, isNull);
  });

  test('Máy bị thu hồi/gỡ ở nơi khác biến mất khi tải lại danh sách', () async {
    final machines = [
      {'machine_id': 'fm_a', 'name': 'Máy A', 'role': 'manager'},
      {'machine_id': 'fm_b', 'name': 'Máy B', 'role': 'owner'},
    ];
    final server = await _fakeServer(machines);
    addTearDown(() => server.close(force: true));
    final controller = DashboardController(
      ServerClient('http://127.0.0.1:${server.port}', token: 'x' * 43),
    );
    addTearDown(controller.dispose);

    await controller.loadMyMachines();
    expect(controller.machines, ['fm_a', 'fm_b']);
    expect(controller.machineId, 'fm_a');
    // Máy offline: các tab báo lỗi offline thay vì "chưa có món".
    expect(controller.products.error, contains('offline'));
    expect(controller.inventory.error, contains('offline'));

    // Chủ thu hồi quyền máy A đang chọn.
    machines.removeAt(0);
    await controller.loadMyMachines();
    expect(controller.machines, ['fm_b']);
    expect(controller.names.containsKey('fm_a'), isFalse);
    expect(controller.roles.containsKey('fm_a'), isFalse);
    // Máy đang chọn bị mất thì chọn máy còn lại.
    expect(controller.machineId, 'fm_b');

    machines.clear();
    await controller.loadMyMachines();
    expect(controller.machines, isEmpty);
    expect(controller.machineId, isNull);
  });

  test('Late status responses cannot overwrite a newer refresh', () async {
    final server = await HttpServer.bind(InternetAddress.loopbackIPv4, 0);
    final requests = StreamIterator<HttpRequest>(server);
    addTearDown(() async {
      await requests.cancel();
      await server.close(force: true);
    });
    final controller = DashboardController(
      ServerClient('http://127.0.0.1:${server.port}'),
    );
    addTearDown(controller.dispose);
    controller.machines.add('fm_a');

    final oldRefresh = controller.refreshStatuses();
    await requests.moveNext();
    final oldRequest = requests.current;
    final newRefresh = controller.refreshStatuses();
    await requests.moveNext();
    final newRequest = requests.current;
    newRequest.response
      ..headers.contentType = ContentType.json
      ..write(jsonEncode({'online': false}));
    await newRequest.response.close();
    await newRefresh;
    oldRequest.response
      ..headers.contentType = ContentType.json
      ..write(jsonEncode({'online': true}));
    await oldRequest.response.close();
    await oldRefresh;
    expect(controller.online['fm_a'], isFalse);
  });

  test(
    'Disposed dashboard ignores successful and failed status responses',
    () async {
      for (final status in [200, 503]) {
        final server = await HttpServer.bind(InternetAddress.loopbackIPv4, 0);
        final requests = StreamIterator<HttpRequest>(server);
        final controller = DashboardController(
          ServerClient('http://127.0.0.1:${server.port}'),
        );
        controller.machines.add('fm_a');
        final pending = controller.refreshStatuses();
        await requests.moveNext();
        controller.dispose();
        requests.current.response
          ..statusCode = status
          ..headers.contentType = ContentType.json
          ..write(
            jsonEncode(status == 200 ? {'online': true} : {'loi': 'offline'}),
          );
        await requests.current.response.close();
        await pending;
        await requests.cancel();
        await server.close(force: true);
        expect(controller.online, isEmpty);
      }
    },
  );
}
