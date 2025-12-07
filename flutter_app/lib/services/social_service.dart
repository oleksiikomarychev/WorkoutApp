import 'package:workout_app/config/api_config.dart';
import 'package:workout_app/services/base_api_service.dart';


class SocialService extends BaseApiService {
  SocialService(super.apiClient);





  Future<List<Map<String, dynamic>>> getWorkoutFeed({
    int limit = 20,
    String scope = 'home',
    String contextType = 'workout',
    String? cursor,
  }) async {
    final query = <String, dynamic>{
      'scope': scope,
      'context_type': contextType,
      'limit': limit.toString(),
    };
    if (cursor != null && cursor.isNotEmpty) {
      query['cursor'] = cursor;
    }

    return getList<Map<String, dynamic>>(
      ApiConfig.socialPostsEndpoint,
      (json) => json,
      queryParams: query,
    );
  }




  Future<Map<String, dynamic>> createWorkoutPost({
    required String workoutId,
    required String ownerId,
    required String content,
    String scope = 'public',
    Map<String, dynamic>? stats,
  }) async {
    final attachments = <Map<String, dynamic>>[];
    if (stats != null && stats.isNotEmpty) {
      attachments.add({
        'type': 'workout_stats',
        ...stats,
      });
    }

    final body = <String, dynamic>{
      'content': content,
      'scope': scope,
      'context_resource': {
        'type': 'workout',
        'id': workoutId,
        'owner_id': ownerId,
      },
      'attachments': attachments,
    };

    return post<Map<String, dynamic>>(
      ApiConfig.socialPostsEndpoint,
      body,
      (json) => json,
    );
  }


  Future<Map<String, dynamic>> addComment({
    required String postId,
    required String content,
    String? replyToCommentId,
  }) async {
    final body = <String, dynamic>{
      'content': content,
    };
    if (replyToCommentId != null && replyToCommentId.isNotEmpty) {
      body['reply_to'] = replyToCommentId;
    }

    return post<Map<String, dynamic>>(
      ApiConfig.socialPostCommentsEndpoint(postId),
      body,
      (json) => json,
    );
  }


  Future<Map<String, dynamic>> toggleReaction({
    required String postId,
    required String reactionType,
  }) async {
    final body = <String, dynamic>{'type': reactionType};

    return post<Map<String, dynamic>>(
      ApiConfig.socialPostReactionsEndpoint(postId),
      body,
      (json) => json,
    );
  }
}
