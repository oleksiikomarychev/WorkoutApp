import '../config/api_config.dart';
import 'api_client.dart';
class HealthService {
  final ApiClient _apiClient;
  HealthService({ApiClient? apiClient})
    : _apiClient = apiClient ?? ApiClient.create();
  Future<Map<String, dynamic>> checkApiHealth() async {
    return await _apiClient.get(
      ApiConfig.healthEndpoint,
      context: 'health',
    );
  }
  Future<String> getApiVersion() async {
    final healthData = await checkApiHealth();
    return healthData['version'] ?? 'unknown';
  }
}
