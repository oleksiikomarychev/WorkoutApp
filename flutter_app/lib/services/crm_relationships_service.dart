import 'package:workout_app/config/api_config.dart';
import 'package:workout_app/models/crm_coach_athlete_link.dart';
import 'package:workout_app/services/api_client.dart';
import 'package:workout_app/services/base_api_service.dart';
import 'package:workout_app/services/logger_service.dart';

class CrmRelationshipsService extends BaseApiService {
  final LoggerService _logger = LoggerService('CrmRelationshipsService');

  CrmRelationshipsService(ApiClient apiClient) : super(apiClient);

  Future<List<CoachAthleteLink>> getMyAthletes({
    String? status,
    int limit = 100,
    int offset = 0,
  }) async {
    try {
      final query = <String, dynamic>{
        'limit': limit.toString(),
        'offset': offset.toString(),
        if (status != null) 'status': status,
      };
      final list = await getList<CoachAthleteLink>(
        ApiConfig.crmMyRelationshipsEndpoint,
        CoachAthleteLink.fromJson,
        queryParams: query,
      );
      return list;
    } catch (e, st) {
      handleError('Failed to fetch CRM relationships', e, st);
    }
  }

  Future<List<CoachAthleteLink>> getMyCoaches({
    String? status,
    int limit = 100,
    int offset = 0,
  }) async {
    try {
      final query = <String, dynamic>{
        'limit': limit.toString(),
        'offset': offset.toString(),
        if (status != null) 'status': status,
      };
      final list = await getList<CoachAthleteLink>(
        ApiConfig.crmMyCoachesEndpoint,
        CoachAthleteLink.fromJson,
        queryParams: query,
      );
      return list;
    } catch (e, st) {
      handleError('Failed to fetch CRM coaches', e, st);
    }
  }

  Future<CoachAthleteLink> requestCoaching({
    required String coachId,
    String? note,
  }) async {
    try {
      final body = <String, dynamic>{
        'coach_id': coachId,
        if (note != null && note.trim().isNotEmpty) 'note': note.trim(),
      };
      return await post<CoachAthleteLink>(
        ApiConfig.crmRelationshipsEndpoint,
        body,
        CoachAthleteLink.fromJson,
      );
    } catch (e, st) {
      handleError('Failed to request coaching', e, st);
    }
  }

  Future<CoachAthleteLink> createLink({required String athleteId}) async {
    try {
      final body = <String, dynamic>{'athlete_id': athleteId};
      return await post<CoachAthleteLink>(
        ApiConfig.crmRelationshipsEndpoint,
        body,
        CoachAthleteLink.fromJson,
      );
    } catch (e, st) {
      handleError('Failed to create CRM relationship', e, st);
    }
  }

  Future<CoachAthleteLink> updateStatus({
    required int id,
    required String status,
    String? endedReason,
  }) async {
    try {
      final body = <String, dynamic>{
        'status': status,
        if (endedReason != null && endedReason.trim().isNotEmpty)
          'ended_reason': endedReason.trim(),
      };
      return await patch<CoachAthleteLink>(
        ApiConfig.crmRelationshipStatusEndpoint(id.toString()),
        body,
        CoachAthleteLink.fromJson,
      );
    } catch (e, st) {
      handleError('Failed to update CRM relationship status', e, st);
    }
  }
}
