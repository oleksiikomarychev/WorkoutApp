import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:workout_app/services/api_client.dart';
import 'package:workout_app/services/user_max_service.dart';
import 'package:workout_app/services/workout_session_service.dart';

// API Client Provider
final apiClientProvider = Provider<ApiClient>((ref) {
  return ApiClient();
});

// User Max Service Provider
final userMaxServiceProvider = Provider<UserMaxService>((ref) {
  final apiClient = ref.watch(apiClientProvider);
  return UserMaxService(apiClient);
});

// Workout Session Service Provider
final workoutSessionServiceProvider = Provider<WorkoutSessionService>((ref) {
  final apiClient = ref.watch(apiClientProvider);
  return WorkoutSessionService(apiClient);
});
