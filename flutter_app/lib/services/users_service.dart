import '../config/api_config.dart';
import '../models/user_summary.dart';
import 'api_client.dart';
import 'base_api_service.dart';

class UsersService extends BaseApiService {
  UsersService(ApiClient client) : super(client);

  Future<List<UserSummary>> fetchAll({
    int limit = 100,
    int offset = 0,
    bool coach = false,
    List<String>? specializations,
    List<String>? languages,
    String? timezone,
    int? minRate,
    int? maxRate,
    String? sortBy,
  }) async {
    final queryParams = <String, dynamic>{
      'limit': '$limit',
      'offset': '$offset',
      if (coach) 'coach': 'true',
      if (specializations != null) 'specializations': specializations,
      if (languages != null) 'languages': languages,
      if (timezone != null) 'timezone': timezone,
      if (minRate != null) 'min_rate': minRate,
      if (maxRate != null) 'max_rate': maxRate,
      if (sortBy != null) 'sort_by': sortBy,
    };

    final response = await apiClient.get(
      ApiConfig.usersAllEndpoint,
      queryParams: queryParams,
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
