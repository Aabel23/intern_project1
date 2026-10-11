import 'package:flutter/material.dart';

import 'package:simple_app/shared/ui/app_theme.dart';
import 'package:simple_app/shared/ui/list_widgets.dart';

// Tab Tổng quan: chỉ giữ giao diện, chưa nối nguồn dữ liệu.
class OverviewTab extends StatelessWidget {
  const OverviewTab({super.key});

  @override
  Widget build(BuildContext context) {
    final now = DateTime.now();
    return ListView(
      padding: const EdgeInsets.fromLTRB(20, 8, 20, 28),
      children: [
        const PageTitle('Hôm nay'),
        const SizedBox(height: 16),
        _RevenueCard(
          date: '${twoDigits(now.day)}/${twoDigits(now.month)}/${now.year}',
          empty: 0,
        ),
      ],
    );
  }
}

// Thẻ xanh đầu trang theo thiết kế. Chưa nối dữ liệu nên các ô hiện "—".
class _RevenueCard extends StatelessWidget {
  const _RevenueCard({required this.date, required this.empty});
  final String date;
  final int empty;

  @override
  Widget build(BuildContext context) => Container(
    padding: const EdgeInsets.all(20),
    decoration: BoxDecoration(
      color: AppColors.green,
      borderRadius: BorderRadius.circular(20),
    ),
    child: Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            Expanded(
              child: Text(
                'Doanh thu · $date',
                style: const TextStyle(
                  fontSize: 13,
                  color: AppColors.onGreenMuted,
                ),
              ),
            ),
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
              decoration: BoxDecoration(
                color: Colors.white.withValues(alpha: 0.14),
                borderRadius: BorderRadius.circular(999),
              ),
              child: const Text(
                'Chưa có dữ liệu',
                style: TextStyle(
                  fontSize: 12,
                  fontWeight: FontWeight.w600,
                  color: Colors.white,
                ),
              ),
            ),
          ],
        ),
        const SizedBox(height: 14),
        Text('—', style: displayNumber(38, color: Colors.white)),
        const SizedBox(height: 14),
        Container(
          padding: const EdgeInsets.only(top: 14),
          decoration: BoxDecoration(
            border: Border(
              top: BorderSide(color: Colors.white.withValues(alpha: 0.18)),
            ),
          ),
          child: Row(
            children: [
              const Expanded(child: _Stat('—', 'Đơn hàng')),
              const Expanded(child: _Stat('—', 'Giá trị TB')),
              Expanded(
                child: _Stat(
                  '$empty',
                  'Sắp hết',
                  note: empty > 0 ? 'Cần xử lý' : 'Ổn định',
                  warning: empty > 0,
                ),
              ),
            ],
          ),
        ),
      ],
    ),
  );
}

class _Stat extends StatelessWidget {
  const _Stat(this.value, this.label, {this.note, this.warning = false});
  final String value, label;
  final String? note;
  final bool warning;

  @override
  Widget build(BuildContext context) => Column(
    crossAxisAlignment: CrossAxisAlignment.start,
    children: [
      Text(
        value,
        style: const TextStyle(
          fontSize: 17,
          fontWeight: FontWeight.w700,
          color: Colors.white,
        ),
      ),
      Text(
        label,
        style: const TextStyle(fontSize: 12, color: AppColors.onGreenMuted),
      ),
      if (note != null)
        Container(
          margin: const EdgeInsets.only(top: 6),
          padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
          decoration: BoxDecoration(
            color: warning ? AppColors.orangeTint : AppColors.greenTint,
            borderRadius: BorderRadius.circular(999),
          ),
          child: Text(
            note!,
            style: TextStyle(
              fontSize: 11,
              fontWeight: FontWeight.w700,
              color: warning ? AppColors.orangeText : AppColors.green,
            ),
          ),
        ),
    ],
  );
}
