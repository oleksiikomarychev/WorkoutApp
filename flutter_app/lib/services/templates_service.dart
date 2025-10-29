import 'dart:convert';
import 'package:workout_app/config/api_config.dart';
import 'package:workout_app/services/api_client.dart';
import 'package:workout_app/models/templates.dart';

class TemplatesService {
  final ApiClient apiClient;
  TemplatesService({required this.apiClient});

  Future<List<MesocycleTemplateResponse>> listTemplates() async {
    final res = await apiClient.get(ApiConfig.mesocycleTemplatesEndpoint, context: 'TemplatesService.list');
    if (res is List) {
      return res.whereType<Map<String, dynamic>>().map((e) => MesocycleTemplateResponse.fromJson(e)).toList();
    }
    if (res is Map && res['items'] is List) {
      return (res['items'] as List)
          .whereType<Map<String, dynamic>>()
          .map((e) => MesocycleTemplateResponse.fromJson(e))
          .toList();
    }
    return [];
  }

  Future<MesocycleTemplateResponse> getTemplate(int id) async {
    final res = await apiClient.get(ApiConfig.mesocycleTemplateByIdEndpoint(id.toString()), context: 'TemplatesService.get');
    return MesocycleTemplateResponse.fromJson((res as Map).cast<String, dynamic>());
  }
}
