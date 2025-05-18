import '../models/exercise.dart';
import '../models/exercise_list.dart';
import 'api_client.dart';
class ExerciseService {
  final ApiClient _apiClient;
  final String _endpoint = '/exercises';
  ExerciseService(this._apiClient);
  Future<List<Exercise>> getExercises() async {
    final response = await _apiClient.get(_endpoint);
    return (response as List).map((json) => Exercise.fromJson(json)).toList();
  }
  Future<Exercise> getExercise(int id) async {
    final response = await _apiClient.get('$_endpoint/$id');
    return Exercise.fromJson(response);
  }
  Future<Exercise> createExercise(Exercise exercise) async {
    final response = await _apiClient.post(_endpoint, exercise.toJson());
    return Exercise.fromJson(response);
  }
  Future<Exercise> updateExercise(Exercise exercise) async {
    final response = await _apiClient.put('$_endpoint/${exercise.id}', exercise.toJson());
    return Exercise.fromJson(response);
  }
  Future<void> deleteExercise(int id) async {
    await _apiClient.delete('$_endpoint/$id');
  }
  Future<List<ExerciseList>> getExerciseList() async {
    final response = await _apiClient.get('$_endpoint/list');
    return (response as List).map((json) => ExerciseList.fromJson(json)).toList();
  }
  Future<ExerciseList> createExerciseList(ExerciseList exercise) async {
    final response = await _apiClient.post('$_endpoint/list', exercise.toJson());
    return ExerciseList.fromJson(response);
  }
}
