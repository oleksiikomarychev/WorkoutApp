import 'package:workout_app/config/api_config.dart';
import 'package:workout_app/models/calendar_plan_instance.dart';
import 'package:workout_app/services/base_api_service.dart';
import 'package:workout_app/services/api_client.dart';

class CalendarPlanInstanceService extends BaseApiService {
  CalendarPlanInstanceService(ApiClient apiClient) : super(apiClient);

  Future<List<CalendarPlanInstance>> listInstances() async {
    try {
      return await getList<CalendarPlanInstance>(
        ApiConfig.calendarPlanInstancesEndpoint,
        (json) => CalendarPlanInstance.fromJson(json),
      );
    } catch (e, st) {
      handleError('Error in listInstances', e, st);
    }
  }

  Future<CalendarPlanInstance> getInstance(int id) async {
    try {
      return await get<CalendarPlanInstance>(
        ApiConfig.calendarPlanInstanceByIdEndpoint(id.toString()),
        (json) => CalendarPlanInstance.fromJson(json),
      );
    } catch (e, st) {
      handleError('Error in getInstance', e, st);
    }
  }

  Future<CalendarPlanInstance> createFromPlan(int planId) async {
    try {
      return await post<CalendarPlanInstance>(
        ApiConfig.createInstanceFromPlanEndpoint(planId.toString()),
        {},
        (json) => CalendarPlanInstance.fromJson(json),
      );
    } catch (e, st) {
      handleError('Error in createFromPlan', e, st);
    }
  }

  Future<CalendarPlanInstance> createInstance(Map<String, dynamic> data) async {
    try {
      return await post<CalendarPlanInstance>(
        ApiConfig.calendarPlanInstancesEndpoint,
        data,
        (json) => CalendarPlanInstance.fromJson(json),
      );
    } catch (e, st) {
      handleError('Error in createInstance', e, st);
    }
  }

  Future<CalendarPlanInstance> updateInstance(int id, Map<String, dynamic> data) async {
    try {
      return await put<CalendarPlanInstance>(
        ApiConfig.calendarPlanInstanceByIdEndpoint(id.toString()),
        data,
        (json) => CalendarPlanInstance.fromJson(json),
      );
    } catch (e, st) {
      handleError('Error in updateInstance', e, st);
    }
  }

  Future<bool> deleteInstance(int id) async {
    try {
      return await delete(
        ApiConfig.calendarPlanInstanceByIdEndpoint(id.toString()),
      );
    } catch (e, st) {
      handleError('Error in deleteInstance', e, st);
    }
  }
}
