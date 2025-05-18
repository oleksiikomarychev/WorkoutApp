import '../models/workout.dart';
import 'api_client.dart';
class WorkoutService {
  final ApiClient _apiClient;
  final String _endpoint = '/workouts';
  WorkoutService(this._apiClient);
  Future<List<Workout>> getWorkouts() async {
    final response = await _apiClient.get(_endpoint);
    return (response as List).map((json) => Workout.fromJson(json)).toList();
  }
  Future<Workout> getWorkout(int id) async {
    final response = await _apiClient.get('$_endpoint/$id');
    return Workout.fromJson(response);
  }
  Future<Workout> createWorkout(Workout workout) async {
    final response = await _apiClient.post(_endpoint, workout.toJson());
    return Workout.fromJson(response);
  }
  Future<Workout> updateWorkout(Workout workout) async {
    final response = await _apiClient.put('$_endpoint/${workout.id}', workout.toJson());
    return Workout.fromJson(response);
  }
  Future<void> deleteWorkout(int id) async {
    await _apiClient.delete('$_endpoint/$id');
  }
}
