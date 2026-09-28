import 'package:flutter/material.dart';

import '../../app_theme.dart';

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
    style: const TextStyle(
      fontSize: 21,
      fontWeight: FontWeight.w700,
      color: AppColors.ink,
    ),
  );
}

// Dòng phụ xám dưới tiêu đề tab.
class PageSubtitle extends StatelessWidget {
  const PageSubtitle(this.text, {super.key});
  final String text;

  @override
  Widget build(BuildContext context) => Padding(
    padding: const EdgeInsets.only(top: 2),
    child: Text(
      text,
      style: const TextStyle(fontSize: 13, color: AppColors.muted),
    ),
  );
}

class NoMachineSelectedPage extends StatelessWidget {
  const NoMachineSelectedPage({super.key});

  @override
  Widget build(BuildContext context) => Center(
    child: Padding(
      padding: const EdgeInsets.all(32),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Container(
            width: 72,
            height: 72,
            decoration: BoxDecoration(
              color: AppColors.greenTint,
              borderRadius: BorderRadius.circular(20),
            ),
            child: const Icon(
              Icons.precision_manufacturing_outlined,
              size: 36,
              color: AppColors.green,
            ),
          ),
          const SizedBox(height: 16),
          const Text(
            'Chưa chọn máy',
            style: TextStyle(
              fontSize: 19,
              fontWeight: FontWeight.w700,
              color: AppColors.ink,
            ),
          ),
          const SizedBox(height: 6),
          const Text(
            'Mở tab Máy để chọn thiết bị cần làm việc.',
            textAlign: TextAlign.center,
            style: TextStyle(fontSize: 13, color: AppColors.muted),
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
        color: error ? AppColors.orangeText : AppColors.muted,
        fontSize: 13,
      ),
    ),
  );
}
