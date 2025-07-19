import 'dart:convert';
import '../models/exercise_instance.dart';
import 'package:flutter/foundation.dart';
import '../models/exercise_list.dart';
import 'api_client.dart';
import '../config/api_config.dart';

class ExerciseService {
  final ApiClient _apiClient;
  static const String _endpoint = ApiConfig.exercisesEndpoint;

  ExerciseService(this._apiClient);

  // --- ExerciseList (Definition) Methods ---

  Future<List<ExerciseList>> getExerciseDefinitions() async {
    final response = await _apiClient.get(ApiConfig.exerciseListEndpoint);
    if (response is List) {
      return response.map((json) => ExerciseList.fromJson(json)).toList();
    } else {
      throw Exception('Unexpected response format: $response');
    }
  }

  Future<ExerciseList> createExerciseDefinition(ExerciseList exercise) async {
    try {
      final response = await _apiClient.post(
        ApiConfig.exerciseListCreateEndpoint,
        exercise.toJson(),
      );
      return ExerciseList.fromJson(response);
    } catch (e) {
      debugPrint('Error in createExerciseDefinition: $e');
      rethrow;
    }
  }
  
  Future<void> deleteExerciseDefinition(int id) async {
    await _apiClient.delete('${ApiConfig.exerciseListEndpoint}/$id');
  }
  
  Future<ExerciseList> updateExerciseDefinition(int id, ExerciseList exercise) async {
    final response = await _apiClient.put('${ApiConfig.exerciseListEndpoint}/$id', exercise.toJson());
    return ExerciseList.fromJson(response);
  }
}
