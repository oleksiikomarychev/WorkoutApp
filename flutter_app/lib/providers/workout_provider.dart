import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:workout_app/services/workout_service.dart';
import 'package:workout_app/models/workout.dart';
import 'package:workout_app/services/service_locator.dart';

final workoutProvider = FutureProvider.family<Workout, int>((ref, workoutId) async {
  final workoutService = ref.watch(workoutServiceProvider);
  return await workoutService.getWorkoutWithDetails(workoutId);
});
