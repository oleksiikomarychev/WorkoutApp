import '../models/progression.dart';
import 'api_client.dart';

class ProgressionService {
  final ApiClient _apiClient;
  static const String _endpoint = '/api/v1/progressions/templates';
  
  ProgressionService(this._apiClient);

  // Get all progression templates
  Future<List<ProgressionTemplate>> getTemplates({
    int? userMaxId,
    int skip = 0,
    int limit = 100,
  }) async {
    final params = {
      'skip': skip.toString(),
      'limit': limit.toString(),
      if (userMaxId != null) 'user_max_id': userMaxId.toString(),
    };
    
    final response = await _apiClient.get(_endpoint, queryParams: params);
    return (response as List)
        .map((json) => ProgressionTemplate.fromJson(json))
        .toList();
  }

  // Get a specific template by ID
  Future<ProgressionTemplate> getTemplate(int id) async {
    final response = await _apiClient.get('$_endpoint/$id');
    return ProgressionTemplate.fromJson(response);
  }

  // Create a new progression template
  Future<ProgressionTemplate> createTemplate(ProgressionTemplate template) async {
    final response = await _apiClient.post(
      _endpoint,
      template.toJson(),
    );
    return ProgressionTemplate.fromJson(response);
  }

  // Update an existing template
  Future<ProgressionTemplate> updateTemplate(ProgressionTemplate template) async {
    final response = await _apiClient.put(
      '$_endpoint/${template.id}',
      template.toJson(),
    );
    return ProgressionTemplate.fromJson(response);
  }

  // Delete a template
  Future<void> deleteTemplate(int id) async {
    await _apiClient.delete('$_endpoint/$id');
  }
}
