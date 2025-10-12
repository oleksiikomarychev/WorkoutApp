import 'dart:convert';
import '../config/api_config.dart';
import '../models/applied_calendar_plan.dart';
import '../models/workout.dart';
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
}
