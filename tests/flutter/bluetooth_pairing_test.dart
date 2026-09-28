import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:simple_app/feature/machine_register/ui/machine_register_bluetooth_page.dart';

void main() {
  const channel = MethodChannel('flexmix/bluetooth_pairing');
  TestWidgetsFlutterBinding.ensureInitialized();

  tearDown(() {
    TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger
        .setMockMethodCallHandler(channel, null);
  });

  testWidgets('Chọn đúng địa chỉ máy, nhận và hiển thị gói pairing', (
    tester,
  ) async {
    String? selected;
    bool cancelled = false;
    TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger
        .setMockMethodCallHandler(channel, (call) async {
          if (call.method == 'scan') {
            return [
              {'name': 'FlexMix-01', 'address': 'AA:BB:CC:DD:EE:01'},
              {'name': 'FlexMix-02', 'address': 'AA:BB:CC:DD:EE:02'},
            ];
          }
          if (call.method == 'connect') {
            selected = call.arguments['address'] as String;
            return {
              'type': 'pairing',
              'machine_name': 'FlexMix-02',
              'product_key': 'test-product-key',
            };
          }
          cancelled = call.method == 'cancel';
          return null;
        });

    await tester.pumpWidget(
      const MaterialApp(
        home: MachinePairingPage(serverUrl: 'http://127.0.0.1:1'),
      ),
    );
    await tester.pumpAndSettle();
    await tester.tap(find.text('FlexMix-02'));
    await tester.pumpAndSettle();
    expect(selected, 'AA:BB:CC:DD:EE:02');
    expect(find.text('Tên máy: FlexMix-02'), findsOneWidget);
    expect(find.text('Product key: ••••-key'), findsOneWidget);
    await tester.pumpWidget(const SizedBox());
    await tester.pumpAndSettle();
    expect(cancelled, isTrue);
  });

  testWidgets('Từ chối quyền vẫn cho phép quét lại', (tester) async {
    TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger
        .setMockMethodCallHandler(channel, (call) async {
          if (call.method == 'scan') {
            throw PlatformException(
              code: 'bluetooth',
              message: 'Cần quyền Bluetooth',
            );
          }
          return null;
        });
    await tester.pumpWidget(
      const MaterialApp(
        home: MachinePairingPage(serverUrl: 'http://127.0.0.1:1'),
      ),
    );
    await tester.pumpAndSettle();
    expect(find.text('Cần quyền Bluetooth'), findsOneWidget);
    final button = tester.widget<FilledButton>(find.byType(FilledButton));
    expect(button.onPressed, isNotNull);
    await tester.pumpWidget(const SizedBox());
    await tester.pumpAndSettle();
  });
}
