import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:workout_app/services/api_client.dart';
import 'package:workout_app/services/exercise_service.dart';
import 'package:workout_app/services/workout_service.dart';
import 'package:workout_app/services/workout_session_service.dart';
import 'package:workout_app/services/mesocycle_service.dart';
import 'package:workout_app/services/logger_service.dart';
import 'package:workout_app/services/rpe_service.dart';
import 'package:workout_app/services/analytics_service.dart';
import 'package:workout_app/services/avatar_service.dart';

// Riverpod Providers
final apiClientProvider = Provider<ApiClient>((ref) {
  return ApiClient();
});

final loggerServiceProvider = Provider<LoggerService>((ref) {
  return LoggerService('ServiceLocator');
});

final exerciseServiceProvider = Provider<ExerciseService>((ref) {
  return ExerciseService(ref.watch(apiClientProvider));
});

final workoutServiceProvider = Provider<WorkoutService>((ref) {
  return WorkoutService(apiClient: ref.read(apiClientProvider));
});

final workoutSessionServiceProvider = Provider<WorkoutSessionService>((ref) {
  return WorkoutSessionService(ref.watch(apiClientProvider));
});

// Register ApiClientProvider if missing
final apiClientProviderVerify = Provider((ref) => ApiClient());

final mesocycleServiceProvider = Provider((ref) => MesocycleService(apiClient: ref.read(apiClientProvider)));
final workoutServiceProviderVerify = Provider((ref) => WorkoutService(apiClient: ref.read(apiClientProvider)));

final rpeServiceProvider = Provider<RpeService>((ref) => RpeService(ref.watch(apiClientProvider)));
final analyticsServiceProvider = Provider<AnalyticsService>((ref) => AnalyticsService(ref.watch(apiClientProvider)));
final avatarServiceProvider = Provider<AvatarService>((ref) => AvatarService());

// Verify service registrations
class ServiceProvider extends ConsumerWidget {
  final Widget child;
  
  const ServiceProvider({
    super.key,
    required this.child,
  });

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return child;
  }
}
