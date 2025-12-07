import 'dart:convert';
import '../config/api_config.dart';
import '../models/workout.dart';
import '../models/exercise_instance.dart';
import '../models/user_max.dart';
import 'api_client.dart';
import 'base_api_service.dart';
import 'logger_service.dart';

class WorkoutService extends BaseApiService {
  @override
  final ApiClient apiClient;
  final LoggerService _logger = LoggerService('WorkoutService');

  @override
  WorkoutService({required this.apiClient}) : super(apiClient);


  Future<List<Workout>> getWorkoutsPaged({int skip = 0, int limit = 20}) async {
    try {
      final endpoint = ApiConfig.workoutsEndpointWithPagination(skip, limit);
      final response = await apiClient.get(
        endpoint,
        context: 'WorkoutService.getWorkouts',
      );

      _logger.d('Workout API response: ${jsonEncode(response)}');

      if (response is List) {
        final workouts = <Workout>[];

        for (var item in response.whereType<Map<String, dynamic>>()) {
          try {

            final workout = Workout.fromJson(item).copyWith(
              exerciseInstances: const [],
            );
            workouts.add(workout);
          } catch (e, stackTrace) {
            _logger.e('Error parsing workout item: ${e.toString()}', e, stackTrace);
            _logger.e('Problematic item: ${jsonEncode(item)}');

          }
        }

        return workouts;
      } else if (response is Map<String, dynamic>) {

        try {
          final workout = Workout.fromJson(response).copyWith(exerciseInstances: const []);
          return [workout];
        } catch (e, stackTrace) {
          _logger.e('Error parsing single workout: ${e.toString()}', e, stackTrace);
          _logger.e('Problematic response: ${jsonEncode(response)}');
          return [];
        }
      } else {
        handleError('Invalid response format for workouts list', Exception('Expected a list or map of workouts'));
        return [];
      }
    } catch (e, stackTrace) {
      handleError('Failed to get workouts', e, stackTrace);
      return [];
    }
  }


  Future<Workout> startWorkoutBff(int id, {bool includeDefinitions = true}) async {
    try {
      final endpoint = '${ApiConfig.startWorkoutBffEndpoint(id.toString())}'
          '${includeDefinitions ? '?include=exercise_instances.exercise_definition' : ''}';
      _logger.d('Starting workout via BFF: $endpoint');
      final response = await apiClient.post(
        endpoint,
        <String, dynamic>{},
        context: 'WorkoutService.startWorkoutBff',
      );
      if (response is Map<String, dynamic>) {
        return Workout.fromJson(response);
      } else {
        handleError('Invalid response format when starting workout via BFF',
            Exception('Expected a workout object'));
        throw Exception('Failed to start workout');
      }
    } catch (e, st) {
      handleError('Failed to start workout via BFF', e, st);
      rethrow;
    }
  }


  Future<Workout> finishWorkoutBff(
    int id, {
    bool includeDefinitions = true,
    bool? cancelled,
    bool? markWorkoutCompleted,
  }) async {
    try {
      final endpoint = '${ApiConfig.finishWorkoutBffEndpoint(id.toString())}'
          '${includeDefinitions ? '?include=exercise_instances.exercise_definition' : ''}';
      _logger.d('Finishing workout via BFF: $endpoint');
      final response = await apiClient.post(
        endpoint,
        <String, dynamic>{
          if (cancelled != null) 'cancelled': cancelled,
          if (markWorkoutCompleted != null) 'mark_workout_completed': markWorkoutCompleted,
        },
        context: 'WorkoutService.finishWorkoutBff',
      );
      if (response is Map<String, dynamic>) {
        return Workout.fromJson(response);
      } else {
        handleError('Invalid response format when finishing workout via BFF',
            Exception('Expected a workout object'));
        throw Exception('Failed to finish workout');
      }
    } catch (e, st) {
      handleError('Failed to finish workout via BFF', e, st);
      rethrow;
    }
  }


  Future<List<Workout>> getWorkouts() async {
    return getWorkoutsPaged(skip: 0, limit: 20);
  }


  Future<List<Workout>> getWorkoutsByProgressionId(int progressionId) async {
    try {
      _logger.d('Fetching workouts for progression ID: $progressionId');
      final endpoint = '${ApiConfig.getWorkoutsEndpoint()}?progression_template_id=$progressionId';
      final response = await apiClient.get(
        endpoint,
        context: 'WorkoutService.getWorkoutsByProgressionId',
      );

      if (response is List) {
        return response
            .whereType<Map<String, dynamic>>()
            .map((json) {

              json['exercise_instances'] = json['exercise_instances'] ?? [];
              return Workout.fromJson(json);
            })
            .map((workout) => workout.copyWith(
                  exerciseInstances: workout.exerciseInstances ?? [],
                ))
            .toList();
      } else {
        handleError('Invalid response format for workouts list by progression',
            Exception('Expected a list of workouts for progression'));
        return [];
      }
    } catch (e, stackTrace) {
      handleError('Failed to get workouts by progression ID', e, stackTrace);
      return [];
    }
  }


