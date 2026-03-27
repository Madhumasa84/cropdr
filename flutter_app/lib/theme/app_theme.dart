import 'package:flutter/material.dart';

class AppColors {
  static const pine = Color(0xFF24553A);
  static const moss = Color(0xFF5E8E52);
  static const leaf = Color(0xFF96B96A);
  static const canvas = Color(0xFFF6F4EC);
  static const panel = Colors.white;
  static const ink = Color(0xFF193125);
  static const softInk = Color(0xFF617264);
  static const border = Color(0xFFD7E1D2);
  static const danger = Color(0xFFBE3A34);
  static const warning = Color(0xFFD88B2F);
  static const success = Color(0xFF2E8B57);
}

ThemeData buildAppTheme() {
  final base = ThemeData(
    useMaterial3: true,
    colorScheme: ColorScheme.fromSeed(
      seedColor: AppColors.pine,
      brightness: Brightness.light,
    ),
    scaffoldBackgroundColor: AppColors.canvas,
    fontFamily: 'Roboto',
  );

  return base.copyWith(
    appBarTheme: const AppBarTheme(
      backgroundColor: AppColors.canvas,
      foregroundColor: AppColors.ink,
      elevation: 0,
      scrolledUnderElevation: 0,
      surfaceTintColor: Colors.transparent,
      titleTextStyle: TextStyle(
        fontSize: 20,
        fontWeight: FontWeight.w700,
        color: AppColors.ink,
      ),
    ),
    cardTheme: CardThemeData(
      color: AppColors.panel,
      elevation: 0,
      margin: EdgeInsets.zero,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(22),
        side: const BorderSide(color: AppColors.border),
      ),
    ),
    elevatedButtonTheme: ElevatedButtonThemeData(
      style: ElevatedButton.styleFrom(
        backgroundColor: AppColors.pine,
        foregroundColor: Colors.white,
        minimumSize: const Size(double.infinity, 56),
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(18),
        ),
        textStyle: const TextStyle(
          fontSize: 16,
          fontWeight: FontWeight.w700,
        ),
      ),
    ),
    outlinedButtonTheme: OutlinedButtonThemeData(
      style: OutlinedButton.styleFrom(
        foregroundColor: AppColors.pine,
        side: const BorderSide(color: AppColors.pine),
        minimumSize: const Size(0, 52),
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(18),
        ),
        textStyle: const TextStyle(
          fontSize: 15,
          fontWeight: FontWeight.w600,
        ),
      ),
    ),
    inputDecorationTheme: InputDecorationTheme(
      filled: true,
      fillColor: Colors.white,
      contentPadding: const EdgeInsets.symmetric(horizontal: 18, vertical: 16),
      enabledBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(18),
        borderSide: const BorderSide(color: AppColors.border),
      ),
      focusedBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(18),
        borderSide: const BorderSide(color: AppColors.pine, width: 1.5),
      ),
    ),
  );
}

Color severityColor(String severity) {
  final normalized = severity.trim().toUpperCase();
  switch (normalized) {
    case 'HIGH':
    case 'SEVERE':
      return AppColors.danger;
    case 'MEDIUM':
    case 'MODERATE':
      return AppColors.warning;
    default:
      return AppColors.success;
  }
}

String severityLabel(String severity) {
  final normalized = severity.trim().toUpperCase();
  switch (normalized) {
    case 'HIGH':
    case 'SEVERE':
      return 'High Risk';
    case 'MEDIUM':
    case 'MODERATE':
      return 'Moderate Risk';
    default:
      return 'Low Risk';
  }
}
