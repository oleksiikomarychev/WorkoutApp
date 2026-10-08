import '../config/api_config.dart';
import 'api_client.dart';
import 'base_api_service.dart';

class AccountService extends BaseApiService {
  final ApiClient apiClient;

  AccountService(this.apiClient) : super(apiClient);

  Future<Map<String, dynamic>> purgeAccount() async {
    try {
      final response = await apiClient.post(
        ApiConfig.accountPurgeEndpoint,
        const <String, dynamic>{},
        context: 'AccountService.purgeAccount',
      );
      if (response is Map<String, dynamic>) {
        return Map<String, dynamic>.from(response);
      }
      return <String, dynamic>{'ok': true};
    } catch (e, st) {
      handleError('Failed to purge account', e, st);
      rethrow;
    }
  }
}
