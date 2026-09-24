import 'package:flutter/material.dart';

import '../../login/auth_page.dart';
import '../machine_api.dart';
import '../minitab/inventory_tab.dart';
import '../minitab/machines_tab.dart';
import '../minitab/orders_tab.dart';
import '../minitab/overview_tab.dart';
import '../minitab/products_tab.dart';
import 'dashboard_controller.dart';
import 'dashboard_widgets.dart';

// Khung chính sau đăng nhập, theo bố cục AdminShell của app Android cũ.
class MainDashboard extends StatefulWidget {
  const MainDashboard({super.key, required this.serverUrl, this.token});
  final String serverUrl;
  final String? token;

  @override
  State<MainDashboard> createState() => _MainDashboardState();
}

class _MainDashboardState extends State<MainDashboard> {
  late final _controller = DashboardController(
    MachineApi(widget.serverUrl, token: widget.token),
  );
  int index = 0;

  @override
  void initState() {
    super.initState();
    _controller.loadMyMachines();
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  void _logout() {
    Navigator.of(context).pushAndRemoveUntil(
      MaterialPageRoute<void>(
        builder: (_) => AuthPage(serverUrl: widget.serverUrl),
      ),
      (_) => false,
    );
  }

  @override
  Widget build(BuildContext context) => ListenableBuilder(
    listenable: _controller,
    builder: (context, _) {
      Widget machinePage(Widget page) =>
          _controller.hasMachine ? page : const NoMachineSelectedPage();
      final sections = <({Widget page, NavigationDestination destination})>[
        (
          page: machinePage(OverviewTab(controller: _controller)),
          destination: const NavigationDestination(
            icon: Icon(Icons.dashboard_outlined),
            selectedIcon: Icon(Icons.dashboard),
            label: 'Tổng quan',
          ),
        ),
        (
          page: machinePage(const OrdersTab()),
          destination: const NavigationDestination(
            icon: Icon(Icons.receipt_long_outlined),
            selectedIcon: Icon(Icons.receipt_long),
            label: 'Đơn hàng',
          ),
        ),
        (
          page: machinePage(ProductsTab(products: _controller.products)),
          destination: const NavigationDestination(
            icon: Icon(Icons.local_cafe_outlined),
            selectedIcon: Icon(Icons.local_cafe),
            label: 'Sản phẩm',
          ),
        ),
        (
          page: machinePage(InventoryTab(controller: _controller)),
          destination: const NavigationDestination(
            icon: Icon(Icons.inventory_2_outlined),
            selectedIcon: Icon(Icons.inventory_2),
            label: 'Kho',
          ),
        ),
        (
          page: MachinesTab(controller: _controller),
          destination: const NavigationDestination(
            icon: Icon(Icons.precision_manufacturing_outlined),
            selectedIcon: Icon(Icons.precision_manufacturing),
            label: 'Máy',
          ),
        ),
      ];
      return Scaffold(
        appBar: AppBar(
          title: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Text(
                'FlexMix',
                style: TextStyle(fontWeight: FontWeight.w800, fontSize: 17),
              ),
              Text(
                _controller.machineId == null
                    ? 'Chưa chọn máy'
                    : 'Máy: ${_controller.machineId}',
                style: const TextStyle(
                  fontSize: 12,
                  fontWeight: FontWeight.normal,
                ),
              ),
            ],
          ),
          actions: [
            PopupMenuButton<String>(
              icon: const CircleAvatar(child: Icon(Icons.person_outline)),
              onSelected: (value) {
                if (value == 'logout') _logout();
              },
              itemBuilder: (_) => const [
                PopupMenuItem(value: 'logout', child: Text('Đăng xuất')),
              ],
            ),
            const SizedBox(width: 8),
          ],
        ),
        body: IndexedStack(
          index: index,
          children: sections.map((section) => section.page).toList(),
        ),
        bottomNavigationBar: NavigationBar(
          selectedIndex: index,
          onDestinationSelected: (value) => setState(() => index = value),
          destinations: sections.map((section) => section.destination).toList(),
        ),
      );
    },
  );
}
