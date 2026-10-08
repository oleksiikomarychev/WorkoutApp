import 'package:firebase_core/firebase_core.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_dotenv/flutter_dotenv.dart';
import 'package:workout_app/l10n/app_localizations.dart';
import 'package:provider/provider.dart' as pv;
import 'package:workout_app/providers/app_locale_provider.dart';
import 'package:workout_app/providers/app_theme_mode_provider.dart';
import 'package:workout_app/firebase_options.dart';
import 'package:workout_app/features/auth/auth_gate.dart';
import 'package:workout_app/features/auth/auth_service.dart';
import 'package:workout_app/services/api_client.dart';
import 'package:workout_app/services/exercise_service.dart';
import 'package:workout_app/services/rpe_service.dart';
import 'package:workout_app/services/chat_service.dart';
import 'package:workout_app/config/theme/app_theme.dart';
import 'package:workout_app/screens/coach/coach_dashboard_screen.dart';
import 'package:workout_app/screens/coach/coach_athletes_screen.dart';
import 'package:workout_app/screens/coach/athlete_detail_screen.dart';
import 'package:workout_app/screens/coach/coach_relationships_screen.dart';
import 'package:workout_app/screens/coaching/my_coaches_screen.dart';
import 'package:workout_app/screens/coach/coach_chat_screen.dart';
import 'package:workout_app/screens/social/social_feed_screen.dart';
import 'package:workout_app/screens/settings/settings_general_screen.dart';
import 'package:workout_app/screens/settings/settings_home_screen.dart';
import 'package:workout_app/screens/settings/settings_import_screen.dart';
import 'package:workout_app/screens/settings/settings_legal_screen.dart';
import 'package:workout_app/screens/debug/amplitude_test_screen.dart';
import 'package:workout_app/config/constants/route_names.dart';
import 'package:workout_app/services/amplitude_service.dart';
import 'package:workout_app/src/widgets/snack_utils.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();

  try {
    await dotenv.load(fileName: 'assets/env/app.env', isOptional: true);
  } catch (e) {
    dotenv.testLoad(fileInput: '');
    if (kDebugMode) {
      debugPrint('dotenv load skipped: $e');
    }
  }

  // Попробуем инициализировать Firebase только если это необходимо,
  // но не будем ждать завершения, если он уже инициализирован.
  try {
    await Firebase.initializeApp(
      options: DefaultFirebaseOptions.currentPlatform,
    );
  } catch (e) {
    // Игнорируем ошибку, если Firebase уже инициализирован
    if (e.toString().contains('duplicate-app')) {
      debugPrint('Firebase already initialized.');
    } else {
      rethrow;
    }
  }

  runApp(const ProviderScope(child: MyApp()));
}

class MyApp extends ConsumerWidget {
  const MyApp({Key? key}) : super(key: key);

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final apiClient = ApiClient();
    final appLocale = ref.watch(appLocaleProvider);
    final themeMode = ref.watch(appThemeModeProvider);
    return pv.MultiProvider(
      providers: [
        pv.Provider<ApiClient>.value(value: apiClient),
        pv.Provider<ExerciseService>(create: (_) => ExerciseService(apiClient)),
        pv.Provider<RpeService>(create: (_) => RpeService(apiClient)),
        pv.Provider<ChatService>(create: (_) => ChatService()),
      ],
      child: MaterialApp(
        scaffoldMessengerKey: rootScaffoldMessengerKey,
        onGenerateTitle: (context) => AppLocalizations.of(context).appTitle,
        theme: AppTheme.lightTheme(),
        darkTheme: AppTheme.darkTheme(),
        themeMode: themeMode,
        debugShowCheckedModeBanner: false,
        localizationsDelegates: AppLocalizations.localizationsDelegates,
        supportedLocales: AppLocalizations.supportedLocales,
        locale: appLocale,

        home: const AuthGate(),
        onGenerateRoute: (settings) {
          switch (settings.name) {
            case RouteNames.coachDashboard:
              return MaterialPageRoute(
                builder: (_) => const CoachDashboardScreen(),
                settings: settings,
              );
            case RouteNames.coachAthletes:
              return MaterialPageRoute(
                builder: (_) => const CoachAthletesScreen(),
                settings: settings,
              );
            case RouteNames.coachAthleteDetail:
              final athleteId = settings.arguments as String?;
              if (athleteId == null) {
                return MaterialPageRoute(
                  builder: (context) {
                    final l10n = AppLocalizations.of(context);
                    return Scaffold(
                      body: Center(child: Text(l10n.missingAthleteId)),
                    );
                  },
                  settings: settings,
                );
              }
              return MaterialPageRoute(
                builder: (_) => AthleteDetailScreen(athleteId: athleteId),
                settings: settings,
              );
            case RouteNames.socialFeed:
              return MaterialPageRoute(
                builder: (_) => SocialFeedScreen(),
                settings: settings,
              );
            case RouteNames.coachRelationships:
              return MaterialPageRoute(
                builder: (_) => const CoachRelationshipsScreen(),
                settings: settings,
              );
            case RouteNames.myCoaches:
              return MaterialPageRoute(
                builder: (_) => const MyCoachesScreen(),
                settings: settings,
              );
            case RouteNames.coachChat:
              final args = settings.arguments;
              if (args is! CoachChatScreenArgs) {
                return MaterialPageRoute(
                  builder: (context) {
                    final l10n = AppLocalizations.of(context);
                    return Scaffold(
                      body: Center(child: Text(l10n.missingChatArguments)),
                    );
                  },
                  settings: settings,
                );
              }
              return MaterialPageRoute(
                builder: (_) => CoachChatScreen(args: args),
                settings: settings,
              );
            case RouteNames.settings:
              return MaterialPageRoute(
                builder: (_) => const SettingsHomeScreen(),
                settings: settings,
              );
            case RouteNames.settingsGeneral:
              return MaterialPageRoute(
                builder: (_) => const SettingsGeneralScreen(),
                settings: settings,
              );
            case RouteNames.settingsImport:
              return MaterialPageRoute(
                builder: (_) => const SettingsImportScreen(),
                settings: settings,
              );
            case RouteNames.settingsLegal:
              return MaterialPageRoute(
                builder: (_) => const SettingsLegalScreen(),
                settings: settings,
              );
            case RouteNames.amplitudeTest:
              return MaterialPageRoute(
                builder: (_) => const AmplitudeTestScreen(),
                settings: settings,
              );
          }
          return null;
        },
      ),
    );
  }
}
