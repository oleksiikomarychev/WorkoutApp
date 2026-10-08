import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:shared_preferences/shared_preferences.dart';

const _kAppLocalePrefsKey = 'app_locale';

final appLocaleProvider = StateNotifierProvider<AppLocaleController, Locale?>((ref) {
  return AppLocaleController();
});

class AppLocaleController extends StateNotifier<Locale?> {
  bool _loaded = false;
  String? _pendingProfileLanguageCode;

  AppLocaleController() : super(null) {
    unawaited(_load());
  }

  Future<void> _load() async {
    final prefs = await SharedPreferences.getInstance();
    final code = prefs.getString(_kAppLocalePrefsKey);
    if (code == null || code.isEmpty) {
      state = null;
      _loaded = true;

      final pending = _pendingProfileLanguageCode;
      if (pending != null && pending.isNotEmpty) {
        state = Locale(pending);
      }
      return;
    }
    state = Locale(code);
    _loaded = true;
  }

  Future<void> setFromProfileIfUnset(String? languageCode) async {
    if (languageCode == null || languageCode.isEmpty) return;

    if (!_loaded) {
      _pendingProfileLanguageCode = languageCode;
      return;
    }

    final prefs = await SharedPreferences.getInstance();
    final existing = prefs.getString(_kAppLocalePrefsKey);
    if (existing != null && existing.isNotEmpty) return;
    if (state != null) return;

    state = Locale(languageCode);
  }

  Future<void> setSystemLocale() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove(_kAppLocalePrefsKey);
    state = null;
  }

  Future<void> setLocaleCode(String languageCode) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(_kAppLocalePrefsKey, languageCode);
    state = Locale(languageCode);
  }
}
