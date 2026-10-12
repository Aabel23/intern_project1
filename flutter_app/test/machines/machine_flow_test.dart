import 'dart:convert';
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:simple_app/feature/machine_register/data/claim_flow.dart';
import 'package:simple_app/feature/machines/data/machine_controller.dart';
import 'package:simple_app/feature/machines/data/machine_service.dart';
import 'package:simple_app/shared/cloud/cloud_client.dart';
import 'package:simple_app/shared/cloud/cloud_error.dart';

import '../user_auth/auth_flow_test.dart' as fixture;

const serial = '00000000abcdef01';
final seal = base64Url.encode(List.filled(32, 7)).replaceAll('=', '');
String qrText([Map<String, Object?> extra = const {}]) => jsonEncode({
  'v': 1,
  'type': 'flexmix-sealed',
  'serial': serial,
  'seal_code': seal,
  ...extra,
});

class FakePairing extends PairingChannel {
  FakePairing({this.online = false, this.claimError});
  final bool online;
  final String? claimError;
  final calls = <String>[];
  @override
  Future<bool> ensurePermissions() async => true;
  @override
  Future<void> start(SealedQr qr) async => calls.add('start ${qr.serial}');
  @override
  Future<Map<String, Object?>> probe() async {
    calls.add('probe');
    return {'machine_id': 'm-1', 'online': online};
  }

  @override
  Future<Map<String, Object?>> wifi(String ssid, String password) async {
    calls.add('wifi $ssid');
    return {'machine_id': 'm-1', 'online': true};
  }

  @override
  Future<Map<String, Object?>> claim(ClaimChallenge c) async {
    calls.add('claim ${c.claimId}');
    if (claimError != null) throw CloudError(claimError!);
    return {
      'claim_id': c.claimId,
      'local_session_binding': 'binding-1',
      'machine_proof': 'proof',
    };
  }

  @override
  Future<void> close() async => calls.add('close');
}

/// Records the bodies sent through authenticatedPost and answers from a script.
class ScriptClient extends CloudClient {
  ScriptClient(this.answers)
    : super(
        config: fixture.client(fixture.MemoryStore()).config,
        crypto: fixture.client(fixture.MemoryStore()).crypto,
        store: fixture.MemoryStore(),
      );
  final List<Object> answers;
  final sent = <Map<String, dynamic>>[];
  @override
  Future<Map<String, dynamic>> authenticatedPost(
    String route,
    Map<String, dynamic> body, {
    bool retryAfterRefresh = false,
    Duration timeout = const Duration(seconds: 10),
  }) async {
    sent.add({'route': route, ...body});
    final next = answers.removeAt(0);
    if (next is CloudError) throw next;
    return Map<String, dynamic>.from(next as Map);
  }
}

Map<String, dynamic> begin() => {
  'claim_id': 'c-1',
  'machine_id': 'm-1',
  'challenge': {'claim_id': 'c-1'},
  'server_challenge_signature': 'sig',
};
Map<String, dynamic> machine() => {
  'machine': {
    'id': 'm-1',
    'serial': serial,
    'name': 'FlexMix',
    'role': 'owner',
  },
};

