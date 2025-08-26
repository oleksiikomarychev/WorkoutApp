import '../models/progression_template.dart';
import 'api_client.dart';

import '../config/api_config.dart';

class ProgressionService {
  final ApiClient _apiClient;
  
  
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
    
    final response = await _apiClient.get(ApiConfig.progressionTemplatesEndpoint, queryParams: params);
    return (response as List)
        .map((json) => ProgressionTemplate.fromJson(json))
        .toList();
  }

  // Get a specific template by ID
  Future<ProgressionTemplate> getTemplate(int id) async {
    final response = await _apiClient.get(ApiConfig.progressionTemplateByIdEndpoint(id.toString()));
    return ProgressionTemplate.fromJson(response);
  }

  // Create a new progression template
  Future<ProgressionTemplate> createTemplate(ProgressionTemplate template) async {
    final response = await _apiClient.post(
      ApiConfig.progressionTemplatesEndpoint,
      template.toJson(),
    );
    return ProgressionTemplate.fromJson(response);
  }

  // Update an existing template
  Future<ProgressionTemplate> updateTemplate(ProgressionTemplate template) async {
    final response = await _apiClient.put(
      ApiConfig.progressionTemplateByIdEndpoint(template.id.toString()),
      template.toJson(),
    );
    return ProgressionTemplate.fromJson(response);
  }

  // Delete a template
  Future<void> deleteTemplate(int id) async {
    await _apiClient.delete(ApiConfig.progressionTemplateByIdEndpoint(id.toString()));
  }
}
