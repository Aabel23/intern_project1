import 'package:simple_app/feature/machine_menu/machine_menu_request.dart';

import 'dart:convert';
import 'dart:io';

import 'package:flutter/foundation.dart';

import 'package:simple_app/core/server_client.dart';

// Số ảnh tối đa mỗi lượt, khớp MAX_IMAGES phía server.
const maxImagesPerRequest = 20;

// Cache ảnh món trên đĩa, khóa theo máy + image_hash (CRC32 byte ảnh từ gói menu).
// Ảnh không đổi thì không tải lại; đổi ảnh thì hash đổi nên tự tải bản mới.
// Ảnh chỉ là phần phụ: lỗi tải thì tab vẫn vẽ chữ cái đầu tên món.
class MenuImageCache extends ChangeNotifier {
  MenuImageCache(this.api, this.machineId, {Directory? root})
    : root = root ?? Directory('${Directory.systemTemp.path}/menu_images');
  final ServerClient api;
  final String? Function() machineId;
  final Directory root;

  // drink_id → (hash, file) đang hiển thị.
  final Map<int, ({int hash, File file})> _files = {};
  // Tăng khi đổi máy để bỏ kết quả trả về muộn.
  int _session = 0;
  bool _disposed = false;

  File? fileOf(int drinkId) => _files[drinkId]?.file;

  void reset() {
    _session++;
    _files.clear();
    _notify();
  }

  // Gọi sau mỗi lần nhận menu: dùng ảnh có sẵn trên đĩa, xin máy phần còn thiếu.
  Future<void> sync(Iterable<({int id, int imageHash})> drinks) async {
    final id = machineId();
    final session = _session;
    if (id == null || _disposed) return;
    final folder = Directory('${root.path}/${_safeName(id)}');
    final wanted = <int, int>{};
    for (final drink in drinks) {
      if (drink.imageHash == 0) {
        _files.remove(drink.id);
        continue;
      }
      if (_files[drink.id]?.hash == drink.imageHash) continue;
      final file = _fileFor(folder, drink.imageHash);
      if (await file.exists()) {
        _files[drink.id] = (hash: drink.imageHash, file: file);
      } else {
        wanted[drink.id] = drink.imageHash;
      }
    }
    _notify();

    try {
      while (wanted.isNotEmpty) {
        final batch = wanted.entries.take(maxImagesPerRequest).toList();
        final reply = await api.receiveImages(id, [
          for (final item in batch)
            {'drink_id': item.key, 'image_hash': item.value},
        ]);
        if (session != _session || _disposed) return;
        for (final item in batch) {
          wanted.remove(item.key);
        }
        final received = await _store(folder, reply['anh']);
        if (session != _session || _disposed) return;
        _files.addAll(received);
        _notify();
        // Máy hết chỗ trong một lượt thì trả con_lai; không nhận được ảnh nào
        // mà vẫn còn lại nghĩa là máy không gửi được, dừng để khỏi lặp mãi.
        final rest = reply['con_lai'];
        if (rest is List && received.isNotEmpty) {
          for (final drinkId in rest.whereType<int>()) {
            final hash = batch
                .where((e) => e.key == drinkId)
                .firstOrNull
                ?.value;
            if (hash != null) wanted[drinkId] = hash;
          }
        }
      }
    } on ApiException {
      // Giữ ảnh đã có; lần tải menu sau sẽ xin lại phần thiếu.
    }
  }

  // Ghi các ảnh hợp lệ, bỏ dòng lỗi hoặc dữ liệu không khớp hash.
  Future<Map<int, ({int hash, File file})>> _store(
    Directory folder,
    Object? images,
  ) async {
    final stored = <int, ({int hash, File file})>{};
    if (images is! List) return stored;
    for (final item in images.whereType<Map>()) {
      final drinkId = item['drink_id'], hash = item['image_hash'];
      final data = item['data'];
      if (drinkId is! int || hash is! int || data is! String) continue;
      final Uint8List bytes;
      try {
        bytes = base64Decode(data);
      } on FormatException {
        continue;
      }
      // Hash là khóa cache nên phải đúng với nội dung thật.
      if (crc32(bytes) != hash) continue;
      final file = _fileFor(folder, hash);
      await folder.create(recursive: true);
      // Ghi file tạm rồi đổi tên để không bao giờ đọc phải ảnh ghi dở.
      final temp = File('${file.path}.tmp');
      await temp.writeAsBytes(bytes, flush: true);
      await temp.rename(file.path);
      stored[drinkId] = (hash: hash, file: file);
    }
    return stored;
  }

  File _fileFor(Directory folder, int hash) => File('${folder.path}/$hash.img');

  // machine_id do server cấp; vẫn lọc ký tự để không thoát khỏi thư mục cache.
  static String _safeName(String id) =>
      id.replaceAll(RegExp(r'[^A-Za-z0-9_-]'), '_');

  void _notify() {
    if (!_disposed) notifyListeners();
  }

  @override
  void dispose() {
    _session++;
    _disposed = true;
    super.dispose();
  }
}

// CRC32 (IEEE, giống zlib.crc32 phía máy) để kiểm ảnh nhận về.
final _crcTable = List<int>.generate(256, (n) {
  var c = n;
  for (var k = 0; k < 8; k++) {
    c = (c & 1) != 0 ? 0xEDB88320 ^ (c >> 1) : c >> 1;
  }
  return c;
});

int crc32(List<int> bytes) {
  var crc = 0xFFFFFFFF;
  for (final byte in bytes) {
    crc = _crcTable[(crc ^ byte) & 0xFF] ^ (crc >> 8);
  }
  return crc ^ 0xFFFFFFFF;
}
