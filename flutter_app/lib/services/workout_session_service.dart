import 'dart:convert';

import 'package:workout_app/config/api_config.dart';
import 'package:workout_app/models/workout_session.dart';
import 'package:workout_app/services/api_client.dart';
import 'package:workout_app/services/base_api_service.dart';
import 'package:workout_app/services/logger_service.dart';

class WorkoutSessionService extends BaseApiService {
  final ApiClient _apiClient;
  final LoggerService _logger = LoggerService('WorkoutSessionService');

  WorkoutSessionService(this._apiClient) : super(_apiClient);

  // POST /workouts/{workout_id}/start
  Future<WorkoutSession> startSession(int workoutId) async {
    try {
      final endpoint = ApiConfig.startWorkoutSessionEndpoint(workoutId.toString());
      _logger.d('Starting session for workout $workoutId');
      final response = await _apiClient.post(
        endpoint,
        <String, dynamic>{}, // path contains workoutId; backend doesn't require body
        context: 'WorkoutSessionService.startSession',
      );

      if (response is Map<String, dynamic>) {
        return WorkoutSession.fromJson(response);
      }
      throw Exception('Unexpected response format when starting session');
    } catch (e, st) {
      handleError('Failed to start session for workout $workoutId', e, st);
    }
  }

  // GET /workouts/{workout_id}/active -> may be 404 (no active)
  Future<WorkoutSession?> getActiveSession(int workoutId) async {
    final endpoint = ApiConfig.activeWorkoutSessionEndpoint(workoutId.toString());
    try {
      _logger.d('Fetching active session for workout $workoutId');
      final response = await _apiClient.get(
        endpoint,
        context: 'WorkoutSessionService.getActiveSession',
      );
      if (response == null) return null;
      if (response is Map<String, dynamic>) {
        return WorkoutSession.fromJson(response);
      }
      throw Exception('Unexpected response format for active session');
    } catch (e) {
      // Treat 404 as no active session
      if (e is ApiException && e.statusCode == 404) {
        _logger.d('No active session for workout $workoutId (404)');
        return null;
      }
      rethrow;
    }
  }

  // GET /workouts/{workout_id}/history
  Future<List<WorkoutSession>> listSessions(int workoutId) async {
    try {
      final endpoint = ApiConfig.workoutSessionHistoryEndpoint(workoutId.toString());
      _logger.d('Listing sessions for workout $workoutId');
      final response = await _apiClient.get(
        endpoint,
        context: 'WorkoutSessionService.listSessions',
      );

      if (response is List) {
        return response
            .whereType<Map<String, dynamic>>()
            .map(WorkoutSession.fromJson)
            .toList();
      }
      if (response is Map<String, dynamic>) {
        // Some backends may return a single object
        return [WorkoutSession.fromJson(response)];
      }
      throw Exception('Unexpected response format for session history');
    } catch (e, st) {
      handleError('Failed to list sessions for workout $workoutId', e, st);
    }
  }

  // PUT /sessions/{session_id}/instances/{instance_id}/sets/{set_id}
  Future<WorkoutSession> updateSetCompletion({
    required int sessionId,
    required int instanceId,
    required int setId,
    required bool completed,
  }) async {
    try {
      final endpoint = ApiConfig.sessionSetCompletionEndpoint(
        sessionId.toString(),
        instanceId.toString(),
        setId.toString(),
      );
      final payload = <String, dynamic>{
        'instance_id': instanceId,
        'set_id': setId,
        'completed': completed,
      };
      _logger.d('Updating set completion: session=$sessionId instance=$instanceId set=$setId completed=$completed');
      final response = await _apiClient.put(
        endpoint,
        payload,
        context: 'WorkoutSessionService.updateSetCompletion',
      );
      if (response is Map<String, dynamic>) {
        return WorkoutSession.fromJson(response);
      }
      throw Exception('Unexpected response format when updating set completion');
    } catch (e, st) {
      handleError('Failed to update set completion', e, st);
    }
  }

  // POST /sessions/{session_id}/finish
  Future<WorkoutSession> finishSession(
    int sessionId, {
    bool cancelled = false,
    bool markWorkoutCompleted = false,
  }) async {
    try {
      final endpoint = ApiConfig.finishSessionEndpoint(sessionId.toString());
      final payload = <String, dynamic>{
        'cancelled': cancelled,
        'mark_workout_completed': markWorkoutCompleted,
      };
      _logger.d('Finishing session $sessionId | payload=$payload');
      final response = await _apiClient.post(
        endpoint,
        payload,
        context: 'WorkoutSessionService.finishSession',
      );
      if (response is Map<String, dynamic>) {
        return WorkoutSession.fromJson(response);
      }
      throw Exception('Unexpected response format when finishing session');
    } catch (e, st) {
      handleError('Failed to finish session $sessionId', e, st);
    }
  }
}
