import 'dart:convert';
import 'package:flutter/foundation.dart';
import 'package:http/http.dart';
import '../config/api_config.dart';
import '../models/workout.dart';
import '../models/exercise_instance.dart';
import '../models/user_max.dart';
import 'api_client.dart';
import 'base_api_service.dart';
import 'logger_service.dart';
import 'exercise_service.dart';

class WorkoutService extends BaseApiService {
  final ApiClient _apiClient;
  final LoggerService _logger = LoggerService('WorkoutService');
  
  WorkoutService(this._apiClient) : super(_apiClient);

  /// Fetches all workouts from the API
  Future<List<Workout>> getWorkouts() async {
    try {
      final response = await _apiClient.get(
        ApiConfig.workoutsEndpoint,
        context: 'WorkoutService.getWorkouts',
      );
      
      _logger.d('Workout API response: ${jsonEncode(response)}');
      
      if (response is List) {
        final workouts = <Workout>[];
        
        for (var item in response.whereType<Map<String, dynamic>>()) {
          try {
            // Ensure exercise_instances is always a list in the JSON
            final exerciseInstances = (item['exercise_instances'] as List?)?.cast<Map<String, dynamic>>() ?? [];
            _logger.d('Parsing exercise instances: ${exerciseInstances.length}');
            
            final exerciseInstanceObjects = exerciseInstances
                .map((ei) => ExerciseInstance.fromJson(ei))
                .toList();
                
            final workout = Workout.fromJson(item).copyWith(
              exerciseInstances: exerciseInstanceObjects,
            );
            
            _logger.d('Parsed workout: ${workout.toString()}');
            workouts.add(workout);
          } catch (e, stackTrace) {
            _logger.e('Error parsing workout item: ${e.toString()}', e, stackTrace);
            _logger.e('Problematic item: ${jsonEncode(item)}');
            // Continue with next item
          }
        }
        
        return workouts;
      } else if (response is Map<String, dynamic>) {
        // Handle single workout response
        try {
          final exerciseInstances = (response['exercise_instances'] as List?)?.cast<Map<String, dynamic>>() ?? [];
          final workout = Workout.fromJson(response).copyWith(
            exerciseInstances: exerciseInstances
                .map((ei) => ExerciseInstance.fromJson(ei))
                .toList(),
          );
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

  /// Fetches workouts filtered by progression template ID
  Future<List<Workout>> getWorkoutsByProgressionId(int progressionId) async {
    try {
      _logger.d('Fetching workouts for progression ID: $progressionId');
      final endpoint = '${ApiConfig.workoutsEndpoint}?progression_template_id=$progressionId';
      final response = await _apiClient.get(
        endpoint,
        context: 'WorkoutService.getWorkoutsByProgressionId',
      );
      
      if (response is List) {
        return response
            .whereType<Map<String, dynamic>>()
            .map((json) {
              // Ensure exercise_instances is always a list in the JSON
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

  /// Fetches a workout by its ID
  Future<Workout> getWorkout(int id) async {
    try {
      final endpoint = ApiConfig.workoutByIdEndpoint(id.toString());
      final response = await _apiClient.get(
        endpoint,
        context: 'WorkoutService.getWorkout',
      );
      
      if (response is Map<String, dynamic>) {
        // Ensure exercise_instances is always a list in the response
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
  
  /// Fetches a workout with all its details including exercise instances
  Future<Workout> getWorkoutWithDetails(int id) async {
    try {
      _logger.d('Fetching workout with ID: $id');
      final response = await _apiClient.get(
        '${ApiConfig.workoutsEndpoint}/$id?include=exercise_instances.exercise_definition',
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

  /// Creates a new workout
  Future<Workout> createWorkout(Workout workout) async {
    try {
      _logger.d('Creating workout: ${workout.toJson()}');
      final response = await _apiClient.post(
        ApiConfig.createWorkoutEndpoint(),
        workout.toJson(),
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

  /// Updates an existing workout
  Future<Workout> updateWorkout(Workout workout) async {
    if (workout.id == null) {
      handleError('Cannot update workout without an ID', 
          Exception('Workout ID is required'));
      throw Exception('Cannot update workout without an ID');
    }
    
    try {
      _logger.d('Updating workout ${workout.id}: ${workout.toJson()}');
      final response = await _apiClient.put(
        '${ApiConfig.workoutsEndpoint}/${workout.id}',
        workout.toJson(),
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

  /// Deletes a workout by ID
  Future<void> deleteWorkout(int id) async {
    try {
      _logger.d('Deleting workout with ID: $id');
      await _apiClient.delete(
        '${ApiConfig.workoutsEndpoint}/$id',
        context: 'WorkoutService.deleteWorkout',
      );
    } catch (e, stackTrace) {
      _logger.e('Failed to delete workout', e, stackTrace);
      rethrow;
    }
  }
  
  // Methods for ExerciseInstance

  /// Creates a new exercise instance
  Future<ExerciseInstance> createExerciseInstance(ExerciseInstance instance) async {
    try {
      _logger.d('Creating exercise instance for workout: ${instance.workoutId}');
      // Backend route: POST /exercises/workouts/{workout_id}/instances
      final endpoint = ApiConfig.exerciseInstancesByWorkoutEndpoint(instance.workoutId.toString());
      final body = instance.toJson();
      
      _logger.d('Sending create exercise instance request to $endpoint');
      _logger.d('Request body: $body');
      
      final response = await _apiClient.post(
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
      // Backend route: PUT /exercises/instances/{instance_id}
      final endpoint = ApiConfig.updateExerciseInstanceEndpoint(instance.id!.toString());
      
      final payload = instance.toJson();
      _logger.d('PUT ExerciseInstance | endpoint=$endpoint | body=$payload');
      final response = await _apiClient.put(
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

  /// Deletes an exercise instance by ID
  Future<bool> deleteExerciseInstance(int instanceId) async {
    try {
      _logger.d('Deleting exercise instance: $instanceId');
      // Backend route: DELETE /exercises/instances/{instance_id}
      final endpoint = ApiConfig.updateExerciseInstanceEndpoint(instanceId.toString());
      
      _logger.d('DELETE ExerciseInstance | endpoint=$endpoint');
      await _apiClient.delete(
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

  /// Fetches user maxes for a specific exercise
  Future<List<UserMax>> getUserMaxesForExercise(int exerciseId) async {
    try {
      final endpoint = ApiConfig.userMaxesByExerciseEndpoint(exerciseId.toString());
      final response = await _apiClient.get(
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

  /// Deletes an exercise set by instance ID and set ID
  Future<void> deleteExerciseSet(int instanceId, int setId) async {
    try {
      _logger.d('Deleting set $setId from instance $instanceId');
      
      // Use the existing endpoint helper from ApiConfig
      final endpoint = ApiConfig.exerciseSetByIdEndpoint(
        instanceId.toString(),
        setId.toString(),
      );
      
      _logger.d('DELETE ExerciseSet | endpoint=$endpoint');
      
      try {
        final response = await _apiClient.delete(
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

  /// Updates an exercise set by instance ID and set ID
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

      final endpoint = ApiConfig.exerciseSetByIdEndpoint(
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

      final response = await _apiClient.put(
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
}
