import 'dart:convert';
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:simple_app/core/server_client.dart';
import 'package:simple_app/feature/machine_menu/machine_menu_sync.dart';
import 'package:simple_app/feature/machine_ingredient/machine_ingredient_sync.dart';

Map<String, dynamic> menuReply(Object? version, String name) => {
  'status': 'ok',
  'menu_version': version,
  'packet': base64Encode(
    ZLibCodec().encode(
      utf8.encode(
        jsonEncode({
          'type': 'menu_sync',
          'v': 1,
          'menu_version': version,
          'fields': [
            'drink_id',
            'drink_name',
            'price',
            'available',
            'in_stock',
          ],
          'drinks': [
            [1, name, 25000, 1, 1],
          ],
        }),
      ),
    ),
  ),
};

void main() {
  for (final feature in ['menu', 'ingredients']) {
    test(
      '$feature rejects invalid CRC versions without replacing valid data',
      () async {
        Object? version = 7;
        var name = 'Current';
        final server = await HttpServer.bind(InternetAddress.loopbackIPv4, 0);
        server.listen((request) async {
          await utf8.decoder.bind(request).join();
          final reply = feature == 'menu'
              ? menuReply(version, name)
              : {
                  'status': 'ok',
                  'version': version,
                  'ingredients': [
                    {'ingredient_id': 1, 'name': name, 'amount': 500},
                  ],
                };
          request.response
            ..headers.contentType = ContentType.json
            ..write(jsonEncode(reply));
          await request.response.close();
        });
        addTearDown(() => server.close(force: true));
        final api = ServerClient('http://127.0.0.1:${server.port}');
        final menu = ProductsSync(api, () => 'fm_test');
        final ingredients = IngredientsSync(api, () => 'fm_test');
        addTearDown(menu.dispose);
        addTearDown(ingredients.dispose);
        Future<void> load() =>
            feature == 'menu' ? menu.load() : ingredients.load();
        await load();
        for (final invalid in [null, true, '7', 1.5, -1, 4294967296]) {
          version = invalid;
          name = 'Untrusted';
          await load();
          if (feature == 'menu') {
            expect(menu.menuVersion, 7);
            expect(menu.drinks.single.name, 'Current');
            expect(menu.error, isNotNull);
            expect(menu.loading, isFalse);
          } else {
            expect(ingredients.version, 7);
            expect(ingredients.ingredients.single.name, 'Current');
            expect(ingredients.error, isNotNull);
            expect(ingredients.loading, isFalse);
          }
        }
        version = 8;
        name = 'Updated';
        await load();
        expect(
          feature == 'menu'
              ? menu.drinks.single.name
              : ingredients.ingredients.single.name,
          'Updated',
        );
        expect(feature == 'menu' ? menu.error : ingredients.error, isNull);
      },
    );
  }
}
