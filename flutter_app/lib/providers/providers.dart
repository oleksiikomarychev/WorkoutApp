import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:workout_app/services/api_client.dart';
import 'package:workout_app/services/workout_session_service.dart';

// API Client Provider
final apiClientProvider = Provider<ApiClient>((ref) {
  return ApiClient();
});

// Workout Session Service Provider
final workoutSessionServiceProvider = Provider<WorkoutSessionService>((ref) {
  final apiClient = ref.watch(apiClientProvider);
  return WorkoutSessionService(apiClient);
});
