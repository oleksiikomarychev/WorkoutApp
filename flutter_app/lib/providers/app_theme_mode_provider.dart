import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:shared_preferences/shared_preferences.dart';

const _kThemeModePrefsKey = 'app_theme_mode';

final appThemeModeProvider = StateNotifierProvider<AppThemeModeController, ThemeMode>((ref) {
  return AppThemeModeController();
});

class AppThemeModeController extends StateNotifier<ThemeMode> {
  bool _loaded = false;
  ThemeMode? _pending;

  AppThemeModeController() : super(ThemeMode.system) {
    unawaited(_load());
  }

  Future<void> _load() async {
    final prefs = await SharedPreferences.getInstance();
    final raw = prefs.getString(_kThemeModePrefsKey);
    final parsed = _parse(raw);
    state = parsed ?? ThemeMode.system;
    _loaded = true;

    final pending = _pending;
    if (pending != null) {
      _pending = null;
      await setThemeMode(pending);
    }
  }

  ThemeMode? _parse(String? raw) {
    switch ((raw ?? '').trim()) {
      case 'system':
        return ThemeMode.system;
      case 'light':
        return ThemeMode.light;
      case 'dark':
        return ThemeMode.dark;
    }
    return null;
  }

  String _serialize(ThemeMode mode) {
    switch (mode) {
      case ThemeMode.system:
        return 'system';
      case ThemeMode.light:
        return 'light';
      case ThemeMode.dark:
        return 'dark';
    }
  }

  Future<void> setThemeMode(ThemeMode mode) async {
    if (!_loaded) {
      _pending = mode;
      return;
    }

    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(_kThemeModePrefsKey, _serialize(mode));
    state = mode;
  }
}
