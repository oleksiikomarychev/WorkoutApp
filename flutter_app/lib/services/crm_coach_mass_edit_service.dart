import 'package:workout_app/config/api_config.dart';
import 'package:workout_app/services/api_client.dart';
import 'package:workout_app/services/base_api_service.dart';

class CoachPlanAiMassEditResponse {
  final Map<String, dynamic> plan;
  final Map<String, dynamic> massEditCommand;

  CoachPlanAiMassEditResponse({
    required this.plan,
    required this.massEditCommand,
  });

  factory CoachPlanAiMassEditResponse.fromJson(Map<String, dynamic> json) {
    return CoachPlanAiMassEditResponse(
      plan: Map<String, dynamic>.from(json['plan'] as Map),
      massEditCommand:
          Map<String, dynamic>.from(json['mass_edit_command'] as Map),
    );
  }
}

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

  Future<CoachPlanAiMassEditResponse> aiMassEditPlan({
    required String athleteId,
    required String prompt,
    String mode = 'preview',
  }) async {
    final payload = <String, dynamic>{
      'prompt': prompt,
      'mode': mode,
    };
    final endpoint = ApiConfig.crmCoachAiMassEditEndpoint(athleteId);
    final json = await apiClient.post(
      endpoint,
      payload,
      context: 'CrmCoachMassEditService.aiMassEditPlan',
    );
    if (json is Map<String, dynamic>) {
      return CoachPlanAiMassEditResponse.fromJson(json);
    }
    throw ApiException(
      'Invalid response from coach AI mass edit endpoint',
      statusCode: 0,
      rawResponse: json.toString(),
    );
  }
}
