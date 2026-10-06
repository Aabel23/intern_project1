import 'package:simple_app/core/server_client.dart';
import 'package:simple_app/feature/user_auth/user_auth_request.dart';
import 'package:flutter/material.dart';
import 'package:simple_app/config/app_config.dart';
import 'package:simple_app/feature/user_auth/ui/auth_page.dart';
import 'package:simple_app/feature/dashboard/ui/dashboard_page.dart';

AuthPage buildAuthPage({String serverUrl = kServerUrl}) => AuthPage(
  serverUrl: serverUrl,
  onAuthenticated: (context, token) => Navigator.of(context).pushReplacement(
    MaterialPageRoute<void>(
      builder: (_) => buildDashboard(serverUrl: serverUrl, token: token),
    ),
  ),
);

MainDashboard buildDashboard({required String serverUrl, String? token}) =>
    MainDashboard(
      serverUrl: serverUrl,
      token: token,
      onLoggedOut: (context, invalidateSession) {
        if (invalidateSession) ServerClient(serverUrl, token: token).logout();
        Navigator.of(context).pushAndRemoveUntil(
          MaterialPageRoute<void>(
            builder: (_) => buildAuthPage(serverUrl: serverUrl),
          ),
          (_) => false,
        );
      },
    );
