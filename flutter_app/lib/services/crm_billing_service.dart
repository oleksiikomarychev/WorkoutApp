import 'package:workout_app/config/api_config.dart';
import 'package:workout_app/services/api_client.dart';
import 'package:workout_app/services/base_api_service.dart';

class CrmBillingService extends BaseApiService {
  CrmBillingService(ApiClient apiClient) : super(apiClient);

  Future<Map<String, dynamic>> getSubscriptionStatus(int linkId) async {
    final endpoint = ApiConfig.crmBillingSubscriptionEndpoint(linkId);
    final response = await apiClient.get(
      endpoint,
      context: 'CrmBillingService.getSubscriptionStatus',
    );
    if (response is Map<String, dynamic>) {
      return Map<String, dynamic>.from(response);
    }
    throw Exception('Unexpected subscription status response: $response');
  }

  Future<Map<String, dynamic>> createCheckoutSession(int linkId) async {
    final endpoint = ApiConfig.crmBillingCheckoutSessionEndpoint(linkId);
    final response = await apiClient.post(
      endpoint,
      const <String, dynamic>{},
      context: 'CrmBillingService.createCheckoutSession',
    );
    if (response is Map<String, dynamic>) {
      return Map<String, dynamic>.from(response);
    }
    throw Exception('Unexpected checkout session response: $response');
  }
}
