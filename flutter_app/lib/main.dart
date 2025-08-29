import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_dotenv/flutter_dotenv.dart';
import 'package:firebase_core/firebase_core.dart';
import 'package:workout_app/firebase_options.dart';
import 'package:firebase_auth/firebase_auth.dart';
import 'package:flutter/foundation.dart' show kIsWeb;
import 'package:workout_app/config/constants/app_constants.dart';
import 'package:workout_app/screens/auth_gate.dart';
import 'package:workout_app/services/service_locator.dart';
import 'package:workout_app/services/logger_service.dart';
import 'package:workout_app/config/theme/app_theme.dart';

Future<void> main() async {
  // Ensure Flutter binding is initialized
  WidgetsFlutterBinding.ensureInitialized();

  // Initialize Firebase
    await Firebase.initializeApp(
    options: DefaultFirebaseOptions.currentPlatform,
  );

  // Web: ensure auth persistence is LOCAL so authStateChanges works reliably
  if (kIsWeb) {
    try {
      await FirebaseAuth.instance.setPersistence(Persistence.LOCAL);
    } catch (e) {
      // ignore but log
      // ignore: avoid_print
      print('Warning: setPersistence failed: $e');
    }
  }

  // Initialize environment variables
  try {
    await dotenv.load(fileName: ".env");
  } catch (e) {
    print('Warning: Could not load .env file: $e');
  }

  // Initialize dependency injection
  // No dependency injection initialization needed

  // Set preferred orientations
  // No orientation restrictions needed for macOS

  // Configure system UI overlay style
  // No system UI overlay style needed for macOS

  // Initialize app with providers
  runApp(
    ProviderScope(
      child: ServiceProvider(
        child: const MyApp(),
      ),
    ),
  );
  
  // Log app start
  final logger = LoggerService('main');
  logger.i('Application started');
}

class MyApp extends StatelessWidget {
  const MyApp({super.key});

  @override
  Widget build(BuildContext context) {
    // Initialize logger for widget build
    final logger = context.logger;
    logger.d('Building MyApp');
    
    return MaterialApp(
      title: AppConstants.appName,
      debugShowCheckedModeBanner: false,
      theme: AppTheme.lightTheme(),
      localizationsDelegates: const [
        GlobalMaterialLocalizations.delegate,
        GlobalWidgetsLocalizations.delegate,
        GlobalCupertinoLocalizations.delegate,
      ],
      supportedLocales: const [
        Locale('en', ''),
      ],
      home: const AuthGate(),
      darkTheme: AppTheme.darkTheme(),

    );
  }
}

class SplashScreen extends StatelessWidget {
  const SplashScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: const [
            CircularProgressIndicator(),
            SizedBox(height: 16),
            Text(
              AppConstants.appName,
              style: TextStyle(fontSize: 24),
            ),
          ],
        ),
      ),
    );
  }
}