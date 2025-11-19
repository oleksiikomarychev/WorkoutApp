import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:workout_app/services/api_client.dart';
import 'package:workout_app/models/user_profile.dart';
import 'package:workout_app/services/service_locator.dart' as sl;
import 'package:workout_app/services/workout_session_service.dart';
import 'package:workout_app/models/workout_session.dart';

// API Client Provider
final apiClientProvider = Provider<ApiClient>((ref) {
  return ApiClient();
});

// Workout Session Service Provider
final workoutSessionServiceProvider = Provider<WorkoutSessionService>((ref) {
  final apiClient = ref.watch(apiClientProvider);
  return WorkoutSessionService(apiClient);
});

final completedSessionsProviderFamily = FutureProvider.family<List<WorkoutSession>, int?>((ref, workoutId) async {
  final svc = ref.watch(workoutSessionServiceProvider);
  final items = workoutId != null
      ? await svc.listSessions(workoutId)
      : await svc.listAllSessions();
  final completed = items
      .where((s) => s.status.toLowerCase() == 'completed' || s.finishedAt != null)
      .toList();
  completed.sort((a, b) => b.startedAt.compareTo(a.startedAt));
  return completed.take(20).toList();
});

final completedSessionsProvider = FutureProvider<List<WorkoutSession>>((ref) async {
  return ref.watch(completedSessionsProviderFamily(null).future);
});

final userProfileProvider = FutureProvider<UserProfile>((ref) async {
  final svc = ref.watch(sl.profileServiceProvider);
  return svc.fetchProfile();
});
