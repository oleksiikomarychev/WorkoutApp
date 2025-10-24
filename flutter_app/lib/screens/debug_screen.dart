import 'package:flutter/material.dart';

import 'exercise_list_screen.dart';
import 'exercise_selection_screen.dart';
import 'user_max_screen.dart';
import 'user_profile_screen.dart';
import 'workout_detail_screen.dart';
import 'workout_list_screen.dart';
import 'workouts_screen.dart';
import 'session_history_screen.dart';

class DebugScreen extends StatelessWidget {
  const DebugScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final Map<String, WidgetBuilder> screens = {
      'Exercise Selection': (context) => ExerciseSelectionScreen(),
      'Workout Detail': (context) => WorkoutDetailScreen(workoutId: 1),  // Example ID
      'Workouts': (context) => WorkoutsScreen(),
      'Workout List': (context) => WorkoutListScreen(progressionId: 1),
      'Exercise List': (context) => ExerciseListScreen(),
      'User Maxes': (context) => const UserMaxScreen(),
      'Session History': (context) => const SessionHistoryScreen(),
      'User Profile': (context) => const UserProfileScreen(),
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
