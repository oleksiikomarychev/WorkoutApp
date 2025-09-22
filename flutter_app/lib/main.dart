import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:workout_app/screens/splash_screen_new.dart';
import 'package:workout_app/screens/home_screen_new.dart';
import 'package:workout_app/screens/workouts_screen.dart';
import 'package:workout_app/screens/calendar_plans_screen.dart';
import 'package:workout_app/services/rpe_service.dart';

// TEMPORARY DEMO: Add demo screen imports
import 'package:workout_app/screens/demo/demo_workouts_screen.dart';
import 'package:workout_app/screens/demo/demo_calendar_plans_screen.dart';
import 'package:workout_app/screens/demo/demo_crm_screen.dart';
import 'package:workout_app/screens/demo/demo_navbar.dart';

// Create a Provider for RpeService
final rpeServiceProvider = Provider<RpeService>((ref) => RpeService());

void main() {
  runApp(
    ProviderScope(
      overrides: [rpeServiceProvider],
      child: const MyApp(),
    ),
  );
}

class MyApp extends StatelessWidget {
  const MyApp({super.key});

  @override
  Widget build(BuildContext context) {
    return const MainApp();
  }
}

class MainApp extends StatefulWidget {
  const MainApp({super.key});

  @override
  State<MainApp> createState() => _MainAppState();
}

class _MainAppState extends State<MainApp> {
  int _currentIndex = 0;

  // TEMPORARY DEMO: Using demo screens
  final List<Widget> _screens = [
    const DemoWorkoutsScreen(),
    DemoCalendarPlansScreen(),
    const DemoCRMScreen(),
  ];

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      home: Scaffold(
        body: _screens[_currentIndex],
        // TEMPORARY DEMO: Using demo navbar
        bottomNavigationBar: DemoNavBar(
          currentIndex: _currentIndex,
          onTap: (index) => setState(() => _currentIndex = index),
        ),
      ),
    );
  }
}