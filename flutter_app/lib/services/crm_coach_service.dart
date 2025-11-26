import 'package:workout_app/config/api_config.dart';
import 'package:workout_app/models/applied_calendar_plan.dart';
import 'package:workout_app/models/workout.dart';
import 'package:workout_app/models/exercise_instance.dart';
import 'package:workout_app/services/api_client.dart';
import 'package:workout_app/services/base_api_service.dart';
import 'package:workout_app/services/logger_service.dart';

class CrmCoachService extends BaseApiService {
  final LoggerService _logger = LoggerService('CrmCoachService');

  CrmCoachService(ApiClient apiClient) : super(apiClient);

  Future<AppliedCalendarPlan?> getAthleteActivePlan(String athleteId) async {
    try {
      final endpoint = ApiConfig.crmCoachActivePlanEndpoint(athleteId);
      final response = await apiClient.get(endpoint);
      if (response is Map<String, dynamic>) {
        return AppliedCalendarPlan.fromJson(response);
      }
      return null;
    } catch (e, st) {
      handleError('Failed to fetch athlete active plan', e, st);
    }
  }

  Future<List<Workout>> getAthleteActivePlanWorkouts(String athleteId) async {
    try {
      final endpoint = ApiConfig.crmCoachActivePlanWorkoutsEndpoint(athleteId);
      final response = await apiClient.get(endpoint);
      if (response is List) {
        return response
            .whereType<Map<String, dynamic>>()
            .map(Workout.fromJson)
            .toList();
      }
      return const [];
    } catch (e, st) {
      handleError('Failed to fetch athlete workouts', e, st);
    }
  }

  Future<Workout> updateAthleteWorkout({
    required String athleteId,
    required int workoutId,
    required Map<String, dynamic> payload,
  }) async {
    if (payload.isEmpty) {
      throw ArgumentError('payload must not be empty');
    }
    try {
      final endpoint = ApiConfig.crmCoachWorkoutEndpoint(athleteId, workoutId);
      final response = await apiClient.patch(
        endpoint,
        payload,
        context: 'CrmCoachService.updateAthleteWorkout',
      );
      if (response is Map<String, dynamic>) {
        return Workout.fromJson(response);
      }
      throw Exception('Unexpected response when updating workout');
    } catch (e, st) {
      handleError('Failed to update athlete workout', e, st);
    }
  }

  Future<ExerciseInstance> updateExerciseInstance({
    required String athleteId,
    required int instanceId,
    required Map<String, dynamic> payload,
  }) async {
    if (payload.isEmpty) {
      throw ArgumentError('payload must not be empty');
    }
    try {
      final endpoint = ApiConfig.crmCoachExerciseEndpoint(athleteId, instanceId);
      final response = await apiClient.patch(
        endpoint,
        payload,
        context: 'CrmCoachService.updateExerciseInstance',
      );
      if (response is Map<String, dynamic>) {
        return ExerciseInstance.fromJson(response);
      }
      throw Exception('Unexpected response when updating exercise instance');
    } catch (e, st) {
      handleError('Failed to update exercise instance', e, st);
    }
  }
}