  Future<Workout> getWorkout(int id) async {
    try {
      final endpoint = ApiConfig.getWorkoutEndpoint(id.toString());
      final response = await apiClient.get(
        endpoint,
        context: 'WorkoutService.getWorkout',
      );

      if (response is Map<String, dynamic>) {

        response['exercise_instances'] = response['exercise_instances'] ?? [];
        return Workout.fromJson(response);
      } else {
        handleError('Invalid response format for workout',
            Exception('Expected a workout object'));
        throw Exception('Failed to get workout');
      }
    } catch (e, stackTrace) {
      handleError('Failed to get workout', e, stackTrace);
      throw Exception('Failed to get workout');
    }
  }


  Future<Workout> getWorkoutWithDetails(int id) async {
    try {
      _logger.d('Fetching workout with ID: $id');
      final response = await apiClient.get(
        '${ApiConfig.getWorkoutsEndpoint()}/$id?include=exercise_instances.exercise_definition',
        context: 'WorkoutService.getWorkoutWithDetails',
      );

      _logger.d('Workout API response: ${jsonEncode(response)}');

      if (response is Map<String, dynamic>) {
        final workout = Workout.fromJson(response);
        _logger.d('Parsed workout: $workout');
        return workout;
      } else {
        _logger.e('Invalid response format when fetching workout');
        throw Exception('Invalid response format when fetching workout');
      }
    } catch (e, stackTrace) {
      _logger.e('Failed to fetch workout', e, stackTrace);
      rethrow;
    }
  }


  Future<Workout> createWorkout(Workout workout) async {
    try {
      final payload = _buildWorkoutPayload(workout);
      _logger.d('Creating workout: $payload');
      final response = await apiClient.post(
        ApiConfig.createWorkoutEndpoint(),
        payload,
        context: 'WorkoutService.createWorkout',
      );

      if (response is Map<String, dynamic>) {
        return Workout.fromJson(response);
      } else {
        _logger.e('Invalid response format when creating workout');
        throw Exception('Failed to create workout');
      }
    } catch (e, stackTrace) {
      _logger.e('Failed to create workout', e, stackTrace);
      rethrow;
    }
  }


  Future<Workout> updateWorkout(Workout workout) async {
    if (workout.id == null) {
      handleError('Cannot update workout without an ID',
          Exception('Workout ID is required'));
      throw Exception('Cannot update workout without an ID');
    }

    try {
      final payload = _buildWorkoutPayload(workout);
      _logger.d('Updating workout ${workout.id}: $payload');
      final response = await apiClient.put(
        '${ApiConfig.getWorkoutsEndpoint()}/${workout.id}',
        payload,
        context: 'WorkoutService.updateWorkout',
      );

      if (response is Map<String, dynamic>) {
        return Workout.fromJson(response);
      } else {
        _logger.e('Invalid response format when updating workout');
        throw Exception('Failed to update workout');
      }
    } catch (e, stackTrace) {
      _logger.e('Failed to update workout', e, stackTrace);
      rethrow;
    }
  }


  Future<void> deleteWorkout(int id) async {
    try {
      _logger.d('Deleting workout with ID: $id');
      await apiClient.delete(
        '${ApiConfig.getWorkoutsEndpoint()}/$id',
        context: 'WorkoutService.deleteWorkout',
      );
    } catch (e, stackTrace) {
      _logger.e('Failed to delete workout', e, stackTrace);
      rethrow;
    }
  }


  Future<List<UserMax>> getUserMaxesForExercise(int exerciseId) async {
    try {
      final endpoint = ApiConfig.userMaxesByExerciseEndpoint(exerciseId.toString());
      final response = await apiClient.get(
        endpoint,
        context: 'WorkoutService.getUserMaxesForExercise',
      );

      if (response is List) {
        return response
            .whereType<Map<String, dynamic>>()
            .map((json) => UserMax.fromJson(json))
            .toList();
      } else {
        handleError('Invalid response format for user maxes',
            Exception('Expected a list of user maxes'));
        return [];
      }
    } catch (e, stackTrace) {
      handleError('Failed to get user maxes for exercise', e, stackTrace);
      rethrow;
    }
  }


