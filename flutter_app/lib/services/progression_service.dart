import '../models/progression.dart';
import 'api_client.dart';
class ProgressionService {
  final ApiClient _apiClient;
  final String _endpoint = '/progressions';
  ProgressionService(this._apiClient);
  Future<List<Progression>> getProgressions() async {
    final response = await _apiClient.get(_endpoint);
    return (response as List).map((json) => Progression.fromJson(json)).toList();
  }
  Future<Progression> getProgression(int id) async {
    final response = await _apiClient.get('$_endpoint/$id');
    return Progression.fromJson(response);
  }
  Future<Progression> createProgression(Progression progression) async {
    final response = await _apiClient.post(_endpoint, progression.toJson());
    return Progression.fromJson(response);
  }
  Future<Progression> updateProgression(Progression progression) async {
    final response = await _apiClient.put('$_endpoint/${progression.id}', progression.toJson());
    return Progression.fromJson(response);
  }
  Future<void> deleteProgression(int id) async {
    await _apiClient.delete('$_endpoint/$id');
  }
  Future<List<dynamic>> getProgressionTemplates() async {
    final response = await _apiClient.get('$_endpoint/template');
    return response as List;
  }
  Future<dynamic> getProgressionTemplate(int id) async {
    final response = await _apiClient.get('$_endpoint/template/$id');
    return response;
  }
  Future<dynamic> createProgressionTemplate(Map<String, dynamic> template) async {
    final response = await _apiClient.post('$_endpoint/template', template);
    return response;
  }
}
