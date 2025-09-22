import 'package:flutter/material.dart';
import 'package:workout_app/screens/exercise_selection_screen.dart';
import 'package:workout_app/screens/login_screen.dart';
import 'package:workout_app/screens/profile_screen.dart';
import 'package:workout_app/screens/registration_screen.dart';
import 'package:workout_app/screens/settings_screen.dart';
import 'package:workout_app/screens/user_base_screen.dart';
import 'package:workout_app/screens/workout_creation_screen.dart';
import 'package:workout_app/screens/workout_detail_screen.dart';
import 'package:workout_app/screens/workout_history_screen.dart';
import 'package:workout_app/screens/workout_list_screen.dart';
import 'package:workout_app/screens/workout_session_screen.dart';
import 'package:workout_app/screens/workouts_screen.dart';

class DebugScreen extends StatelessWidget {
  const DebugScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final screens = <String, WidgetBuilder>{
      'Exercise Selection': (context) => const ExerciseSelectionScreen(),
      'Workout Creation': (context) => const WorkoutCreationScreen(),
      'Workout Detail': (context) => const WorkoutDetailScreen(),
      'Workout History': (context) => const WorkoutHistoryScreen(),
      'Workout Session': (context) => const WorkoutSessionScreen(),
      'Workouts': (context) => const WorkoutsScreen(),
      'Workout List': (context) => const WorkoutListScreen(),
    };

    return Scaffold(
      appBar: AppBar(title: const Text('Debug Screen')),
      body: ListView(
        children: [
          ListTile(
            title: const Text('Reset app state'),
            onTap: () {},
          ),
          ListTile(
            title: const Text('Clear cache'),
            onTap: () {},
          ),
          ...screens.entries.map((entry) {
            return ListTile(
              title: Text(entry.key),
              onTap: () => Navigator.push(context, MaterialPageRoute(builder: entry.value)),
            );
          }),
        ],
      ),
    );
  }
}