  Future<void> deleteExerciseSet(int instanceId, int setId) async {
    try {
      _logger.d('Deleting set $setId from instance $instanceId');


      final endpoint = ApiConfig.deleteExerciseSetEndpoint(
        instanceId.toString(),
        setId.toString(),
      );

      _logger.d('DELETE ExerciseSet | endpoint=$endpoint');

      try {
        final response = await apiClient.delete(
          endpoint,
          context: 'WorkoutService.deleteExerciseSet',
        );
        _logger.d('DELETE successful. Response: $response');
      } catch (e, stackTrace) {
        _logger.e('DELETE failed', e, stackTrace);
        rethrow;
      }

      _logger.d('Successfully processed deletion of set $setId from instance $instanceId');
    } catch (e, stackTrace) {
      _logger.e('Failed to delete exercise set', e, stackTrace);
      rethrow;
    }
  }


  Future<ExerciseInstance> updateExerciseSet({
    required int instanceId,
    required int setId,
    int? reps,
    double? weight,
    double? rpe,
    int? order,
    Map<String, dynamic>? extra,
  }) async {
    try {
      _logger.d('Updating set $setId in instance $instanceId');

      final endpoint = ApiConfig.updateExerciseSetEndpoint(
        instanceId.toString(),
        setId.toString(),
      );

      final payload = <String, dynamic>{
        if (reps != null) 'reps': reps,
        if (weight != null) 'weight': weight,
        if (rpe != null) 'rpe': rpe,
        if (order != null) 'order': order,
        if (extra != null) ...extra,
      };

      _logger.d('PUT ExerciseSet | endpoint=$endpoint | body=$payload');

      final response = await apiClient.put(
        endpoint,
        payload,
        context: 'WorkoutService.updateExerciseSet',
      );

      if (response is Map<String, dynamic>) {
        final updatedInstance = ExerciseInstance.fromJson(response);
        _logger.d('Successfully updated set. Instance: ${updatedInstance.id}');
        return updatedInstance;
      } else {
        handleError('Invalid response format when updating exercise set',
            Exception('Expected an exercise instance object in response'));
        throw Exception('Failed to update exercise set');
      }
    } catch (e, stackTrace) {
      handleError('Failed to update exercise set', e, stackTrace);
      rethrow;
    }
  }


  Future<List<Workout>> getWorkoutsByType(WorkoutType type) async {
    try {
      final typeStr = type.toString().split('.').last;
      final endpoint = ApiConfig.workoutsByTypeEndpoint(typeStr);
      final response = await apiClient.get(
        endpoint,
        context: 'WorkoutService.getWorkoutsByType',
      );

      if (response is List) {
        return response
            .whereType<Map<String, dynamic>>()
            .map((json) => Workout.fromJson(json))
            .toList();
      } else {
        handleError('Invalid response format for workouts by type',
            Exception('Expected a list of workouts'));
        return [];
      }
    } catch (e, stackTrace) {
      handleError('Failed to get workouts by type', e, stackTrace);
      return [];
    }
  }


  Future<Workout?> getNextGeneratedWorkout() async {
    try {
      final endpoint = ApiConfig.nextGeneratedWorkoutEndpoint;
      final response = await apiClient.get(
        endpoint,
        context: 'WorkoutService.getNextGeneratedWorkout',
      );

      if (response is Map<String, dynamic>) {
        return Workout.fromJson(response);
      } else {
        handleError('Invalid response format for next generated workout',
            Exception('Expected a workout object'));
        return null;
      }
    } catch (e, stackTrace) {
      handleError('Failed to get next generated workout', e, stackTrace);
      return null;
    }
  }


  Future<Workout?> getNextWorkoutInPlan(int workoutId) async {
    try {
      final endpoint = '${ApiConfig.nextWorkoutInPlanEndpoint(workoutId.toString())}?include=exercise_instances.exercise_definition';
      final response = await apiClient.get(
        endpoint,
        context: 'WorkoutService.getNextWorkoutInPlan',
      );

      if (response is Map<String, dynamic>) {
        return Workout.fromJson(response);
      } else {
        handleError('Invalid response format for next workout in plan',
            Exception('Expected a workout object'));
        return null;
      }
    } catch (e, stackTrace) {
      handleError('Failed to get next workout in plan', e, stackTrace);
      return null;
    }
  }


