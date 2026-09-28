import 'package:flutter/material.dart';

import 'UI/app_theme.dart';
import 'UI/login/auth_page.dart';

void main() {
  runApp(const MainApp());
}

class MainApp extends StatelessWidget {
  const MainApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'FlexMix',
      debugShowCheckedModeBanner: false,
      theme: buildAppTheme(),
      home: const AuthPage(),
    );
  }
}
