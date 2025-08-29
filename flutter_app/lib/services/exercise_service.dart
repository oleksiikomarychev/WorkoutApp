import 'dart:convert';
import 'package:flutter/foundation.dart';
import 'package:http/http.dart' as http;
import '../models/exercise_instance.dart';
import '../models/exercise_definition.dart';
import 'api_client.dart';
import 'base_api_service.dart';
import 'logger_service.dart';
import 'package:workout_app/config/api_config.dart';
import 'package:workout_app/models/muscle_info.dart';

class ExerciseService extends BaseApiService {
  final ApiClient _apiClient;
  final LoggerService _logger = LoggerService('ExerciseService');

  ExerciseService(this._apiClient) : super(_apiClient);

  // --- ExerciseDefinition Methods ---

  /// Fetches all exercise definitions from the API
  Future<List<ExerciseDefinition>> getExerciseDefinitions() async {
    try {
      final response = await _apiClient.get(
        ApiConfig.exerciseDefinitionsEndpoint,
        context: 'ExerciseService.getExerciseDefinitions',
      );
      if (response is List) {
        return response
            .whereType<Map<String, dynamic>>()
            .map((json) => ExerciseDefinition.fromJson(json))
            .toList();
      } else {
        handleError(
          'Invalid response format for exercise definitions',
          Exception('Expected a list of exercise definitions'),
        );
        return [];
      }
    } catch (e, stackTrace) {
      handleError('Failed to get exercise definitions', e, stackTrace);
      rethrow;
    }
  }

  /// Fetches muscles enum with labels and groups
  Future<List<MuscleInfo>> getMuscles() async {
    try {
      final response = await _apiClient.get(
        ApiConfig.musclesEndpoint,
        context: 'ExerciseService.getMuscles',
      );
      if (response is List) {
        return response
            .whereType<Map<String, dynamic>>()
            .map((e) => MuscleInfo.fromJson(e))
            .toList();
      }
      handleError('Invalid response format for muscles', Exception('Expected a list'));
      return [];
    } catch (e, stackTrace) {
      handleError('Failed to get muscles', e, stackTrace);
      rethrow;
    }
  }

  /// Fetches multiple exercise definitions by their IDs
  Future<List<ExerciseDefinition>> getExercisesByIds(List<int> ids) async {
    try {
      if (ids.isEmpty) return [];
      
      final endpoint = '${ApiConfig.exerciseDefinitionsEndpoint}?ids=${ids.join(',')}';
      _logger.d('Fetching exercise definitions | endpoint=$endpoint');
      
      final response = await _apiClient.get(
        endpoint,
        context: 'ExerciseService.getExercisesByIds',
      );
      
      if (response is List) {
        return response
            .whereType<Map<String, dynamic>>()
            .map((json) => ExerciseDefinition.fromJson(json))
            .toList();
      } else {
        handleError('Invalid response format for exercise definitions',
            Exception('Expected a list of exercise definitions'));
        return [];
      }
    } catch (e, stackTrace) {
      handleError('Failed to get exercise definitions by IDs', e, stackTrace);
      rethrow;
    }
  }

  /// Fetches a single exercise definition by ID
  Future<ExerciseDefinition> getExerciseDefinition(int id) async {
    try {
      final endpoint = ApiConfig.exerciseDefinitionByIdEndpoint(id.toString());
      _logger.d('Fetching exercise definition | endpoint=$endpoint');
      final response = await _apiClient.get(
        endpoint,
        context: 'ExerciseService.getExerciseDefinition',
      );
      
      if (response is Map<String, dynamic>) {
        return ExerciseDefinition.fromJson(response);
      } else {
        handleError('Invalid response format for exercise definition',
            Exception('Expected an exercise definition object'));
        throw Exception('Failed to get exercise definition');
      }
    } catch (e, stackTrace) {
      handleError('Failed to get exercise definition', e, stackTrace);
      rethrow;
    }
  }

  /// Creates a new exercise definition
  Future<ExerciseDefinition> createExerciseDefinition(ExerciseDefinition exercise) async {
    try {
      final endpoint = ApiConfig.exerciseDefinitionsEndpoint;
      final body = exercise.toJson();
      _logger.d('Creating exercise definition | endpoint=$endpoint | body=$body');
      final response = await _apiClient.post(
        endpoint,
        body,
        context: 'ExerciseService.createExerciseDefinition',
      );
      
      if (response is Map<String, dynamic>) {
        return ExerciseDefinition.fromJson(response);
      } else {
        handleError('Invalid response format when creating exercise definition',
            Exception('Expected an exercise definition object'));
        throw Exception('Failed to create exercise definition');
      }
    } catch (e, stackTrace) {
      handleError('Failed to create exercise definition', e, stackTrace);
      rethrow;
    }
  }
  
