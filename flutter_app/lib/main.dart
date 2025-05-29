import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:provider/provider.dart';
import 'package:dynamic_color/dynamic_color.dart';
import 'package:google_fonts/google_fonts.dart';

import 'screens/home_screen.dart';
import 'services/api_client.dart';
import 'services/workout_service.dart';
import 'services/exercise_service.dart';
import 'services/user_max_service.dart';
import 'services/progression_service.dart';


const _primaryColor = Color(0xFF0063B0);

void main() async {
  WidgetsFlutterBinding.ensureInitialized();
  

  await SystemChrome.setPreferredOrientations([
    DeviceOrientation.portraitUp,
    DeviceOrientation.portraitDown,
  ]);
  

  SystemChrome.setSystemUIOverlayStyle(
    const SystemUiOverlayStyle(
      statusBarColor: Colors.transparent,
      systemNavigationBarColor: Colors.transparent,
      systemNavigationBarDividerColor: Colors.transparent,
    ),
  );
  
  runApp(const MyApp());
}

class MyApp extends StatelessWidget {
  const MyApp({super.key});

  @override
  Widget build(BuildContext context) {
    return DynamicColorBuilder(
      builder: (ColorScheme? lightDynamic, ColorScheme? darkDynamic) {

        ColorScheme lightColorScheme;
        ColorScheme darkColorScheme;

        if (lightDynamic != null && darkDynamic != null) {

          lightColorScheme = lightDynamic;
          darkColorScheme = darkDynamic;
        } else {

          lightColorScheme = ColorScheme.fromSeed(
            seedColor: _primaryColor,
            brightness: Brightness.light,
          );
          darkColorScheme = ColorScheme.fromSeed(
            seedColor: _primaryColor,
            brightness: Brightness.dark,
          );
        }

        return MultiProvider(
          providers: [
            Provider<ApiClient>(
              create: (_) => ApiClient(baseUrl: 'http://localhost:8000'),
            ),
            ProxyProvider<ApiClient, WorkoutService>(
              update: (_, apiClient, __) => WorkoutService(apiClient),
            ),
            ProxyProvider<ApiClient, ExerciseService>(
              update: (_, apiClient, __) => ExerciseService(apiClient),
            ),
            ProxyProvider<ApiClient, UserMaxService>(
              update: (_, apiClient, __) => UserMaxService(apiClient),
            ),
            ProxyProvider<ApiClient, ProgressionService>(
              update: (_, apiClient, __) => ProgressionService(apiClient),
            ),
          ],
          child: MaterialApp(
            title: 'Workout App',
            theme: ThemeData(
              colorScheme: lightColorScheme,
              useMaterial3: true,
              fontFamily: 'Montserrat',
              textTheme: GoogleFonts.montserratTextTheme(
                Theme.of(context).textTheme,
              ),
              appBarTheme: AppBarTheme(
                centerTitle: true,
                backgroundColor: lightColorScheme.primaryContainer,
                foregroundColor: lightColorScheme.onPrimaryContainer,
                elevation: 0,
                systemOverlayStyle: SystemUiOverlayStyle.light,
              ),
              cardTheme: CardTheme(
                elevation: 0,
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
                clipBehavior: Clip.antiAlias,
              ),
              elevatedButtonTheme: ElevatedButtonThemeData(
                style: ElevatedButton.styleFrom(
                  padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 12),
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                ),
              ),
              navigationBarTheme: NavigationBarThemeData(
                indicatorColor: lightColorScheme.primaryContainer,
                labelBehavior: NavigationDestinationLabelBehavior.onlyShowSelected,
              ),
              snackBarTheme: SnackBarThemeData(
                behavior: SnackBarBehavior.floating,
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
              ),
            ),
            darkTheme: ThemeData(
              colorScheme: darkColorScheme,
              useMaterial3: true,
              fontFamily: 'Montserrat',
              textTheme: GoogleFonts.montserratTextTheme(
                ThemeData.dark().textTheme,
              ),
              appBarTheme: AppBarTheme(
                centerTitle: true,
                backgroundColor: darkColorScheme.surfaceVariant,
                foregroundColor: darkColorScheme.onSurfaceVariant,
                elevation: 0,
                systemOverlayStyle: SystemUiOverlayStyle.dark,
              ),
              cardTheme: CardTheme(
                elevation: 0,
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
                clipBehavior: Clip.antiAlias,
              ),
              elevatedButtonTheme: ElevatedButtonThemeData(
                style: ElevatedButton.styleFrom(
                  padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 12),
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                ),
              ),
              navigationBarTheme: NavigationBarThemeData(
                indicatorColor: darkColorScheme.primaryContainer,
                labelBehavior: NavigationDestinationLabelBehavior.onlyShowSelected,
              ),
              snackBarTheme: SnackBarThemeData(
                behavior: SnackBarBehavior.floating,
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
              ),
            ),
            themeMode: ThemeMode.system,
            debugShowCheckedModeBanner: false,
            home: const HomeScreen(),
          ),
        );
      },
    );
  }
}
