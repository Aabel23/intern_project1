import 'dart:convert';
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:simple_app/UI/dashboard/dashboard/dashboard_controller.dart';
import 'package:simple_app/UI/dashboard/machine_api.dart';

// Server giả: /app/may-cua-toi trả danh sách máy đang giữ trong [machines];
// máy offline nên lệnh xem menu/đồng bộ kho trả lỗi offline như server thật.
Future<HttpServer> _fakeServer(List<Map<String, String>> machines) async {
  final server = await HttpServer.bind(InternetAddress.loopbackIPv4, 0);
  server.listen((request) async {
    await utf8.decoder.bind(request).join();
    Object reply;
    var status = 200;
    switch (request.uri.path) {
      case '/app/may-cua-toi':
        reply = {'valid': true, 'machines': machines};
      case '/machine/trang-thai':
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

void main() {
  test('Máy bị thu hồi/gỡ ở nơi khác biến mất khi tải lại danh sách', () async {
    final machines = [
      {'machine_id': 'fm_a', 'name': 'Máy A', 'role': 'manager'},
      {'machine_id': 'fm_b', 'name': 'Máy B', 'role': 'owner'},
    ];
    final server = await _fakeServer(machines);
    addTearDown(() => server.close(force: true));
    final controller = DashboardController(
      MachineApi('http://127.0.0.1:${server.port}', token: 'x' * 43),
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
}
