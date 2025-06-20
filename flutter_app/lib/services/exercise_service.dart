import '../models/exercise.dart';
import '../models/exercise_instance.dart';
import '../models/exercise_list.dart';
import 'api_client.dart';
import '../config/api_config.dart';
class ExerciseService {
  final ApiClient _apiClient;
  static const String _endpoint = ApiConfig.exercisesEndpoint;
  ExerciseService(this._apiClient);
  Future<List<Exercise>> getExercises() async {
    try {
      final response = await _apiClient.get(ApiConfig.exerciseListEndpoint);
      if (response is List) {
        return response.map((json) => Exercise.fromJson(json)).toList();
      } else if (response is Map<String, dynamic>) {
        // Handle case where the API returns a single item as a map
        return [Exercise.fromJson(response)];
      } else {
        throw Exception('Unexpected response format: $response');
      }
    } catch (e) {
      print('Error in getExercises: $e');
      rethrow;
    }
  }

  Future<List<Exercise>> getExercisesByWorkoutId(int workoutId) async {
    final response = await _apiClient.get('$_endpoint/workouts/$workoutId');
    if (response is List) {
      return response.map((json) => Exercise.fromJson(json)).toList();
    } else if (response is Map<String, dynamic>) {
      return [Exercise.fromJson(response)];
    } else {
      throw Exception('Unexpected response format: $response');
    }
  }
  
  Future<ExerciseInstance> getExerciseInstance(int id) async {
    final response = await _apiClient.get('$_endpoint/instances/$id');
    return ExerciseInstance.fromJson(response);
  }
  Future<Exercise> getExercise(int id) async {
    final response = await _apiClient.get('$_endpoint/$id');
    return Exercise.fromJson(response);
  }
  Future<Exercise> createExercise(Exercise exercise) async {
    final data = exercise.toJson();
    final response = await _apiClient.post(
      _endpoint,
      data,
    );
    return Exercise.fromJson(response);
  }
  
  Future<ExerciseInstance> createExerciseInstance(ExerciseInstance instance) async {
    final response = await _apiClient.post(
      '${_endpoint}/instances',
      instance.toJson(),
    );
    return ExerciseInstance.fromJson(response);
  }
  
  Future<ExerciseInstance> updateExerciseInstance(ExerciseInstance instance) async {
    final response = await _apiClient.put(
      '${_endpoint}/instances/${instance.id}',
      instance.toJson(),
    );
    return ExerciseInstance.fromJson(response);
  }
  
  Future<void> deleteExerciseInstance(int id) async {
    await _apiClient.delete('${_endpoint}/instances/$id');
  }
  
  Future<List<ExerciseInstance>> getExerciseInstancesByWorkoutId(int workoutId) async {
    final response = await _apiClient.get('$_endpoint/instances/workout/$workoutId');
    if (response is List) {
      return response.map((json) => ExerciseInstance.fromJson(json)).toList();
    } else if (response is Map<String, dynamic>) {
      return [ExerciseInstance.fromJson(response)];
    } else {
      throw Exception('Unexpected response format: $response');
    }
  }
  Future<Exercise> updateExercise(Exercise exercise) async {
    final response = await _apiClient.put('$_endpoint/${exercise.id}', exercise.toJson());
    return Exercise.fromJson(response);
  }
  Future<void> deleteExercise(int id) async {
    await _apiClient.delete('$_endpoint/$id');
  }
  Future<List<ExerciseList>> getExerciseList() async {
    final response = await _apiClient.get(ApiConfig.exerciseListEndpoint);
    if (response is List) {
      return response.map((json) => ExerciseList.fromJson(json)).toList();
    } else if (response is Map<String, dynamic>) {
      // Handle case where the API returns a single item as a map
      return [ExerciseList.fromJson(response)];
    } else {
      throw Exception('Unexpected response format: $response');
    }
  }
  Future<ExerciseList> createExerciseList(ExerciseList exercise) async {
    final response = await _apiClient.post('$_endpoint', exercise.toJson());
    if (response is Map<String, dynamic>) {
      return ExerciseList.fromJson(response);
    } else if (response is List) {
      // Handle case where the API returns a list
      return ExerciseList.fromJson(response.first);
    } else {
      throw Exception('Unexpected response format: $response');
    }
  }
}
