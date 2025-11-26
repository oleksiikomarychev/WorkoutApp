import 'package:flutter/material.dart';
import 'package:workout_app/config/constants/theme_constants.dart';
import 'package:workout_app/models/workout.dart';

class WorkoutStatusView {
  final String label;
  final Color background;
  final Color textColor;
  final Color dotColor;

  const WorkoutStatusView({
    required this.label,
    required this.background,
    required this.textColor,
    required this.dotColor,
  });
}

WorkoutStatusView workoutStatusView(Workout workout) {
  final completed = (workout.status?.toLowerCase() == 'completed') || (workout.completedAt != null);
  final inProgress = (workout.startedAt != null) && (workout.completedAt == null);
  if (completed) {
    return const WorkoutStatusView(
      label: 'Completed',
      background: Color(0xFFEFF8F2),
      textColor: Colors.green,
      dotColor: Colors.green,
    );
  } else if (inProgress) {
    return WorkoutStatusView(
      label: 'In Progress',
      background: const Color(0xFFEAEFFF),
      textColor: AppColors.primary,
      dotColor: AppColors.primary,
    );
  } else {
    return const WorkoutStatusView(
      label: 'Planned',
      background: Color(0xFFFFEBEE),
      textColor: Colors.redAccent,
      dotColor: Colors.redAccent,
    );
  }
}

class WorkoutStatusCounts {
  final int planned;
  final int inProgress;
  final int completed;

  const WorkoutStatusCounts({required this.planned, required this.inProgress, required this.completed});
}

WorkoutStatusCounts workoutStatusCounts(List<Workout> workouts) {
  int planned = 0;
  int inProgress = 0;
  int completed = 0;
  for (final w in workouts) {
    final status = workoutStatusView(w);
    if (status.label == 'Completed') {
      completed++;
    } else if (status.label == 'In Progress') {
      inProgress++;
    } else {
      planned++;
    }
  }
  return WorkoutStatusCounts(planned: planned, inProgress: inProgress, completed: completed);
}

Widget workoutStatusDot(Color color) {
  return Container(
    margin: const EdgeInsets.symmetric(horizontal: 1.5),
    width: 6,
    height: 6,
    decoration: BoxDecoration(color: color, shape: BoxShape.circle),
  );
}
