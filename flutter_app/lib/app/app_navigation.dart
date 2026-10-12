import 'package:flutter/material.dart';

import '../feature/user_auth/ui/auth_page.dart';
import '../feature/user_auth/data/auth_service.dart';
import '../feature/dashboard/ui/dashboard_page.dart';
import '../feature/machine_register/data/claim_flow.dart';
import '../feature/machines/data/machine_controller.dart';
import '../feature/machines/data/machine_service.dart';

AuthPage buildAuthPage(AuthService service) => AuthPage(
  authService: service,
  onAuthenticated: (context) => Navigator.of(context).pushReplacement(
    MaterialPageRoute<void>(builder: (_) => buildDashboard(service)),
  ),
);
MainDashboard buildDashboard(AuthService service) {
  final machines = MachineService(client: service.client);
  return MainDashboard(
    machines: MachineController(service: machines),
    claimFlow: ClaimFlow(pairing: PairingChannel(), machines: machines),
    onLoggedOut: (context) async {
      final confirmed = await service.logout();
      if (!context.mounted) return;
      final messenger = ScaffoldMessenger.of(context);
      Navigator.of(context).pushAndRemoveUntil(
        MaterialPageRoute<void>(builder: (_) => buildAuthPage(service)),
        (_) => false,
      );
      if (!confirmed) {
        messenger.showSnackBar(
          const SnackBar(
            content: Text(
              'Đã đăng xuất trên điện thoại. Đăng xuất server chưa được xác nhận.',
            ),
          ),
        );
      }
    },
  );
}
