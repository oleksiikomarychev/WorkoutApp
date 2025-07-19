import 'package:flutter/foundation.dart';
import '../config/api_config.dart';
import '../models/workout.dart';
import '../models/exercise_instance.dart';
import '../models/user_max.dart';
import 'api_client.dart';

class WorkoutService {
  final ApiClient _apiClient;
  
  WorkoutService(this._apiClient);

  Future<List<Workout>> getWorkouts() async {
    try {
      final response = await _apiClient.get(ApiConfig.workoutsEndpoint);
      if (response is List) {
        return response.map<Workout>((json) {
          // Ensure exercise_instances is always a list in the JSON
          if (json['exercise_instances'] == null) {
            json['exercise_instances'] = [];
          }
          return Workout.fromJson(json);
        }).toList();
      } else {
        debugPrint('Unexpected response format: $response');
        return [];
      }
    } catch (e) {
      debugPrint('Error in getWorkouts: $e');
      rethrow;
    }
  }

  Future<List<Workout>> getWorkoutsByProgressionId(int progressionId) async {
    try {
      final allWorkouts = await getWorkouts();
      final filteredWorkouts = allWorkouts.where((workout) => workout.progressionTemplateId == progressionId).toList();
      return filteredWorkouts.map((workout) => workout.copyWith(
        exerciseInstances: workout.exerciseInstances ?? [],
      )).toList();
    } catch (e) {
      debugPrint('Error in getWorkoutsByProgressionId: $e');
      return [];
    }
  }

  Future<Workout> getWorkout(int id) async {
    try {
      final response = await _apiClient.get(ApiConfig.workoutByIdEndpoint.replaceAll('{workout_id}', id.toString()));
      // Ensure exercise_instances is always a list in the response
      if (response != null && response is Map<String, dynamic>) {
        response['exercise_instances'] = response['exercise_instances'] ?? [];
      }
      return Workout.fromJson(response);
    } catch (e) {
      debugPrint('Error in getWorkout: $e');
      rethrow;
    }
  }
  
  Future<Workout> getWorkoutWithDetails(int id) async {
    try {
      final response = await _apiClient.get('${ApiConfig.workoutByIdEndpoint.replaceAll('{workout_id}', id.toString())}?include=exercise_instances');
      // Ensure exercise_instances is always a list in the response
      if (response != null && response is Map<String, dynamic>) {
        response['exercise_instances'] = response['exercise_instances'] ?? [];
      }
      return Workout.fromJson(response);
    } catch (e) {
      debugPrint('Error in getWorkoutWithDetails: $e');
      rethrow;
    }
  }

  Future<Workout> createWorkout(Workout workout) async {
    try {
      // Create the workout first
      final workoutData = workout.toJson()..remove('exercise_instances');
      final response = await _apiClient.post(
        ApiConfig.workoutsEndpoint, 
        workoutData,
      );
      
      final createdWorkout = Workout.fromJson(response);
      
      // Create exercise instances if any
      if (workout.exerciseInstances.isNotEmpty) {
        // In a real app, you would need to create each exercise instance here
        // This would require a method to create exercise instances
        debugPrint('Workout created with ${workout.exerciseInstances.length} exercise instances');
      }
      
      return createdWorkout;
    } catch (e) {
      debugPrint('Error in createWorkout: $e');
      rethrow;
    }
  }

  Future<Workout> updateWorkout(Workout workout) async {
    try {
      if (workout.id == null) {
        throw Exception('Cannot update workout without an ID');
      }
      final response = await _apiClient.put(
        ApiConfig.workoutByIdEndpoint.replaceAll('{workout_id}', workout.id.toString()), 
        workout.toJson(),
      );
      return Workout.fromJson(response);
    } catch (e) {
      debugPrint('Error in updateWorkout: $e');
      rethrow;
    }
  }

  Future<void> deleteWorkout(int id) async {
    try {
      await _apiClient.delete(ApiConfig.workoutByIdEndpoint.replaceAll('{workout_id}', id.toString()));
    } catch (e) {
      debugPrint('Error in deleteWorkout: $e');
      rethrow;
    }
  }

  // Methods for ExerciseInstance

  Future<ExerciseInstance> createExerciseInstance({
    required int workoutId,
    required int exerciseListId,
    required int volume,
    required int weight,
    required int intensity,
    required int effort,
  }) async {
    try {
      final url = ApiConfig.exerciseInstancesEndpoint.replaceAll('{workout_id}', workoutId.toString());
      final response = await _apiClient.post(
        url,
        {
          'workout_id': workoutId,
          'exercise_list_id': exerciseListId,
          'volume': volume,
          'weight': weight,
          'intensity': intensity,
          'effort': effort,
        },
      );
      return ExerciseInstance.fromJson(response);
    } catch (e) {
      debugPrint('Error in createExerciseInstance: $e');
      rethrow;
    }
  }

  Future<void> updateExerciseInstance(ExerciseInstance instance) async {
    try {
      final endpoint = ApiConfig.exerciseInstancesEndpoint
          .replaceAll('{workout_id}', instance.workoutId.toString());
      
      await _apiClient.put(
        endpoint,
        instance.toJson(),
      );
    } catch (e) {
      debugPrint('Error in updateExerciseInstance: $e');
      rethrow;
    }
  }

  Future<void> deleteExerciseInstance(int instanceId) async {
    try {
      await _apiClient.delete('${ApiConfig.exerciseInstancesEndpoint}${instanceId}/');
    } catch (e) {
      debugPrint('Error deleting exercise instance: $e');
      rethrow;
    }
  }

  Future<List<UserMax>> getUserMaxesForExercise(int exerciseId) async {
    try {
      final endpoint = ApiConfig.userMaxesByExerciseEndpoint
          .replaceAll('{exercise_id}', exerciseId.toString());
      final response = await _apiClient.get(endpoint);
      return (response as List).map((data) => UserMax.fromJson(data)).toList();
    } catch (e) {
      debugPrint('Error fetching user maxes: $e');
      // Return an empty list or rethrow, depending on how you want to handle errors
      return [];
    }
  }
}
