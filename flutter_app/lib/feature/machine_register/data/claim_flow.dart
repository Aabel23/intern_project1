import 'dart:convert';

import 'package:flutter/services.dart';

import '../../../shared/cloud/cloud_error.dart';
import '../../machines/data/machine_service.dart';

/// Tem niêm phong: {v:1,type:"flexmix-sealed",serial,seal_code}. Sai dạng thì từ chối, không đoán.
class SealedQr {
  const SealedQr(this.serial, this.sealCode);
  final String serial;
  final String sealCode;

  static SealedQr? parse(String raw) {
    if (utf8.encode(raw).length > 1024) return null;
    try {
      final value = jsonDecode(raw);
      if (value is! Map ||
          value.length != 4 ||
          value['v'] != 1 ||
          value['type'] != 'flexmix-sealed') {
        return null;
      }
      final serial = value['serial'], seal = value['seal_code'];
      if (serial is! String ||
          !RegExp(r'^[0-9a-f]{16}$').hasMatch(serial) ||
          seal is! String ||
          !RegExp(r'^[A-Za-z0-9_-]{43}$').hasMatch(seal)) {
        return null;
      }
      return SealedQr(serial, seal);
    } on FormatException {
      return null;
    }
  }
}

/// Kênh native "flexmix/pairing": S và khóa phiên ở lại phía Kotlin.
class PairingChannel {
  static const _channel = MethodChannel('flexmix/pairing');

  Future<T?> _call<T>(String method, [Map<String, Object?>? args]) async {
    try {
      return await _channel.invokeMethod<T>(method, args);
    } on PlatformException catch (e) {
      throw CloudError(e.code);
    }
  }

  Future<bool> ensurePermissions() async =>
      await _call<bool>('ensurePermissions') ?? false;
  Future<void> start(SealedQr qr) =>
      _call('start', {'serial': qr.serial, 'seal_code': qr.sealCode});
  Future<Map<String, Object?>> probe() async =>
      Map<String, Object?>.from(await _call<Map>('probe') ?? {});
  Future<Map<String, Object?>> wifi(String ssid, String password) async =>
      Map<String, Object?>.from(
        await _call<Map>('wifi', {'ssid': ssid, 'password': password}) ?? {},
      );
  Future<Map<String, Object?>> claim(ClaimChallenge c) async =>
      Map<String, Object?>.from(
        await _call<Map>('claim', {
              'challenge': c.challenge,
              'server_challenge_signature': c.signature,
            }) ??
            {},
      );
  Future<void> close() => _call('close');
}

enum ClaimStep { permission, connecting, wifi, server, claiming, done }

/// Thông tin Wi-Fi do người dùng nhập; null = máy đã online, bỏ qua bước Wi-Fi (v2 D4).
typedef WifiPrompt = Future<({String ssid, String password})?> Function();

/// Nhận máy: BLE probe → [Wi-Fi] → server begin → máy ký trong phiên BLE → server complete.
class ClaimFlow {
  ClaimFlow({required this.pairing, required this.machines});
  final PairingChannel pairing;
  final MachineService machines;

  Future<Machine> run(
    SealedQr qr, {
    required WifiPrompt askWifi,
    void Function(ClaimStep step)? onStep,
  }) async {
    onStep?.call(ClaimStep.permission);
    if (!await pairing.ensurePermissions()) {
      throw const CloudError('BLUETOOTH_PERMISSION');
    }
    try {
      onStep?.call(ClaimStep.connecting);
      await pairing.start(qr);
      final probe = await pairing.probe();
      if (probe['online'] != true) {
        final wifi = await askWifi();
        if (wifi == null) throw const CloudError('CANCELLED');
        onStep?.call(ClaimStep.wifi);
        await pairing.wifi(wifi.ssid, wifi.password);
      }
      onStep?.call(ClaimStep.server);
      final challenge = await machines.beginClaim(qr.serial);
      onStep?.call(ClaimStep.claiming);
      final proof = await pairing.claim(challenge);
      final claimId = proof['claim_id'],
          binding = proof['local_session_binding'];
      final machineProof = proof['machine_proof'];
      if (claimId != challenge.claimId ||
          binding is! String ||
          machineProof is! String) {
        throw const CloudError('PAIRING_PROTOCOL_ERROR');
      }
      Future<Machine> complete() => machines.completeClaim(
        claimId: challenge.claimId,
        machineProof: machineProof,
        localSessionBinding: binding,
      );
      Machine machine;
      try {
        machine = await complete();
      } on CloudError catch (e) {
        // Mất phản hồi sau commit: gửi lại đúng claim_id, server trả lại kết quả cũ.
        if (e.code != 'TIMEOUT' && e.code != 'TRANSPORT_ERROR') rethrow;
        machine = await complete();
      }
      onStep?.call(ClaimStep.done);
      return machine;
    } finally {
      await pairing.close().catchError((_) {});
    }
  }
}
