import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:simple_app/feature/machines/data/machine_controller.dart';
import 'package:simple_app/feature/machines/data/machine_service.dart';
import 'package:simple_app/feature/orders/data/qr_ticket.dart';
import 'package:simple_app/feature/orders/ui/orders_tab.dart';
import 'package:simple_app/shared/cloud/cloud_error.dart';

import '../user_auth/auth_flow_test.dart' as fixture;

Map<String, dynamic> row(int serial, {String status = 'used'}) => {
  'serial': serial,
  'drink_name': 'Trà đào',
  'price_vnd': '35000.00',
  'status': status,
  'created_at': '2026-10-13T10:42:00',
  'scanned_at': '2026-10-13T10:43:00',
  'completed_at': '2026-10-13T10:45:00',
};

MachineAnswer page(List<Map<String, dynamic>> rows, {int? next}) =>
    MachineAnswer(
      requestId: 'test',
      receivedAt: 1,
      ok: true,
      data: {'tickets': rows, 'next_before_serial': next},
    );

class TicketService extends MachineService {
  TicketService() : super(client: fixture.client(fixture.MemoryStore()));

  final calls =
      <({String machineId, String instruction, Map<String, dynamic> data})>[];
  final pending = <Completer<MachineAnswer>>[];

  @override
  Future<MachineAnswer> ask(
    String machineId,
    String instruction,
    Map<String, dynamic> data, {
    String? requestId,
    bool retry = false,
  }) {
    calls.add((machineId: machineId, instruction: instruction, data: data));
    final completer = Completer<MachineAnswer>();
    pending.add(completer);
    return completer.future;
  }
}

MachineController controllerFor(TicketService service) {
  final controller = MachineController(service: service);
  controller.machines = const [
    Machine(
      id: 'm-1',
      serial: 's-1',
      name: 'Máy 1',
      role: 'owner',
      online: true,
    ),
    Machine(
      id: 'm-2',
      serial: 's-2',
      name: 'Máy 2',
      role: 'owner',
      online: true,
    ),
  ];
  return controller;
}

Future<void> showTab(WidgetTester tester, MachineController controller) async {
  await tester.pumpWidget(
    MaterialApp(
      home: Scaffold(body: OrdersTab(controller: controller)),
    ),
  );
  await tester.pump();
}

void main() {
  test('QR ticket keeps exact decimal and naive machine time', () {
    final ticket = QrTicket.fromMap(row(132));
    expect(ticket.priceVnd, '35000.00');
    expect(ticket.createdAt, '2026-10-13T10:42:00');
    expect(ticket.status, QrTicketStatus.used);
    final legacy = QrTicket.fromMap({
      ...row(131, status: 'unused'),
      'drink_name': null,
      'price_vnd': null,
      'scanned_at': null,
      'completed_at': null,
    });
    expect(legacy.priceVnd, isNull);
    expect(legacy.status, QrTicketStatus.unused);
  });

  test('QR ticket rejects invented status, numeric price and timezone', () {
    for (final invalid in [
      {...row(1), 'status': 'cancelled'},
      {...row(1), 'price_vnd': 35000},
      {...row(1), 'created_at': '2026-10-13T10:42:00+07:00'},
    ]) {
      expect(() => QrTicket.fromMap(invalid), throwsA(isA<CloudError>()));
    }
  });

  test('page validates descending serial and cursor', () {
    final rows = [for (var serial = 40; serial >= 21; serial--) row(serial)];
    expect(
      QrTicketPage.fromData({'tickets': rows, 'next_before_serial': 21})
          .nextBeforeSerial,
      21,
    );
    expect(
      () => QrTicketPage.fromData({
        'tickets': [row(4), row(5)],
        'next_before_serial': null,
      }),
      throwsA(isA<CloudError>()),
    );
    expect(
      () => QrTicketPage.fromData({
        'tickets': [row(4)],
        'next_before_serial': 4,
      }),
      throwsA(isA<CloudError>()),
    );
    expect(
      () => QrTicketPage.fromData({
        'tickets': [
          {1: 'wrong key'},
        ],
        'next_before_serial': null,
      }),
      throwsA(isA<CloudError>()),
    );
  });

  testWidgets('loads real ticket page, exact price, statuses and next page', (
    tester,
  ) async {
    final service = TicketService();
    final controller = controllerFor(service)..select('m-1');
    await showTab(tester, controller);
    expect(service.calls.single.instruction, 'nhan_ve_qr');
    expect(service.calls.single.data, {'before_serial': null, 'limit': 20});
    service.pending[0].complete(
      page([
        for (var serial = 40; serial >= 21; serial--) row(serial),
      ], next: 21),
    );
    await tester.pumpAndSettle();
    expect(find.text('Vé #40'), findsOneWidget);
    expect(find.text('Giá trên vé: 35000.00 đ'), findsWidgets);
    expect(find.textContaining('giờ trên máy'), findsWidgets);
    expect(find.text('Đơn hàng'), findsNothing);
    await tester.scrollUntilVisible(find.text('Xem thêm vé'), 500);
    await tester.tap(find.text('Xem thêm vé'));
    await tester.pump();
    expect(service.calls.last.data, {'before_serial': 21, 'limit': 20});
    service.pending[1].complete(page([row(20, status: 'noqr_err')]));
    await tester.pumpAndSettle();
    await tester.scrollUntilVisible(find.text('Vé #20'), 500);
    expect(find.text('Pha lỗi, không có QR'), findsOneWidget);
    expect(find.text('Xem thêm vé'), findsNothing);
  });

  testWidgets('switching machine drops late results from previous machine', (
    tester,
  ) async {
    final service = TicketService();
    final controller = controllerFor(service)..select('m-1');
    await showTab(tester, controller);
    controller.select('m-2');
    await tester.pump();
    expect(service.calls.map((c) => c.machineId), ['m-1', 'm-2']);
    service.pending[1].complete(page([row(2, status: 'expired')]));
    await tester.pumpAndSettle();
    service.pending[0].complete(page([row(1)]));
    await tester.pumpAndSettle();
    expect(find.text('Vé #2'), findsOneWidget);
    expect(find.text('Hết hạn'), findsOneWidget);
    expect(find.text('Vé #1'), findsNothing);
  });

  testWidgets('refresh requests first page and replaces old tickets', (
    tester,
  ) async {
    final service = TicketService();
    final controller = controllerFor(service)..select('m-1');
    await showTab(tester, controller);
    service.pending[0].complete(page([row(8)]));
    await tester.pumpAndSettle();
    expect(find.text('Vé #8'), findsOneWidget);

    await tester.tap(find.byTooltip('Làm mới vé QR'));
    await tester.pump();
    expect(service.calls.length, 2);
    expect(service.calls.last.data['before_serial'], isNull);
    service.pending[1].complete(page([row(9)]));
    await tester.pumpAndSettle();
    expect(find.text('Vé #9'), findsOneWidget);
    expect(find.text('Vé #8'), findsNothing);
  });
}
