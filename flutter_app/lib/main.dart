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

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  
  // Load environment variables
  await dotenv.load(fileName: 'assets/env/app.env');
  
  // Initialize Firebase
  await Firebase.initializeApp(
    options: DefaultFirebaseOptions.currentPlatform,
  );
  
  // Configure Firebase Auth Emulator for local development
  // Uncomment the following lines to use the emulator in debug mode:
  // if (kDebugMode) {
  //   final authService = AuthService();
  //   authService.useAuthEmulator(host: 'localhost', port: 9099);
  // }
  
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
        localizationsDelegates: const [
          GlobalMaterialLocalizations.delegate,
          GlobalWidgetsLocalizations.delegate,
          GlobalCupertinoLocalizations.delegate,
        ],
        supportedLocales: const [
          Locale('en'),
          Locale('ru'),
        ],
        // Use AuthGate to handle authentication-based routing
        home: const AuthGate(),
      ),
    );
  }
}
