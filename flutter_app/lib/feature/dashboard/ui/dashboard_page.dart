import 'package:flutter/material.dart';

import 'package:simple_app/shared/ui/app_theme.dart';
import 'package:simple_app/feature/machine_ingredient/ui/machine_ingredient_tab.dart';
import 'package:simple_app/feature/dashboard/ui/machines_tab.dart';
import 'package:simple_app/feature/orders/ui/orders_tab.dart';
import 'package:simple_app/feature/dashboard/ui/overview_tab.dart';
import 'package:simple_app/feature/machine_menu/ui/machine_menu_tab.dart';

// Khung chính sau đăng nhập, theo bố cục AdminShell của app Android cũ.
class MainDashboard extends StatefulWidget {
  const MainDashboard({super.key, required this.onLoggedOut});
  final void Function(BuildContext context) onLoggedOut;

  @override
  State<MainDashboard> createState() => _MainDashboardState();
}

class _MainDashboardState extends State<MainDashboard> {
  int index = 0;

  @override
  Widget build(BuildContext context) {
    final sections = <({Widget page, NavigationDestination destination})>[
      (
        page: const OverviewTab(),
        destination: const NavigationDestination(
          icon: Icon(Icons.dashboard_outlined),
          selectedIcon: Icon(Icons.dashboard),
          label: 'Tổng quan',
        ),
      ),
      (
        page: const OrdersTab(),
        destination: const NavigationDestination(
          icon: Icon(Icons.receipt_long_outlined),
          selectedIcon: Icon(Icons.receipt_long),
          label: 'Đơn hàng',
        ),
      ),
      (
        page: const ProductsTab(),
        destination: const NavigationDestination(
          icon: Icon(Icons.local_cafe_outlined),
          selectedIcon: Icon(Icons.local_cafe),
          label: 'Sản phẩm',
        ),
      ),
      (
        page: const InventoryTab(),
        destination: const NavigationDestination(
          icon: Icon(Icons.inventory_2_outlined),
          selectedIcon: Icon(Icons.inventory_2),
          label: 'Kho',
        ),
      ),
      (
        page: const MachinesTab(),
        destination: const NavigationDestination(
          icon: Icon(Icons.precision_manufacturing_outlined),
          selectedIcon: Icon(Icons.precision_manufacturing),
          label: 'Máy',
        ),
      ),
    ];
    return Scaffold(
      appBar: AppBar(
        toolbarHeight: 72,
        titleSpacing: 20,
        title: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              'Chưa chọn máy',
              style: TextStyle(fontSize: 13, color: AppColors.muted),
            ),
            const Text(
              'FlexMix',
              style: TextStyle(
                fontSize: 21,
                fontWeight: FontWeight.w700,
                color: AppColors.ink,
              ),
            ),
          ],
        ),
        actions: [
          PopupMenuButton<String>(
            tooltip: 'Tài khoản',
            icon: Container(
              width: 44,
              height: 44,
              decoration: BoxDecoration(
                color: Colors.white,
                shape: BoxShape.circle,
                border: Border.all(color: AppColors.border),
              ),
              child: const Icon(Icons.person_outline, color: AppColors.ink),
            ),
            onSelected: (value) {
              if (value == 'logout') widget.onLoggedOut(context);
            },
            itemBuilder: (_) => const [
              PopupMenuItem(value: 'logout', child: Text('Đăng xuất')),
            ],
          ),
          const SizedBox(width: 12),
        ],
      ),
      body: IndexedStack(
        index: index,
        children: sections.map((section) => section.page).toList(),
      ),
      bottomNavigationBar: DecoratedBox(
        decoration: const BoxDecoration(
          border: Border(top: BorderSide(color: AppColors.border)),
        ),
        child: NavigationBar(
          selectedIndex: index,
          onDestinationSelected: (value) => setState(() => index = value),
          destinations: sections.map((section) => section.destination).toList(),
        ),
      ),
    );
  }
}
