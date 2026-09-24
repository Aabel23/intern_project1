import 'package:flutter/material.dart';

String money(num value) {
  final raw = value.round().toString();
  final out = StringBuffer();
  for (var i = 0; i < raw.length; i++) {
    if (i > 0 && (raw.length - i) % 3 == 0) out.write('.');
    out.write(raw[i]);
  }
  return '$outđ';
}

String twoDigits(int value) => value.toString().padLeft(2, '0');

void showMessage(BuildContext context, String message) {
  ScaffoldMessenger.of(context)
    ..hideCurrentSnackBar()
    ..showSnackBar(SnackBar(content: Text(message)));
}

// Nút của những tính năng server chưa có: chỉ giữ giao diện, chưa gắn chức năng.
void notAvailableYet(BuildContext context) =>
    showMessage(context, 'Tính năng này chưa được hỗ trợ.');

// Tiêu đề lớn đầu mỗi tab.
class PageTitle extends StatelessWidget {
  const PageTitle(this.text, {super.key});
  final String text;

  @override
  Widget build(BuildContext context) => Text(
    text,
    style: Theme.of(context).textTheme.headlineSmall
        ?.copyWith(fontWeight: FontWeight.w800),
  );
}

class NoMachineSelectedPage extends StatelessWidget {
  const NoMachineSelectedPage({super.key});

  @override
  Widget build(BuildContext context) => const Center(
    child: Padding(
      padding: EdgeInsets.all(32),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(Icons.precision_manufacturing_outlined, size: 64),
          SizedBox(height: 16),
          Text(
            'Chưa chọn máy',
            style: TextStyle(fontSize: 20, fontWeight: FontWeight.w800),
          ),
          SizedBox(height: 8),
          Text(
            'Mở tab Máy để chọn thiết bị cần làm việc.',
            textAlign: TextAlign.center,
          ),
        ],
      ),
    ),
  );
}

// Dòng thông báo trống hoặc lỗi bên trong danh sách.
class ListNotice extends StatelessWidget {
  const ListNotice(this.message, {super.key, this.error = false});
  final String message;
  final bool error;

  @override
  Widget build(BuildContext context) => Padding(
    padding: const EdgeInsets.symmetric(vertical: 32),
    child: Text(
      message,
      textAlign: TextAlign.center,
      style: TextStyle(
        color: error ? Theme.of(context).colorScheme.error : Colors.black54,
      ),
    ),
  );
}
