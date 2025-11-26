import 'package:workout_app/config/api_config.dart';
import 'package:workout_app/models/crm_analytics.dart';
import 'package:workout_app/services/api_client.dart';
import 'package:workout_app/services/base_api_service.dart';
import 'package:workout_app/services/logger_service.dart';

class CrmAnalyticsService extends BaseApiService {
  final LoggerService _logger = LoggerService('CrmAnalyticsService');

  CrmAnalyticsService(ApiClient apiClient) : super(apiClient);

  Future<CoachAthletesAnalyticsModel> getMyAthletesAnalytics({
    int weeks = 12,
    int inactiveAfterDays = 14,
    int limit = 100,
    int offset = 0,
  }) async {
    try {
      final query = <String, dynamic>{
        'weeks': weeks.toString(),
        'inactive_after_days': inactiveAfterDays.toString(),
        'limit': limit.toString(),
        'offset': offset.toString(),
      };
      final response = await apiClient.get(
        ApiConfig.crmAnalyticsMyAthletesEndpoint,
        queryParams: query,
        context: 'CrmAnalyticsService.getMyAthletesAnalytics',
      );
      if (response is Map<String, dynamic>) {
        return CoachAthletesAnalyticsModel.fromJson(response);
      }
      throw Exception('Unexpected response format for coach athletes analytics');
    } catch (e, st) {
      handleError('Failed to fetch coach athletes analytics', e, st);
    }
  }

  Future<CoachSummaryAnalyticsModel> getMySummaryAnalytics({
    int weeks = 12,
    int inactiveAfterDays = 14,
    int limit = 100,
    int offset = 0,
  }) async {
    try {
      final query = <String, dynamic>{
        'weeks': weeks.toString(),
        'inactive_after_days': inactiveAfterDays.toString(),
        'limit': limit.toString(),
        'offset': offset.toString(),
      };
      final response = await apiClient.get(
        ApiConfig.crmAnalyticsMySummaryEndpoint,
        queryParams: query,
        context: 'CrmAnalyticsService.getMySummaryAnalytics',
      );
      if (response is Map<String, dynamic>) {
        return CoachSummaryAnalyticsModel.fromJson(response);
      }
      throw Exception('Unexpected response format for coach summary analytics');
    } catch (e, st) {
      handleError('Failed to fetch coach summary analytics', e, st);
    }
  }

  Future<AthleteDetailedAnalyticsModel> getAthleteAnalytics({
    required String athleteId,
    int weeks = 12,
    int inactiveAfterDays = 14,
  }) async {
    try {
      final query = <String, dynamic>{
        'weeks': weeks.toString(),
        'inactive_after_days': inactiveAfterDays.toString(),
      };
      final response = await apiClient.get(
        ApiConfig.crmAnalyticsAthleteEndpoint(athleteId),
        queryParams: query,
        context: 'CrmAnalyticsService.getAthleteAnalytics',
      );
      if (response is Map<String, dynamic>) {
        return AthleteDetailedAnalyticsModel.fromJson(response);
      }
      throw Exception('Unexpected response format for athlete detailed analytics');
    } catch (e, st) {
      handleError('Failed to fetch athlete detailed analytics', e, st);
    }
  }
}
