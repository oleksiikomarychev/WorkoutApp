import 'package:workout_app/config/api_config.dart';
import 'package:workout_app/services/api_client.dart';
import 'package:workout_app/services/base_api_service.dart';
import 'package:workout_app/services/logger_service.dart';

class AgentAppliedPlanMassEditService extends BaseApiService {
  AgentAppliedPlanMassEditService(ApiClient apiClient) : super(apiClient);

  final LoggerService _logger = LoggerService('AgentAppliedPlanMassEditService');

  /// Starts an applied-plan mass edit job via agent-service and returns Celery task id.
  Future<String> startAppliedPlanMassEdit({
    required int appliedPlanId,
    required String prompt,
    String mode = 'apply',
  }) async {
    try {
      final payload = <String, dynamic>{
        'applied_plan_id': appliedPlanId,
        'mode': mode,
        'prompt': prompt,
      };

      final json = await apiClient.post(
        ApiConfig.agentAppliedPlanMassEditEndpoint,
        payload,
        context: 'AgentAppliedPlanMassEditService.startAppliedPlanMassEdit',
      );

      if (json is Map<String, dynamic>) {
        final taskId = json['task_id'];
        if (taskId is String && taskId.isNotEmpty) {
          return taskId;
        }
        throw ApiException(
          'Missing task_id in agent applied mass edit response',
          statusCode: 0,
          rawResponse: json.toString(),
        );
      }

      throw ApiException(
        'Invalid response from agent applied mass edit endpoint',
        statusCode: 0,
        rawResponse: json.toString(),
      );
    } catch (e, st) {
      _logger.e('Failed to start applied plan mass edit: $e', e, st);
      rethrow;
    }
  }
}

