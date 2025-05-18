import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'screens/home_screen.dart';
import 'services/api_client.dart';
import 'services/workout_service.dart';
import 'services/exercise_service.dart';
import 'services/user_max_service.dart';
import 'services/progression_service.dart';
void main() {
  runApp(const MyApp());
}
class MyApp extends StatelessWidget {
  const MyApp({Key? key}) : super(key: key);
  @override
  Widget build(BuildContext context) {
    return MultiProvider(
      providers: [
        Provider<ApiClient>(
          create: (_) => ApiClient(baseUrl: 'http:
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
          primarySwatch: Colors.blue,
          visualDensity: VisualDensity.adaptivePlatformDensity,
          fontFamily: 'Montserrat',
        ),
        debugShowCheckedModeBanner: false,
        home: const HomeScreen(),
      ),
    );
  }
}
