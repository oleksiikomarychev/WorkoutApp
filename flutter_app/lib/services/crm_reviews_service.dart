import 'package:workout_app/config/api_config.dart';
import 'package:workout_app/models/coach_review.dart';
import 'package:workout_app/services/api_client.dart';
import 'package:workout_app/services/base_api_service.dart';
import 'package:workout_app/services/logger_service.dart';

class CrmReviewsService extends BaseApiService {
  final LoggerService _logger = LoggerService('CrmReviewsService');

  CrmReviewsService(ApiClient apiClient) : super(apiClient);

  Future<CoachReview> createReview({
    required int linkId,
    required int rating,
    String? comment,
  }) async {
    try {
      final body = <String, dynamic>{
        'rating': rating,
        if (comment != null && comment.trim().isNotEmpty) 'comment': comment.trim(),
      };
      return await post<CoachReview>(
        ApiConfig.crmReviewsCreateEndpoint(linkId),
        body,
        CoachReview.fromJson,
      );
    } catch (e, st) {
      handleError('Failed to create review', e, st);
    }
  }

  Future<CoachReviewListResponse> getCoachReviews({
    required String coachId,
    int limit = 100,
    int offset = 0,
  }) async {
    try {
      final query = <String, dynamic>{
        'limit': limit.toString(),
        'offset': offset.toString(),
      };
      return await get(
        ApiConfig.crmReviewsCoachEndpoint(coachId),
        CoachReviewListResponse.fromJson,
        queryParams: query,
      );
    } catch (e, st) {
      handleError('Failed to fetch coach reviews', e, st);
    }
  }
}
