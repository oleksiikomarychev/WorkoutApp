import 'dart:convert';
import 'package:http/http.dart' as http;
import 'package:workout_app/services/base_api_service.dart';
import 'package:workout_app/config/api_config.dart';

class SocialService extends BaseApiService {
  SocialService(super.apiClient);




  Future<List<Map<String, dynamic>>> getWorkoutFeed({
    int limit = 20,
    String scope = 'home',
    String? contextType,
    String? cursor,
    String? expand,
  }) async {
    final query = <String, dynamic>{
      'scope': scope,
      'limit': limit.toString(),
    };
    if (contextType != null && contextType.isNotEmpty) {
      query['context_type'] = contextType;
    }
    if (cursor != null && cursor.isNotEmpty) {
      query['cursor'] = cursor;
    }
    if (expand != null && expand.isNotEmpty) {
      query['expand'] = expand;
    }

    final response = await get<Map<String, dynamic>>(
      ApiConfig.socialPostsEndpoint,
      (json) => json,
      queryParams: query,
    );
    return (response['posts'] as List<dynamic>).cast<Map<String, dynamic>>();
  }




  Future<Map<String, dynamic>> createWorkoutPost({
    String? workoutId,
    String? ownerId,
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
      'attachments': attachments,
    };

    // Only add context_resource if workoutId is provided
    if (workoutId != null && workoutId.isNotEmpty) {
      body['context_resource'] = {
        'type': 'workout',
        'id': workoutId,
        if (ownerId != null && ownerId.isNotEmpty) 'owner_id': ownerId,
      };
    }

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


  Future<List<Map<String, dynamic>>> getUsersByIds(List<String> userIds) async {
    if (userIds.isEmpty) return [];

    final query = <String, dynamic>{
      'user_ids': userIds.join(','),
    };

    final response = await apiClient.get(
      ApiConfig.accountUsersEndpoint,
      queryParams: query,
    );

    // The API returns a list of user objects directly
    if (response is List) {
      return response.whereType<Map<String, dynamic>>().toList();
    }

    return [];
  }
}
