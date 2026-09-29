import 'package:flutter/material.dart';

// Bảng màu và kiểu chữ chung, theo bản thiết kế "App quản lý bán hàng".
class AppColors {
  static const background = Color(0xFFF6F3EC);
  static const ink = Color(0xFF1C2420);
  static const muted = Color(0xFF5B635E);
  static const subtle = Color(0xFF6B716D);
  static const green = Color(0xFF1F5C45);
  static const greenDark = Color(0xFF16432F);
  static const greenSoft = Color(0xFFCFE0D6);
  static const greenTint = Color(0xFFE3EFE8);
  static const onGreenMuted = Color(0xFFD5E6DC);
  static const orange = Color(0xFFC2410C);
  static const orangeText = Color(0xFF9A3412);
  static const orangeTint = Color(0xFFFCEBD9);
  static const border = Color(0xFFE4DED2);
  static const divider = Color(0xFFEFEAE0);
  static const segment = Color(0xFFECE7DC);
  static const card = Colors.white;
}

const kBodyFont = 'BeVietnamPro';

// Số tiền/số liệu lớn dùng Fraunces đậm như bản thiết kế.
TextStyle displayNumber(double size, {Color color = AppColors.ink}) =>
    TextStyle(
      fontFamily: 'Fraunces',
      fontSize: size,
      fontWeight: FontWeight.w600,
      fontVariations: const [FontVariation('wght', 600)],
      letterSpacing: -0.5,
      color: color,
    );

ThemeData buildAppTheme() {
  final scheme =
      ColorScheme.fromSeed(
        seedColor: AppColors.green,
        surface: AppColors.background,
      ).copyWith(
        primary: AppColors.green,
        onPrimary: Colors.white,
        secondary: AppColors.orange,
        onSurface: AppColors.ink,
        outline: AppColors.border,
        outlineVariant: AppColors.divider,
      );
  final rounded14 = RoundedRectangleBorder(
    borderRadius: BorderRadius.circular(14),
  );
  const buttonText = TextStyle(
    fontFamily: kBodyFont,
    fontSize: 14,
    fontWeight: FontWeight.w700,
  );
  return ThemeData(
    useMaterial3: true,
    fontFamily: kBodyFont,
    colorScheme: scheme,
    scaffoldBackgroundColor: AppColors.background,
    appBarTheme: const AppBarTheme(
      backgroundColor: AppColors.background,
      foregroundColor: AppColors.ink,
      surfaceTintColor: Colors.transparent,
      elevation: 0,
      scrolledUnderElevation: 0,
    ),
    cardTheme: const CardThemeData(
      color: AppColors.card,
      surfaceTintColor: Colors.transparent,
      elevation: 0,
      margin: EdgeInsets.zero,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.all(Radius.circular(16)),
        side: BorderSide(color: AppColors.border),
      ),
    ),
    inputDecorationTheme: InputDecorationTheme(
      filled: true,
      fillColor: Colors.white,
      border: OutlineInputBorder(
        borderRadius: BorderRadius.circular(14),
        borderSide: const BorderSide(color: AppColors.border),
      ),
      enabledBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(14),
        borderSide: const BorderSide(color: AppColors.border),
      ),
      focusedBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(14),
        borderSide: const BorderSide(color: AppColors.green, width: 1.6),
      ),
    ),
    filledButtonTheme: FilledButtonThemeData(
      style: FilledButton.styleFrom(
        backgroundColor: AppColors.green,
        foregroundColor: Colors.white,
        minimumSize: const Size(44, 48),
        shape: rounded14,
        textStyle: buttonText,
      ),
    ),
    outlinedButtonTheme: OutlinedButtonThemeData(
      style: OutlinedButton.styleFrom(
        foregroundColor: AppColors.green,
        backgroundColor: Colors.white,
        minimumSize: const Size(44, 48),
        side: const BorderSide(color: AppColors.green),
        shape: rounded14,
        textStyle: buttonText,
      ),
    ),
    textButtonTheme: TextButtonThemeData(
      style: TextButton.styleFrom(
        foregroundColor: AppColors.green,
        textStyle: buttonText.copyWith(fontSize: 13),
      ),
    ),
    floatingActionButtonTheme: FloatingActionButtonThemeData(
      backgroundColor: AppColors.orange,
      foregroundColor: Colors.white,
      elevation: 4,
      extendedTextStyle: buttonText,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(18)),
    ),
    chipTheme: ChipThemeData(
      backgroundColor: Colors.white,
      side: const BorderSide(color: AppColors.border),
      shape: const StadiumBorder(),
      labelStyle: const TextStyle(
        fontFamily: kBodyFont,
        fontSize: 12,
        fontWeight: FontWeight.w600,
        color: AppColors.ink,
      ),
    ),
    switchTheme: SwitchThemeData(
      trackColor: WidgetStateProperty.resolveWith(
        (s) => s.contains(WidgetState.selected)
            ? AppColors.green
            : AppColors.segment,
      ),
      thumbColor: WidgetStateProperty.resolveWith(
        (s) =>
            s.contains(WidgetState.selected) ? Colors.white : AppColors.subtle,
      ),
      trackOutlineColor: const WidgetStatePropertyAll(Colors.transparent),
    ),
    progressIndicatorTheme: const ProgressIndicatorThemeData(
      color: AppColors.green,
      linearTrackColor: AppColors.segment,
    ),
    dialogTheme: DialogThemeData(
      backgroundColor: AppColors.background,
      surfaceTintColor: Colors.transparent,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
    ),
    popupMenuTheme: PopupMenuThemeData(
      color: Colors.white,
      surfaceTintColor: Colors.transparent,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(14),
        side: const BorderSide(color: AppColors.border),
      ),
    ),
    snackBarTheme: SnackBarThemeData(
      backgroundColor: AppColors.ink,
      behavior: SnackBarBehavior.floating,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
    ),
    navigationBarTheme: NavigationBarThemeData(
      backgroundColor: Colors.white,
      surfaceTintColor: Colors.transparent,
      elevation: 0,
      height: 72,
      indicatorColor: Colors.transparent,
      iconTheme: WidgetStateProperty.resolveWith(
        (s) => IconThemeData(
          size: 24,
          color: s.contains(WidgetState.selected)
              ? AppColors.green
              : AppColors.subtle,
        ),
      ),
      labelTextStyle: WidgetStateProperty.resolveWith(
        (s) => TextStyle(
          fontFamily: kBodyFont,
          fontSize: 11,
          fontWeight: s.contains(WidgetState.selected)
              ? FontWeight.w700
              : FontWeight.w500,
          color: s.contains(WidgetState.selected)
              ? AppColors.green
              : AppColors.subtle,
        ),
      ),
    ),
    dividerTheme: const DividerThemeData(color: AppColors.divider, space: 1),
  );
}

