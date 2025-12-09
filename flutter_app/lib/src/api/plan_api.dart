import 'dart:convert';
import 'package:http/http.dart' as http;
import 'package:workout_app/models/user_max.dart';
import 'package:workout_app/config/api_config.dart';
import 'package:workout_app/models/workout.dart';
import 'package:workout_app/models/calendar_plan.dart';
import 'package:workout_app/models/calendar_plan_summary.dart';
import 'package:workout_app/services/api_client.dart';

class PlanApi {
  static final ApiClient _apiClient = ApiClient();

  static Future<List<UserMax>> getUserMaxes() async {
    final data = await _apiClient.get(ApiConfig.getUserMaxesEndpoint()) as List<dynamic>;
    return data.map((json) => UserMax.fromJson(json as Map<String, dynamic>)).toList();
  }

  static Future<List<Workout>> applyPlan({
    required int planId,
    required List<int> userMaxIds,
    required bool computeWeights,
    required double roundingStep,
    required String roundingMode,
  }) async {
    final endpoint = ApiConfig.applyPlanEndpoint(planId.toString());
    final query = {
      'user_max_ids': userMaxIds.join(','),
    };
    final payload = {
      'name': 'Applied Plan',
      'compute_weights': computeWeights,
      'rounding_step': roundingStep,
      'rounding_mode': roundingMode == 'up' ? 'ceil' : roundingMode == 'down' ? 'floor' : roundingMode,
      'generate_workouts': true,
    };
    final data = await _apiClient.post(
      endpoint,
      payload,
      queryParams: query,
      context: 'applyPlan',
    ) as List<dynamic>;
    return data.map((json) => Workout.fromJson(json as Map<String, dynamic>)).toList();
  }

  static Future<UserMax> createUserMax({
    required int exerciseId,
    required int maxWeight,
    required int repMax,
    required String date,
  }) async {
    final response = await _apiClient.post(
      ApiConfig.createUserMaxEndpoint(),
      {
        'exercise_id': exerciseId,
        'max_weight': maxWeight,
        'rep_max': repMax,
        'date': date,
      },
    ) as Map<String, dynamic>;

    return UserMax.fromJson(response);
  }


  static Future<List<CalendarPlanSummary>> getVariants(int planId) async {
    final data = await _apiClient.get(
      ApiConfig.listPlanVariantsEndpoint(planId.toString()),
    ) as List<dynamic>;
    return data
        .map((json) => CalendarPlanSummary.fromJson(json as Map<String, dynamic>))
        .toList();
  }

  static Future<CalendarPlan> getCalendarPlan(int planId) async {
    final data = await _apiClient.get(
      ApiConfig.getCalendarPlanEndpoint(planId.toString()),
    ) as Map<String, dynamic>;
    return CalendarPlan.fromJson(data);
  }

  static Future<CalendarPlan> createVariant({
    required int planId,
    required String name,
  }) async {
    final data = await _apiClient.post(
      ApiConfig.createPlanVariantEndpoint(planId.toString()),
      {
        'name': name,
      },
    ) as Map<String, dynamic>;
    return CalendarPlan.fromJson(data);
  }

  static Future<CalendarPlan> updateCalendarPlanPublic({
    required int planId,
    required bool isPublic,
  }) async {
    final endpoint = ApiConfig.updateCalendarPlanEndpoint(planId.toString());
    final payload = {
      'is_public': isPublic,
    };
    final data = await _apiClient.put(
      endpoint,
      payload,
      context: 'updateCalendarPlanPublic',
    ) as Map<String, dynamic>;
    return CalendarPlan.fromJson(data);
  }
}
