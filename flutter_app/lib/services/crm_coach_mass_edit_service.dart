import 'package:workout_app/config/api_config.dart';
import 'package:workout_app/services/api_client.dart';
import 'package:workout_app/services/base_api_service.dart';

class CrmCoachMassEditService extends BaseApiService {
  CrmCoachMassEditService(ApiClient apiClient) : super(apiClient);

  Future<Map<String, dynamic>> massEditWorkouts({
    required String athleteId,
    List<Map<String, dynamic>>? workouts,
    List<Map<String, dynamic>>? exerciseInstances,
  }) async {
    final payload = <String, dynamic>{
      if (workouts != null && workouts.isNotEmpty) 'workouts': workouts,
      if (exerciseInstances != null && exerciseInstances.isNotEmpty)
        'exercise_instances': exerciseInstances,
    };
    final endpoint = ApiConfig.crmCoachMassEditEndpoint(athleteId);
    final json = await apiClient.post(
      endpoint,
      payload,
      context: 'CrmCoachMassEditService.massEditWorkouts',
    );
    if (json is Map<String, dynamic>) {
      return json;
    }
    throw ApiException(
      'Invalid response from coach mass edit endpoint',
      statusCode: 0,
      rawResponse: json.toString(),
    );
  }
}