// Ô vuông chữ viết tắt đầu dòng (như "SU", "BQ" trong thiết kế).
class InitialsTile extends StatelessWidget {
  const InitialsTile(
    this.text, {
    super.key,
    this.background = AppColors.greenTint,
    this.foreground = AppColors.green,
    this.size = 40,
  });
  final String text;
  final Color background, foreground;
  final double size;

  @override
  Widget build(BuildContext context) => Container(
    width: size,
    height: size,
    alignment: Alignment.center,
    decoration: BoxDecoration(
      color: background,
      borderRadius: BorderRadius.circular(10),
    ),
    child: Text(
      text,
      style: TextStyle(
        color: foreground,
        fontSize: 13,
        fontWeight: FontWeight.w700,
      ),
    ),
  );
}

// Nhãn trạng thái bo tròn ("Hoàn thành", "Chờ giao"...).
class StatusPill extends StatelessWidget {
  const StatusPill(
    this.text, {
    super.key,
    this.background = AppColors.greenTint,
    this.foreground = AppColors.green,
  });
  final String text;
  final Color background, foreground;

  @override
  Widget build(BuildContext context) => Container(
    padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 3),
    decoration: BoxDecoration(
      color: background,
      borderRadius: BorderRadius.circular(999),
    ),
    child: Text(
      text,
      style: TextStyle(
        color: foreground,
        fontSize: 11,
        fontWeight: FontWeight.w700,
      ),
    ),
  );
}

String initialsOf(String name) {
  final words = name.trim().split(RegExp(r'\s+')).where((w) => w.isNotEmpty);
  if (words.isEmpty) return '?';
  if (words.length == 1) {
    final w = words.first;
    return (w.length >= 2 ? w.substring(0, 2) : w).toUpperCase();
  }
  return (words.first[0] + words.elementAt(1)[0]).toUpperCase();
}
