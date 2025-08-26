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
      return await getOptional<AppliedCalendarPlan>(
        ApiConfig.activeAppliedCalendarPlanEndpoint,
        (json) => AppliedCalendarPlan.fromJson(json as Map<String, dynamic>),
      );
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
