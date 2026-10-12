import 'package:flutter/material.dart';

import '../feature/user_auth/ui/auth_page.dart';
import '../feature/user_auth/data/auth_service.dart';
import '../feature/dashboard/ui/dashboard_page.dart';

AuthPage buildAuthPage(AuthService service) => AuthPage(
  authService: service,
  onAuthenticated: (context) => Navigator.of(context).pushReplacement(
    MaterialPageRoute<void>(builder: (_) => buildDashboard(service)),
  ),
);
MainDashboard buildDashboard(AuthService service) => MainDashboard(
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
