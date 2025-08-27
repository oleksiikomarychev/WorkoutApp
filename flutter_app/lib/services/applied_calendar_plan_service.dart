import 'package:workout_app/config/api_config.dart';
import 'package:workout_app/models/applied_calendar_plan.dart';
import 'package:workout_app/models/apply_plan_request.dart';
import 'package:workout_app/services/api_client.dart';
import 'package:workout_app/services/base_api_service.dart';

class AppliedCalendarPlanService extends BaseApiService {
  AppliedCalendarPlanService(ApiClient apiClient) : super(apiClient);

  Future<AppliedCalendarPlan> applyPlan({
    required int planId,
    required ApplyPlanRequest request,
  }) async {
    try {
      return await post<AppliedCalendarPlan>(
        ApiConfig.applyCalendarPlanEndpoint(planId.toString()),
        request.toJson(),
        (json) => AppliedCalendarPlan.fromJson(json as Map<String, dynamic>),
      );
    } catch (e, stackTrace) {
      handleError('Error in applyPlan', e, stackTrace);
    }
  }

  Future<AppliedCalendarPlan> applyPlanFromInstance({
    required int instanceId,
    required ApplyPlanRequest request,
  }) async {
    try {
      return await post<AppliedCalendarPlan>(
        ApiConfig.applyFromInstanceEndpoint(instanceId.toString()),
        request.toJson(),
        (json) => AppliedCalendarPlan.fromJson(json as Map<String, dynamic>),
      );
    } catch (e, stackTrace) {
      handleError('Error in applyPlanFromInstance', e, stackTrace);
    }
  }

  Future<AppliedCalendarPlan?> getActiveAppliedCalendarPlan() async {
    try {
      // Call API directly to handle null or empty-map gracefully
      final response = await apiClient.get(
        ApiConfig.activeAppliedCalendarPlanEndpoint,
        context: 'AppliedCalendarPlanService.getActiveAppliedCalendarPlan',
      );

      // Upstream may return:
      // - null (no active plan)
      // - {} (empty object) — treat as no active plan
      // - a populated map with plan fields
      if (response == null) {
        return null;
      }
      if (response is Map<String, dynamic>) {
        if (response.isEmpty) {
          return null;
        }
        return AppliedCalendarPlan.fromJson(response);
      }

      // Any other unexpected format
      throw Exception('Unexpected response format for active applied plan');
    } catch (e, stackTrace) {
      handleError('Error in getActiveAppliedCalendarPlan', e, stackTrace);
    }
  }

  Future<List<AppliedCalendarPlan>> getUserAppliedCalendarPlans() async {
    try {
      return await getList<AppliedCalendarPlan>(
        ApiConfig.userAppliedCalendarPlansEndpoint,
        (json) => AppliedCalendarPlan.fromJson(json as Map<String, dynamic>),
      );
    } catch (e, stackTrace) {
      handleError('Error in getUserAppliedCalendarPlans', e, stackTrace);
      rethrow;
    }
  }
}