void main() {
  group('SealedQr', () {
    test('accepts exactly the sealed format', () {
      final qr = SealedQr.parse(qrText())!;
      expect((qr.serial, qr.sealCode), (serial, seal));
    });
    test('rejects extra fields, bad serial, bad seal, non-JSON', () {
      expect(SealedQr.parse(qrText({'product_key': 'x'})), isNull);
      expect(SealedQr.parse(qrText({'serial': 'ABCDEF0000000000'})), isNull);
      expect(SealedQr.parse(qrText({'seal_code': 'short'})), isNull);
      expect(SealedQr.parse('not json'), isNull);
    });
  });

  group('ClaimFlow', () {
    test('offline machine gets Wi-Fi before claim, then complete', () async {
      final pairing = FakePairing();
      final client = ScriptClient([begin(), machine()]);
      final flow = ClaimFlow(
        pairing: pairing,
        machines: MachineService(client: client),
      );
      final result = await flow.run(
        SealedQr.parse(qrText())!,
        askWifi: () async => (ssid: 'Cafe', password: 'pw'),
      );
      expect(result.id, 'm-1');
      expect(pairing.calls, [
        'start $serial',
        'probe',
        'wifi Cafe',
        'claim c-1',
        'close',
      ]);
      expect(client.sent.map((b) => b['step']), ['begin', 'complete']);
      expect(client.sent.last['machine_proof'], 'proof');
    });

    test('online machine skips Wi-Fi (no credentials asked)', () async {
      final pairing = FakePairing(online: true);
      var asked = false;
      await ClaimFlow(
        pairing: pairing,
        machines: MachineService(client: ScriptClient([begin(), machine()])),
      ).run(
        SealedQr.parse(qrText())!,
        askWifi: () async {
          asked = true;
          return null;
        },
      );
      expect(asked, isFalse);
      expect(pairing.calls.where((c) => c.startsWith('wifi')), isEmpty);
    });

    test('lost complete response is retried with the same claim_id', () async {
      final client = ScriptClient([
        begin(),
        const CloudError('TIMEOUT'),
        machine(),
      ]);
      await ClaimFlow(
        pairing: FakePairing(online: true),
        machines: MachineService(client: client),
      ).run(SealedQr.parse(qrText())!, askWifi: () async => null);
      final completes = client.sent
          .where((b) => b['step'] == 'complete')
          .toList();
      expect(completes.length, 2);
      expect(completes[0]['claim_id'], completes[1]['claim_id']);
    });

    test('machine refusal closes the session and surfaces the code', () async {
      final pairing = FakePairing(online: true, claimError: 'CLAIM_INVALID');
      await expectLater(
        ClaimFlow(
          pairing: pairing,
          machines: MachineService(client: ScriptClient([begin()])),
        ).run(SealedQr.parse(qrText())!, askWifi: () async => null),
        throwsA(predicate((e) => e is CloudError && e.code == 'CLAIM_INVALID')),
      );
      expect(pairing.calls.last, 'close');
    });
  });

  group('MachineService.ask', () {
    Map<String, dynamic> answer(String id, Map<String, Object?> result) => {
      'request_id': id,
      'machine_id': 'm-1',
      'source': 'machine',
      'received_at': 1,
      'result': result,
    };

    test('machine error is an answer, not a relay error', () async {
      late String id;
      final client = ScriptClient([]);
      final service = MachineService(client: client);
      id = newRequestId();
      client.answers.add(
        answer(id, {
          'ok': false,
          'error': {'code': 'COMMAND_FAILED', 'message': 'Không có món 9'},
        }),
      );
      final out = await service.ask('m-1', 'cap_nhat_menu', {}, requestId: id);
      expect(
        (out.ok, out.errorCode, out.message),
        (false, 'COMMAND_FAILED', 'Không có món 9'),
      );
    });

    test('retry keeps request_id and sets retry=true', () async {
      final client = ScriptClient([]);
      final id = newRequestId();
      client.answers.add(answer(id, {'ok': true, 'data': {}}));
      await MachineService(client: client)
          .ask('m-1', 'nap_kho', {}, requestId: id, retry: true);
      expect(client.sent.single['request_id'], id);
      expect(client.sent.single['retry'], isTrue);
    });

    test('answer for another request is rejected', () async {
      final client = ScriptClient([
        answer(newRequestId(), {'ok': true, 'data': {}}),
      ]);
      await expectLater(
        MachineService(client: client).ask('m-1', 'machine.status.read', {}),
        throwsA(
          predicate((e) => e is CloudError && e.code == 'INVALID_RESPONSE'),
        ),
      );
    });

    test('request ids are UUIDv4', () {
      expect(
        newRequestId(),
        matches(
          RegExp(
            r'^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
          ),
        ),
      );
    });
  });

  test('menu packet from version1.1 decodes to rows', () {
    final packet = base64.encode(
      ZLibEncoder().convert(
        utf8.encode(
          jsonEncode({
            'type': 'menu_sync',
            'v': 1,
            'menu_version': 5,
            'fields': [
              'drink_id',
              'drink_name',
              'price',
              'available',
              'in_stock',
            ],
            'drinks': [
              [1, 'Trà đào', 35000, 1, 1],
            ],
          }),
        ),
      ),
    );
    expect(decodeMenuPacket(packet), [
      {
        'drink_id': 1,
        'drink_name': 'Trà đào',
        'price': 35000,
        'available': 1,
        'in_stock': 1,
      },
    ]);
  });
}
