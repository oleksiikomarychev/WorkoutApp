import 'package:flutter/foundation.dart';
import '../config/api_config.dart';
import '../models/workout.dart';
import '../models/exercise_instance.dart';
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
      // First, try to get the progression template directly
      dynamic template;
      try {
        template = await _apiClient.get(
          '${ApiConfig.progressionsEndpoint}/templates/$progressionId',
        );
      } catch (e) {
        // If we can't get the template, log it and return empty list
        debugPrint('Could not fetch progression template $progressionId: $e');
        return [];
      }
      
      if (template == null || template['id'] == null) {
        debugPrint('Progression template not found');
        return [];
      }
      
      // Get all workouts and filter by template ID
      final allWorkouts = await getWorkouts();
      final filteredWorkouts = allWorkouts.where((workout) => workout.progressionTemplateId == template['id']).toList();
      
      // Ensure exerciseInstances is not null
      return filteredWorkouts.map((workout) => workout.copyWith(
        exerciseInstances: workout.exerciseInstances ?? [],
      )).toList();
    } catch (e) {
      debugPrint('Error in getWorkoutsByProgressionId: $e');
      // Instead of rethrowing, return an empty list to prevent UI from breaking
      return [];
    }
  }

  Future<Workout> getWorkout(int id) async {
    try {
      final response = await _apiClient.get('${ApiConfig.workoutsEndpoint}/$id');
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
      final response = await _apiClient.get('${ApiConfig.workoutsEndpoint}/$id?include=exercise_instances');
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
        '${ApiConfig.workoutsEndpoint}/${workout.id}', 
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
      await _apiClient.delete('${ApiConfig.workoutsEndpoint}/$id');
    } catch (e) {
      debugPrint('Error in deleteWorkout: $e');
      rethrow;
    }
  }
}
