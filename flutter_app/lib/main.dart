import 'package:firebase_core/firebase_core.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_dotenv/flutter_dotenv.dart';
import 'package:provider/provider.dart' as pv;
import 'package:workout_app/firebase_options.dart';
import 'package:workout_app/features/auth/auth_gate.dart';
import 'package:workout_app/features/auth/auth_service.dart';
import 'package:workout_app/services/api_client.dart';
import 'package:workout_app/services/exercise_service.dart';
import 'package:workout_app/services/rpe_service.dart';
import 'package:workout_app/services/chat_service.dart';
import 'package:workout_app/screens/coach/coach_dashboard_screen.dart';
import 'package:workout_app/screens/coach/coach_athletes_screen.dart';
import 'package:workout_app/screens/coach/athlete_detail_screen.dart';
import 'package:workout_app/screens/coach/coach_relationships_screen.dart';
import 'package:workout_app/screens/coaching/my_coaches_screen.dart';
import 'package:workout_app/screens/coach/coach_chat_screen.dart';
import 'package:workout_app/screens/social/social_feed_screen.dart';
import 'package:workout_app/config/constants/route_names.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();


  await dotenv.load(fileName: 'assets/env/app.env');


  await Firebase.initializeApp(
    options: DefaultFirebaseOptions.currentPlatform,
  );








  runApp(
    const ProviderScope(
      child: MyApp(),
    ),
  );
}

class MyApp extends ConsumerWidget {
  const MyApp({Key? key}) : super(key: key);

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final apiClient = ApiClient();
    return pv.MultiProvider(
      providers: [
        pv.Provider<ApiClient>.value(value: apiClient),
        pv.Provider<ExerciseService>(create: (_) => ExerciseService(apiClient)),
        pv.Provider<RpeService>(create: (_) => RpeService(apiClient)),
        pv.Provider<ChatService>(create: (_) => ChatService()),
      ],
      child: MaterialApp(
        title: 'Workout App',
        theme: ThemeData(
          primarySwatch: Colors.blue,
        ),
        debugShowCheckedModeBanner: false,
        localizationsDelegates: const [
          GlobalMaterialLocalizations.delegate,
          GlobalWidgetsLocalizations.delegate,
          GlobalCupertinoLocalizations.delegate,
        ],
        supportedLocales: const [
          Locale('en'),
          Locale('ru'),
        ],

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
                  builder: (_) => const Scaffold(
                    body: Center(child: Text('Missing athleteId')),
                  ),
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
                  builder: (_) => const Scaffold(
                    body: Center(child: Text('Missing chat arguments')),
                  ),
                  settings: settings,
                );
              }
              return MaterialPageRoute(
                builder: (_) => CoachChatScreen(args: args),
                settings: settings,
              );
          }
          return null;
        },
      ),
    );
  }
}
