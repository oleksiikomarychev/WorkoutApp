import 'dart:convert';
import 'package:http/http.dart' as http;
import 'package:workout_app/models/user_max.dart';
import 'package:workout_app/config/api_config.dart';
import 'package:workout_app/models/workout.dart';

class PlanApi {
  static Future<List<UserMax>> getUserMaxes() async {
    final response = await http.get(Uri.parse(ApiConfig.buildFullUrl(ApiConfig.getUserMaxesEndpoint())));
    if (response.statusCode == 200) {
      final List<dynamic> data = json.decode(response.body);
      return data.map((json) => UserMax.fromJson(json)).toList();
    } else {
      throw Exception('Failed to load user maxes');
    }
  }

  static Future<List<Workout>> applyPlan({
    required int planId,
    required List<int> userMaxIds,
    required bool computeWeights,
    required double roundingStep,
    required String roundingMode,
  }) async {
    final url = ApiConfig.buildFullUrl(ApiConfig.applyPlanEndpoint(planId.toString()));
    final uri = Uri.parse(url).replace(queryParameters: {
      'user_max_ids': userMaxIds.join(','),
    });
    print('Apply Plan URL: ${uri.toString()}');
    final response = await http.post(
      uri,
      headers: {
        'Content-Type': 'application/json',
      },
      body: json.encode({
        'name': 'Applied Plan',
        'compute_weights': computeWeights,
        'rounding_step': roundingStep,
        'rounding_mode': roundingMode == 'up' ? 'ceil' : roundingMode == 'down' ? 'floor' : roundingMode,
        'generate_workouts': true,
      }),
    );

    if (response.statusCode == 200) {
      final List<dynamic> data = json.decode(response.body);
      return data.map((json) => Workout.fromJson(json)).toList();
    } else {
      ApiConfig.logApiError(response);
      throw Exception('Failed to apply plan: ${response.body}');
    }
  }
}
