import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:workout_app/config/theme/app_theme.dart';
import 'package:workout_app/l10n/app_localizations.dart';
import 'package:workout_app/models/user_stats.dart';
import 'package:workout_app/providers/app_theme_mode_provider.dart';
import 'package:workout_app/widgets/profile_sections.dart';

void main() {
  test('saved theme is available before the first frame', () async {
    SharedPreferences.setMockInitialValues({'app_theme_mode': 'dark'});
    final mode = await AppThemeModeController.loadInitialThemeMode();
    expect(mode, ThemeMode.dark);
    final controller = AppThemeModeController(initialThemeMode: mode);
    expect(controller.debugState, ThemeMode.dark);
    controller.dispose();
  });

  testWidgets('profile stat cards use the active color scheme', (tester) async {
    const stats = UserStats(
      totalWorkouts: 8,
      totalVolume: 1200,
      activeDays: 4,
      activityMap: {},
      completedSessions: [],
      maxDayVolume: 0,
      weeks: 1,
    );

    for (final mode in [ThemeMode.light, ThemeMode.dark]) {
      final theme = mode == ThemeMode.light
          ? AppTheme.lightTheme()
          : AppTheme.darkTheme();
      await tester.pumpWidget(
        MaterialApp(
          theme: AppTheme.lightTheme(),
          darkTheme: AppTheme.darkTheme(),
          themeMode: mode,
          localizationsDelegates: AppLocalizations.localizationsDelegates,
          supportedLocales: AppLocalizations.supportedLocales,
          home: const Scaffold(body: ProfileStatsRow(stats: stats)),
        ),
      );
      await tester.pumpAndSettle();

      final value = tester.widget<Text>(find.text('8'));
      expect(value.style?.color, theme.colorScheme.onTertiaryContainer);
      final card = tester.widget<Container>(
        find
            .ancestor(of: find.text('8'), matching: find.byType(Container))
            .first,
      );
      expect(
        (card.decoration as BoxDecoration).color,
        theme.colorScheme.tertiaryContainer,
      );
    }
  });
}
