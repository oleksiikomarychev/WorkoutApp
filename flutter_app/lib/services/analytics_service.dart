import 'package:workout_app/config/api_config.dart';
import 'package:workout_app/services/api_client.dart';
import 'package:workout_app/services/base_api_service.dart';
import 'package:workout_app/services/logger_service.dart';
import 'package:workout_app/models/plan_analytics.dart';

class AnalyticsService extends BaseApiService {
  final ApiClient apiClient;
  final LoggerService _logger = LoggerService('AnalyticsService');

  AnalyticsService(this.apiClient) : super(apiClient);

  Future<Map<String, dynamic>> getProfileAggregates({int weeks = 48, int limit = 20, String? userId}) async {
    try {
      final endpoint = ApiConfig.profileAggregatesEndpoint;
      final response = await apiClient.get(
        endpoint,
        queryParams: <String, String>{
          'weeks': weeks.toString(),
          'limit': limit.toString(),
          if (userId != null && userId.isNotEmpty) 'user_id': userId,
        },
        context: 'AnalyticsService.getProfileAggregates',
      );
      if (response is Map<String, dynamic>) {
        return response;
      }
      _logger.w('Unexpected profile aggregates response: $response');
      return <String, dynamic>{
        'generated_at': DateTime.now().toIso8601String(),
        'weeks': weeks,
        'total_workouts': 0,
        'total_volume': 0.0,
        'active_days': 0,
        'max_day_volume': 0.0,
        'activity_map': <String, dynamic>{},
        'completed_sessions': <dynamic>[],
      };
    } catch (e, st) {
      handleError('Failed to fetch profile aggregates', e, st);
      rethrow;
    }
  }

  Future<Map<String, dynamic>> fetchMetrics({
    required int planId,
    required String metricX,
    required String metricY,
    DateTime? dateFrom,
    DateTime? dateTo,
  }) async {
    try {
      final endpoint = ApiConfig.workoutMetricsEndpoint;
      final queryParams = <String, String>{
        'plan_id': planId.toString(),
        'metric_x': metricX,
        'metric_y': metricY,
        if (dateFrom != null) 'date_from': dateFrom.toIso8601String(),
        if (dateTo != null) 'date_to': dateTo.toIso8601String(),
      };
      final response = await apiClient.get(
        endpoint,
        queryParams: queryParams,
        context: 'AnalyticsService.fetchMetrics',
      );
      if (response is Map<String, dynamic>) {
        return response;
      }
      _logger.w('Unexpected analytics response: $response');
      return {
        'items': <Map<String, dynamic>>[],
        'one_rm': <Map<String, dynamic>>[],
      };
    } catch (e, st) {
      handleError('Failed to fetch analytics metrics', e, st);
      rethrow;
    }
  }

  Future<PlanAnalyticsResponse?> getWorkoutHistoryAnalytics({
    int days = 365,
    List<String>? layers,
    bool includeMeta = true,
    int topLayersLimit = 50,
  }) async {
    try {
      final endpoint = ApiConfig.workoutsAnalyticsHistoryEndpoint;
      final query = <String, dynamic>{
        'days': days.toString(),
      };
      if (layers != null && layers.isNotEmpty) {
        query['layers'] = layers;
      }
      if (includeMeta) {
        query['include_meta'] = 'true';
        query['top_layers_limit'] = topLayersLimit.toString();
      }
      final response = await apiClient.get(
        endpoint,
        queryParams: query,
        context: 'AnalyticsService.getWorkoutHistoryAnalytics',
      );
      if (response is Map<String, dynamic>) {
        return PlanAnalyticsResponse.fromJson(response);
      }
      _logger.w('Unexpected workout history analytics response: $response');
      return null;
    } catch (e, st) {
      handleError('Failed to fetch workout history analytics', e, st);
      return null;
    }
  }
}
