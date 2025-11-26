import '../config/api_config.dart';
import '../models/user_summary.dart';
import 'api_client.dart';
import 'base_api_service.dart';

class UsersService extends BaseApiService {
  UsersService(ApiClient client) : super(client);

  Future<List<UserSummary>> fetchAll({int limit = 100, int offset = 0}) async {
    final response = await apiClient.get(
      ApiConfig.usersAllEndpoint,
      queryParams: {
        'limit': '$limit',
        'offset': '$offset',
      },
      context: 'UsersService.fetchAll',
    );
    if (response is List) {
      return response
          .whereType<Map<String, dynamic>>()
          .map(UserSummary.fromJson)
          .toList();
    }
    throw Exception('Unexpected response for users/all: $response');
  }
}
