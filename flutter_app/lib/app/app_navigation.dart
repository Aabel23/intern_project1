import 'package:flutter/material.dart';
import 'package:simple_app/feature/user_auth/ui/auth_page.dart';
import 'package:simple_app/feature/dashboard/ui/dashboard_page.dart';

AuthPage buildAuthPage() => AuthPage(
  onAuthenticated: (context) => Navigator.of(
    context,
  ).pushReplacement(MaterialPageRoute<void>(builder: (_) => buildDashboard())),
);

MainDashboard buildDashboard() => MainDashboard(
  onLoggedOut: (context) => Navigator.of(context).pushAndRemoveUntil(
    MaterialPageRoute<void>(builder: (_) => buildAuthPage()),
    (_) => false,
  ),
);
