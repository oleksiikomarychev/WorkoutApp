import 'dart:convert';
import '../config/api_config.dart';
import '../models/applied_calendar_plan.dart';
import 'api_client.dart';
import 'base_api_service.dart';
import 'logger_service.dart';

class PlanService extends BaseApiService {
  final ApiClient apiClient;

  PlanService({required this.apiClient}) : super(apiClient);

  Future<AppliedCalendarPlan?> getActivePlan() async {
    try {
      final endpoint = ApiConfig.getActivePlanEndpoint;
      final response = await apiClient.get(
        endpoint,
        context: 'PlanService.getActivePlan',
      );
      if (response is Map<String, dynamic>) {
        return AppliedCalendarPlan.fromJson(response);
      }
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
}
