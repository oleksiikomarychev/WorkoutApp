import 'package:flutter/material.dart';
import '../../models/workout.dart';

class WorkoutHeader extends StatelessWidget {
  final Workout? workout;
  
  const WorkoutHeader({super.key, this.workout});

  @override
  Widget build(BuildContext context) {
    return const Column(
      children: [
        // Header content will be moved here
      ],
    );
  }
}
