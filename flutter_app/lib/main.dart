import 'package:flutter/material.dart';

import 'package:simple_app/shared/ui/app_theme.dart';
import 'package:simple_app/app/app_navigation.dart';

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
      home: buildAuthPage(),
    );
  }
}
