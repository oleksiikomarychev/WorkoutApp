import 'package:workout_app/config/api_config.dart';
import 'package:workout_app/services/api_client.dart';
import 'package:workout_app/services/base_api_service.dart';

class AgentPlanMassEditResponse {
  final Map<String, dynamic> plan;
  final Map<String, dynamic> massEditCommand;

  AgentPlanMassEditResponse({
    required this.plan,
    required this.massEditCommand,
  });

  factory AgentPlanMassEditResponse.fromJson(Map<String, dynamic> json) {
    return AgentPlanMassEditResponse(
      plan: Map<String, dynamic>.from(json['plan'] as Map),
      massEditCommand:
          Map<String, dynamic>.from(json['mass_edit_command'] as Map),
    );
  }
}

class AgentMassEditService extends BaseApiService {
  AgentMassEditService(ApiClient apiClient) : super(apiClient);

  Future<AgentPlanMassEditResponse> planMassEdit({
    required int planId,
    required String prompt,
    String mode = 'preview',
  }) async {
    final payload = <String, dynamic>{
      'plan_id': planId,
      'prompt': prompt,
      'mode': mode,
    };

    final json = await apiClient.post(
      ApiConfig.agentPlanMassEditEndpoint,
      payload,
      context: 'AgentMassEditService.planMassEdit',
    );

    if (json is Map<String, dynamic>) {
      return AgentPlanMassEditResponse.fromJson(json);
    }
    throw ApiException(
      'Invalid response from agent mass edit endpoint',
      statusCode: 0,
      rawResponse: json.toString(),
    );
  }
}