  Future<List<Workout>> getWorkoutsByAppliedPlan(int appliedPlanId) async {
    try {
      final endpoint = '${ApiConfig.workoutsEndpoint}?applied_plan_id=$appliedPlanId';
      _logger.d('Fetching workouts by applied plan: $endpoint');
      final response = await apiClient.get(
        endpoint,
        context: 'WorkoutService.getWorkoutsByAppliedPlan',
      );

      if (response is List) {
        return response
            .whereType<Map<String, dynamic>>()
            .map((json) => Workout.fromJson(json))
            .toList();
      } else {
        handleError('Invalid response format for workouts by applied plan',
            Exception('Expected a list of workouts'));
        return [];
      }
    } catch (e, stackTrace) {
      handleError('Failed to get workouts by applied plan', e, stackTrace);
      return [];
    }
  }




  Future<ExerciseInstance> createExerciseInstance(ExerciseInstance instance) async {
    try {
      _logger.d('Creating exercise instance for workout: ${instance.workoutId}');

      final endpoint = ApiConfig.getInstancesByWorkoutEndpoint(instance.workoutId.toString());
      final body = instance.toJson();

      _logger.d('Sending create exercise instance request to $endpoint');
      _logger.d('Request body: $body');

      final response = await apiClient.post(
        endpoint,
        body,
        context: 'WorkoutService.createExerciseInstance',
      );

      if (response is Map<String, dynamic>) {
        final exerciseInstance = ExerciseInstance.fromJson(response);
        _logger.d('Successfully created exercise instance: ${exerciseInstance.id}');
        return exerciseInstance;
      } else {
        handleError('Invalid response format when creating exercise instance',
            Exception('Expected an exercise instance object in response'));
        throw Exception('Failed to create exercise instance');
      }
    } catch (e, stackTrace) {
      handleError('Failed to create exercise instance', e, stackTrace);
      throw Exception('Failed to create exercise instance');
    }
  }

  Future<ExerciseInstance> updateExerciseInstance(ExerciseInstance instance) async {
    try {
      _logger.d('Updating exercise instance: ${instance.id}');

      final endpoint = ApiConfig.updateExerciseInstanceEndpoint(instance.id!.toString());

      final payload = instance.toJson();
      _logger.d('PUT ExerciseInstance | endpoint=$endpoint | body=$payload');
      final response = await apiClient.put(
        endpoint,
        payload,
        context: 'WorkoutService.updateExerciseInstance',
      );

      if (response is Map<String, dynamic>) {
        final updatedInstance = ExerciseInstance.fromJson(response);
        _logger.d('Successfully updated exercise instance: ${updatedInstance.id}');
        return updatedInstance;
      } else {
        handleError('Invalid response format when updating exercise instance',
            Exception('Expected an exercise instance object in response'));
        throw Exception('Failed to update exercise instance');
      }
    } catch (e, stackTrace) {
      handleError('Failed to update exercise instance', e, stackTrace);
      throw Exception('Failed to update exercise instance');
    }
  }


  Future<bool> deleteExerciseInstance(int instanceId) async {
    try {
      _logger.d('Deleting exercise instance: $instanceId');

      final endpoint = ApiConfig.updateExerciseInstanceEndpoint(instanceId.toString());

      _logger.d('DELETE ExerciseInstance | endpoint=$endpoint');
      await apiClient.delete(
        endpoint,
        context: 'WorkoutService.deleteExerciseInstance',
      );
      _logger.d('Successfully deleted exercise instance: $instanceId');
      return true;
    } catch (e, stackTrace) {
      handleError('Failed to delete exercise instance', e, stackTrace);
      return false;
    }
  }

  Map<String, dynamic> _buildWorkoutPayload(Workout workout) {
    final payload = <String, dynamic>{
      'name': workout.name,
      if (workout.notes != null) 'notes': workout.notes,
      if (workout.status != null) 'status': workout.status,
      if (workout.startedAt != null) 'started_at': workout.startedAt!.toIso8601String(),
      if (workout.durationSeconds != null) 'duration_seconds': workout.durationSeconds,
      if (workout.rpeSession != null) 'rpe_session': workout.rpeSession,
      if (workout.location != null) 'location': workout.location,
      if (workout.readinessScore != null) 'readiness_score': workout.readinessScore,
      if (workout.appliedPlanId != null) 'applied_plan_id': workout.appliedPlanId,
      if (workout.planOrderIndex != null) 'plan_order_index': workout.planOrderIndex,
      if (workout.scheduledFor != null) 'scheduled_for': workout.scheduledFor!.toIso8601String(),
      if (workout.completedAt != null) 'completed_at': workout.completedAt!.toIso8601String(),
    };

    final typeStr = workout.workoutType.toString().split('.').last;
    if (typeStr != 'manual') {
      payload['workout_type'] = typeStr;
    }

    return payload;
  }
}
