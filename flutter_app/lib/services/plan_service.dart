import 'dart:convert';
import '../config/api_config.dart';
import '../models/applied_calendar_plan.dart';
import '../models/workout.dart';
import '../models/plan_analytics.dart';
import 'api_client.dart';
import 'base_api_service.dart';
import 'logger_service.dart';

class PlanService extends BaseApiService {
  final ApiClient apiClient;
  final LoggerService _logger = LoggerService('PlanService');

  PlanService({required this.apiClient}) : super(apiClient);

  Future<AppliedCalendarPlan?> getActivePlan() async {
    try {
      final endpoint = ApiConfig.getActivePlanEndpoint;
      _logger.d('GET Active Plan: $endpoint');
      final response = await apiClient.get(
        endpoint,
        context: 'PlanService.getActivePlan',
      );
      if (response is Map<String, dynamic>) {
        _logger.d('Active plan fetched successfully');
        return AppliedCalendarPlan.fromJson(response);
      }
      _logger.d('Active plan not found (null or invalid format)');
      return null;
    } catch (e, stackTrace) {
      handleError('Failed to get active plan', e, stackTrace);
      return null;
    }
  }

  Future<bool> applyPlan(int planId, List<int> userMaxIds) async {
    try {
      if (userMaxIds.isEmpty) {
        throw Exception('At least one user_max_id is required');
      }
      final endpoint = ApiConfig.applyPlanEndpoint(planId.toString());
      final response = await apiClient.post(
        endpoint,
        {},
        queryParams: {'user_max_ids': userMaxIds.join(',')},
        context: 'PlanService.applyPlan',
      );
      return response != null;
    } catch (e, stackTrace) {
      handleError('Failed to apply plan', e, stackTrace);
      return false;
    }
  }

  Future<Workout?> getNextWorkoutInActivePlan(int planId) async {
    try {
      final endpoint = ApiConfig.nextWorkoutInActivePlanEndpoint(planId.toString());
      _logger.d('GET Next Workout In Active Plan: $endpoint');
      final response = await apiClient.get(
        endpoint,
        context: 'PlanService.getNextWorkoutInActivePlan',
      );
      if (response is Map<String, dynamic>) {
        _logger.d('Next workout (by plan order) fetched successfully');
        return Workout.fromJson(response);
      }
      _logger.d('No next workout returned by endpoint');
      return null;
    } catch (e, stackTrace) {
      handleError('Failed to get next workout in active plan', e, stackTrace);
      return null;
    }
  }

  Future<PlanAnalyticsResponse?> getAppliedPlanAnalytics(
    int appliedPlanId, {
    DateTime? from,
    DateTime? to,
    String? groupBy,
  }) async {
    try {
      final endpoint = ApiConfig.appliedPlanAnalyticsEndpoint(appliedPlanId.toString());
      final query = <String, String>{};
      if (from != null) query['from'] = from.toUtc().toIso8601String();
      if (to != null) query['to'] = to.toUtc().toIso8601String();
      if (groupBy != null) query['group_by'] = groupBy;
      final response = await apiClient.get(
        endpoint,
        queryParams: query.isEmpty ? null : query,
        context: 'PlanService.getAppliedPlanAnalytics',
      );
      if (response is Map<String, dynamic>) {
        return PlanAnalyticsResponse.fromJson(response);
      }
      return null;
    } catch (e, stackTrace) {
      handleError('Failed to get applied plan analytics', e, stackTrace);
      return null;
    }
  }

  Future<bool> cancelAppliedPlan(int appliedPlanId, {String? dropoutReason}) async {
    try {
      final endpoint = ApiConfig.cancelAppliedPlanEndpoint(appliedPlanId.toString());
      _logger.d('POST Cancel Applied Plan: $endpoint');
      final response = await apiClient.post(
        endpoint,
        {
          if (dropoutReason != null && dropoutReason.trim().isNotEmpty)
            'dropout_reason': dropoutReason.trim(),
        },
        context: 'PlanService.cancelAppliedPlan',
      );
      final ok = response != null;
      if (!ok) {
        _logger.w('Cancel applied plan returned null response');
      }
      return ok;
    } catch (e, stackTrace) {
      handleError('Failed to cancel applied plan', e, stackTrace);
      return false;
    }
  }
}
