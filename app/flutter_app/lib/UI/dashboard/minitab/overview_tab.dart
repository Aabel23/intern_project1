import 'package:flutter/material.dart';

import '../../app_theme.dart';
import '../dashboard/dashboard_controller.dart';
import '../dashboard/dashboard_widgets.dart';

// Tab Tổng quan. Doanh thu/đơn hàng chưa có trên server nên chỉ giữ ô hiển thị.
class OverviewTab extends StatelessWidget {
  const OverviewTab({super.key, required this.controller});
  final DashboardController controller;

  @override
  Widget build(BuildContext context) {
    final now = DateTime.now();
    return ListenableBuilder(
      listenable: Listenable.merge([controller, controller.inventory]),
      builder: (context, _) {
        final empty = controller.inventory.ingredients
            .where((i) => !i.inStock)
            .length;
        return ListView(
          padding: const EdgeInsets.fromLTRB(20, 8, 20, 28),
          children: [
            const PageTitle('Hôm nay'),
            const SizedBox(height: 16),
            _RevenueCard(
              date: '${twoDigits(now.day)}/${twoDigits(now.month)}/${now.year}',
              empty: empty,
            ),
          ],
        );
      },
    );
  }
}

// Thẻ xanh đầu trang theo thiết kế. Doanh thu, đơn hàng, giá trị TB chưa có
// trên server nên hiện "—"; chỉ "Sắp hết" lấy từ kho của máy.
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
