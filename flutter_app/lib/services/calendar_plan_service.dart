import 'package:workout_app/config/api_config.dart';
import 'package:workout_app/models/calendar_plan.dart';
import 'package:workout_app/services/base_api_service.dart';
import 'package:workout_app/services/api_client.dart';

class CalendarPlanService extends BaseApiService {
  CalendarPlanService(ApiClient apiClient) : super(apiClient);

  // Get all calendar plans
  Future<List<CalendarPlan>> getCalendarPlans() async {
    try {
      return await getList<CalendarPlan>(
        ApiConfig.calendarPlansEndpoint,
        (json) => CalendarPlan.fromJson(json as Map<String, dynamic>),
      );
    } catch (e, stackTrace) {
      handleError('Error in getCalendarPlans', e, stackTrace);
      rethrow;
    }
  }

  // Get favorite calendar plans (backend)
  Future<List<CalendarPlan>> getFavoriteCalendarPlans() async {
    try {
      return await getList<CalendarPlan>(
        ApiConfig.calendarPlanFavoritesEndpoint,
        (json) => CalendarPlan.fromJson(json as Map<String, dynamic>),
      );
    } catch (e, stackTrace) {
      handleError('Error in getFavoriteCalendarPlans', e, stackTrace);
      rethrow;
    }
  }

  // Add to favorites
  Future<CalendarPlan> addFavoriteCalendarPlan(int id) async {
    try {
      return await post<CalendarPlan>(
        ApiConfig.calendarPlanFavoriteByIdEndpoint(id.toString()),
        {},
        (json) => CalendarPlan.fromJson(json as Map<String, dynamic>),
      );
    } catch (e, stackTrace) {
      handleError('Error in addFavoriteCalendarPlan', e, stackTrace);
      rethrow;
    }
  }

  // Remove from favorites
  Future<bool> removeFavoriteCalendarPlan(int id) async {
    try {
      return await delete(
        ApiConfig.calendarPlanFavoriteByIdEndpoint(id.toString()),
      );
    } catch (e, stackTrace) {
      handleError('Error in removeFavoriteCalendarPlan', e, stackTrace);
      rethrow;
    }
  }

  // Get a single calendar plan by ID
  Future<CalendarPlan> getCalendarPlan(int id) async {
    try {
      return await get<CalendarPlan>(
        ApiConfig.calendarPlanByIdEndpoint(id.toString()),
        (json) => CalendarPlan.fromJson(json as Map<String, dynamic>),
      );
    } catch (e, stackTrace) {
      handleError('Error in getCalendarPlan', e, stackTrace);
      rethrow;
    }
  }

  // Create a new calendar plan
  Future<CalendarPlan> createCalendarPlan(Map<String, dynamic> data) async {
    try {
      return await post<CalendarPlan>(
        ApiConfig.calendarPlansEndpoint,
        data,
        (json) => CalendarPlan.fromJson(json as Map<String, dynamic>),
      );
    } catch (e, stackTrace) {
      handleError('Error in createCalendarPlan', e, stackTrace);
      rethrow;
    }
  }

  // Update an existing calendar plan
  Future<CalendarPlan> updateCalendarPlan(int id, Map<String, dynamic> data) async {
    try {
      return await put<CalendarPlan>(
        ApiConfig.calendarPlanByIdEndpoint(id.toString()),
        data,
        (json) => CalendarPlan.fromJson(json as Map<String, dynamic>),
      );
    } catch (e, stackTrace) {
      handleError('Error in updateCalendarPlan', e, stackTrace);
      rethrow;
    }
  }

  // Delete a calendar plan
  Future<bool> deleteCalendarPlan(int id) async {
    try {
      return await delete(
        ApiConfig.calendarPlanByIdEndpoint(id.toString()),
      );
    } catch (e, stackTrace) {
      handleError('Error in deleteCalendarPlan', e, stackTrace);
      rethrow;
    }
  }
}