  /// Updates an existing exercise definition
  Future<ExerciseDefinition> updateExerciseDefinition(ExerciseDefinition exercise) async {
    try {
      if (exercise.id == null) {
        throw Exception('Cannot update exercise definition without an ID');
      }
      
      final endpoint = ApiConfig.exerciseDefinitionByIdEndpoint(exercise.id.toString());
      final body = exercise.toJson();
      _logger.d('Updating exercise definition | endpoint=$endpoint | body=$body');
      final response = await _apiClient.put(
        endpoint,
        body,
        context: 'ExerciseService.updateExerciseDefinition',
      );
      
      if (response is Map<String, dynamic>) {
        return ExerciseDefinition.fromJson(response);
      } else {
        handleError('Invalid response format when updating exercise definition',
            Exception('Expected an exercise definition object'));
        throw Exception('Failed to update exercise definition');
      }
    } catch (e, stackTrace) {
      handleError('Failed to update exercise definition', e, stackTrace);
      rethrow;
    }
  }

  /// Deletes an exercise definition by ID
  Future<bool> deleteExerciseDefinition(int id) async {
    try {
      final endpoint = ApiConfig.exerciseDefinitionByIdEndpoint(id.toString());
      _logger.d('Deleting exercise definition | endpoint=$endpoint');
      await _apiClient.delete(
        endpoint,
        context: 'ExerciseService.deleteExerciseDefinition',
      );
      return true;
    } catch (e, stackTrace) {
      handleError('Failed to delete exercise definition', e, stackTrace);
      return false;
    }
  }

  // --- ExerciseInstance Methods ---

  /// Fetches an exercise instance by ID
  Future<ExerciseInstance> getExerciseInstance(int id) async {
    try {
      final endpoint = ApiConfig.exerciseInstanceByIdEndpoint(id.toString());
      _logger.d('Fetching exercise instance | endpoint=$endpoint');
      final response = await _apiClient.get(
        endpoint,
        context: 'ExerciseService.getExerciseInstance',
      );
      
      if (response is Map<String, dynamic>) {
        return ExerciseInstance.fromJson(response);
      } else {
        handleError('Invalid response format for exercise instance',
            Exception('Expected an exercise instance object'));
        throw Exception('Failed to get exercise instance');
      }
    } catch (e, stackTrace) {
      handleError('Failed to get exercise instance', e, stackTrace);
      rethrow;
    }
  }

  /// Creates a new exercise instance in a workout
  Future<ExerciseInstance> createExerciseInstance({
    required int workoutId,
    required int exerciseDefinitionId,
    required List<Map<String, int>> sets,
    int? userMaxId,
  }) async {
    try {
      final endpoint = ApiConfig.exerciseInstancesByWorkoutEndpoint(workoutId.toString());
      final body = {
        'exercise_list_id': exerciseDefinitionId,
        'sets': sets,
        if (userMaxId != null) 'user_max_id': userMaxId,
      };
      _logger.d('POST ExerciseInstance | endpoint=$endpoint | body=$body');
      final response = await _apiClient.post(
        endpoint,
        body,
        context: 'ExerciseService.createExerciseInstance',
      );
      
      if (response is Map<String, dynamic>) {
        return ExerciseInstance.fromJson(response);
      } else {
        handleError('Invalid response format when creating exercise instance',
            Exception('Expected an exercise instance object'));
        throw Exception('Failed to create exercise instance');
      }
    } catch (e, stackTrace) {
      handleError('Failed to create exercise instance', e, stackTrace);
      rethrow;
    }
  }

  /// Updates an existing exercise instance
  Future<ExerciseInstance> updateExerciseInstance(ExerciseInstance instance) async {
    try {
      if (instance.id == null) {
        throw Exception('Cannot update exercise instance without an ID');
      }
      
      final endpoint = ApiConfig.exerciseInstanceByIdEndpoint(instance.id.toString());
      final payload = instance.toJson();
      _logger.d('PUT ExerciseInstance | endpoint=$endpoint | body=$payload');
      final response = await _apiClient.put(
        endpoint,
        payload,
        context: 'ExerciseService.updateExerciseInstance',
      );
      
      if (response is Map<String, dynamic>) {
        return ExerciseInstance.fromJson(response);
      } else {
        handleError('Invalid response format when updating exercise instance',
            Exception('Expected an exercise instance object'));
        throw Exception('Failed to update exercise instance');
      }
    } catch (e, stackTrace) {
      handleError('Failed to update exercise instance', e, stackTrace);
      rethrow;
    }
  }

  /// Deletes an exercise instance by ID
  Future<bool> deleteExerciseInstance(int id) async {
    try {
      final endpoint = ApiConfig.exerciseInstanceByIdEndpoint(id.toString());
      _logger.d('DELETE ExerciseInstance | endpoint=$endpoint');
      await _apiClient.delete(
        endpoint,
        context: 'ExerciseService.deleteExerciseInstance',
      );
      return true;
    } catch (e, stackTrace) {
      handleError('Failed to delete exercise instance', e, stackTrace);
      return false;
    }
  }
}
