import 'package:workout_app/config/api_config.dart';
import 'package:workout_app/services/base_api_service.dart';


class MessagingService extends BaseApiService {
  MessagingService(super.apiClient);





  Future<List<Map<String, dynamic>>> getChannelMessages({
    required String channelId,
    int limit = 50,
    DateTime? before,
  }) async {
    final query = <String, dynamic>{
      'limit': limit.toString(),
      'sort': 'desc',
    };
    if (before != null) {
      query['before'] = before.toUtc().toIso8601String();
    }

    return getList<Map<String, dynamic>>(
      ApiConfig.messagingChannelMessagesEndpoint(channelId),
      (json) => json,
      queryParams: query,
    );
  }




  Future<Map<String, dynamic>> sendTextMessage({
    required String channelId,
    required String content,
    String? workoutId,
  }) async {
    final body = <String, dynamic>{
      'content': content,
      'kind': 'text',
    };
    if (workoutId != null && workoutId.isNotEmpty) {
      body['context_resource'] = {
        'type': 'workout',
        'id': workoutId,
      };
    }

    return post<Map<String, dynamic>>(
      ApiConfig.messagingChannelMessagesEndpoint(channelId),
      body,
      (json) => json,
    );
  }
}
