import 'package:workout_app/models/user_max.dart';
import 'package:workout_app/config/api_config.dart';
import 'package:workout_app/models/workout.dart';
import 'package:workout_app/models/calendar_plan.dart';
import 'package:workout_app/models/calendar_plan_summary.dart';
import 'package:workout_app/services/api_client.dart';

class PlanApi {
  static final ApiClient _apiClient = ApiClient();

  static Future<Map<String, dynamic>> applyPlanAsync({
    required int planId,
    required List<int> userMaxIds,
    required bool computeWeights,
    required double roundingStep,
    required String roundingMode,
  }) async {
    final endpoint = ApiConfig.applyPlanAsyncEndpoint(planId.toString());
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
      timeout: const Duration(seconds: 30),
      context: 'applyPlanAsync',
    );
    if (data is Map<String, dynamic>) {
      return data;
    }
    return <String, dynamic>{};
  }

  static Future<Map<String, dynamic>> getPlanTaskStatus(String taskId) async {
    final endpoint = ApiConfig.plansTaskStatusEndpoint(taskId);
    final data = await _apiClient.get(
      endpoint,
      timeout: const Duration(seconds: 30),
      context: 'getPlanTaskStatus',
    );
    if (data is Map<String, dynamic>) {
      return data;
    }
    return <String, dynamic>{};
  }

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
      timeout: const Duration(seconds: 120),
      context: 'applyPlan',
    ) as List<dynamic>;

    await _apiClient.invalidateCacheGroups(const [
      'plans:active',
      'plans:list',
      'plans:variants',
      'workouts:list',
      'workouts:history_all',
    ]);
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

    await _apiClient.invalidateCacheGroups([
      'plans:list',
      'plans:variants',
      'plans:variants:$planId',
      'plans:detail',
      'plans:detail:$planId',
    ]);
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

    await _apiClient.invalidateCacheGroups([
      'plans:list',
      'plans:detail',
      'plans:detail:$planId',
      'plans:variants',
    ]);
    return CalendarPlan.fromJson(data);
  }


  static Future<CalendarPlan> recalcCalendarPlanSets(int planId) async {
    final endpoint = ApiConfig.recalcCalendarPlanSetsEndpoint(planId.toString());
    final data = await _apiClient.post(
      endpoint,
      const {},
      context: 'recalcCalendarPlanSets',
    ) as Map<String, dynamic>;

    await _apiClient.invalidateCacheGroups([
      'plans:detail',
      'plans:detail:$planId',
      'plans:list',
    ]);
    return CalendarPlan.fromJson(data);
  }

  static Future<int> getRootPlanAdoptersCount(int rootPlanId) async {
    final data = await _apiClient.get(
      ApiConfig.rootPlanAdoptersStatsEndpoint(rootPlanId.toString()),
    ) as Map<String, dynamic>;
    final raw = data['unique_adopters'];
    if (raw is int) return raw;
    if (raw is num) return raw.toInt();
    return int.tryParse(raw?.toString() ?? '') ?? 0;
  }
}
