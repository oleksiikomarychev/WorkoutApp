import '../models/exercise_instance.dart';
import '../models/exercise_definition.dart';
import 'api_client.dart';
import 'base_api_service.dart';
import 'logger_service.dart';
import 'package:workout_app/config/api_config.dart';
import 'package:workout_app/models/muscle_info.dart';
import 'package:workout_app/models/progression_template.dart';
import 'package:http_parser/http_parser.dart';

class ExerciseService extends BaseApiService {
  final ApiClient _apiClient;
  final LoggerService _logger = LoggerService('ExerciseService');

  ExerciseService(this._apiClient) : super(_apiClient);




  Future<List<ExerciseDefinition>> getExerciseDefinitions({
    int? limit,
    int? offset,
    String? search,
    List<String>? muscleGroups,
    List<String>? equipment
  }) async {
    try {
      // Build query parameters
      final queryParams = <String, String>{};
      if (limit != null) queryParams['limit'] = limit.toString();
      if (offset != null) queryParams['offset'] = offset.toString();
      if (search != null && search.isNotEmpty) queryParams['search'] = search;
      if (muscleGroups != null && muscleGroups.isNotEmpty) {
        queryParams['muscle_group'] = muscleGroups.join(',');
      }
      if (equipment != null && equipment.isNotEmpty) {
        queryParams['equipment'] = equipment.join(',');
      }

      final uri = Uri.parse(ApiConfig.exerciseDefinitionsEndpoint)
          .replace(queryParameters: queryParams);
      
      final response = await _apiClient.get(
        uri.toString(),
        context: 'ExerciseService.getExerciseDefinitionsPaginated',
      );
      
      if (response is List) {
        return response
            .whereType<Map<String, dynamic>>()
            .map((json) => ExerciseDefinition.fromJson(json))
            .toList();
      } else {
        handleError(
          'Invalid response format for exercise definitions',
          Exception('Expected a list of exercise definitions'),
        );
        return [];
      }
    } catch (e, stackTrace) {
      handleError('Failed to get exercise definitions', e, stackTrace);
      rethrow;
    }
  }

  // Legacy method for backward compatibility
  Future<List<ExerciseDefinition>> getExerciseDefinitionsLegacy() async {
    try {
      final response = await _apiClient.get(
        ApiConfig.exerciseDefinitionsEndpoint,
        context: 'ExerciseService.getExerciseDefinitions',
      );
      if (response is List) {
        return response
            .whereType<Map<String, dynamic>>()
            .map((json) => ExerciseDefinition.fromJson(json))
            .toList();
      } else {
        handleError(
          'Invalid response format for exercise definitions',
          Exception('Expected a list of exercise definitions'),
        );
        return [];
      }
    } catch (e, stackTrace) {
      handleError('Failed to get exercise definitions', e, stackTrace);
      rethrow;
    }
  }

  Future<ExerciseDefinition> uploadExerciseGif({
    required int exerciseId,
    required List<int> bytes,
    required String filename,
    MediaType? contentType,
  }) async {
    try {
      final endpoint = ApiConfig.uploadExerciseGifEndpoint(exerciseId.toString());
      _logger.d('Uploading exercise gif | endpoint=$endpoint | filename=$filename | bytes=${bytes.length}');

      final response = await _apiClient.postMultipart(
        endpoint,
        bytes: bytes,
        fileField: 'file',
        filename: filename,
        contentType: contentType,
        context: 'ExerciseService.uploadExerciseGif',
      );

      if (response is Map<String, dynamic>) {
        return ExerciseDefinition.fromJson(response);
      }

      handleError(
        'Invalid response format when uploading exercise gif',
        Exception('Expected an exercise definition object'),
      );
      throw Exception('Failed to upload exercise gif');
    } catch (e, stackTrace) {
      handleError('Failed to upload exercise gif', e, stackTrace);
      rethrow;
    }
  }


  Future<List<MuscleInfo>> getMuscles() async {
    try {
      final response = await _apiClient.get(
        ApiConfig.musclesEndpoint,
        context: 'ExerciseService.getMuscles',
      );
      if (response is List) {
        return response
            .whereType<Map<String, dynamic>>()
            .map((json) => MuscleInfo.fromJson(json))
            .toList();
      }
      handleError('Invalid response format for muscles', Exception('Expected a list of muscles'));
      return [];
    } catch (e, stackTrace) {
      handleError('Failed to get muscles', e, stackTrace);
      rethrow;
    }
  }


  Future<List<ExerciseDefinition>> getExercisesByIds(List<int> ids) async {
    try {
      if (ids.isEmpty) return [];

      final endpoint = '${ApiConfig.exerciseDefinitionsEndpoint}?ids=${ids.join(',')}';
      _logger.d('Fetching exercise definitions | endpoint=$endpoint');

      final response = await _apiClient.get(
        endpoint,
        context: 'ExerciseService.getExercisesByIds',
      );

      if (response is List) {
        return response
            .whereType<Map<String, dynamic>>()
            .map((json) => ExerciseDefinition.fromJson(json))
            .toList();
      } else {
        handleError('Invalid response format for exercise definitions',
            Exception('Expected a list of exercise definitions'));
        return [];
      }
    } catch (e, stackTrace) {
      handleError('Failed to get exercise definitions by IDs', e, stackTrace);
      rethrow;
    }
  }


  Future<ExerciseDefinition> getExerciseDefinition(int id) async {
    try {
      final endpoint = ApiConfig.exerciseDefinitionByIdEndpoint(id.toString());
      _logger.d('Fetching exercise definition | endpoint=$endpoint');
      final response = await _apiClient.get(
        endpoint,
        context: 'ExerciseService.getExerciseDefinition',
      );

      if (response is Map<String, dynamic>) {
        return ExerciseDefinition.fromJson(response);
      } else {
        handleError('Invalid response format for exercise definition',
            Exception('Expected an exercise definition object'));
        throw Exception('Failed to get exercise definition');
      }
    } catch (e, stackTrace) {
      handleError('Failed to get exercise definition', e, stackTrace);
      rethrow;
    }
  }


  Future<ExerciseDefinition> createExerciseDefinition(ExerciseDefinition exercise) async {
    try {
      final endpoint = ApiConfig.exerciseDefinitionsEndpoint;
      final body = exercise.toJson();
      _logger.d('Creating exercise definition | endpoint=$endpoint | body=$body');
      final response = await _apiClient.post(
        endpoint,
        body,
        context: 'ExerciseService.createExerciseDefinition',
      );

      if (response is Map<String, dynamic>) {
        return ExerciseDefinition.fromJson(response);
      } else {
        handleError('Invalid response format when creating exercise definition',
            Exception('Expected an exercise definition object'));
        throw Exception('Failed to create exercise definition');
      }
    } catch (e, stackTrace) {
      handleError('Failed to create exercise definition', e, stackTrace);
      rethrow;
    }
  }


  Future<ExerciseDefinition> updateExerciseDefinition(ExerciseDefinition exercise) async {
    try {
      if (exercise.id == null) {
        throw Exception('Cannot update exercise definition without an ID');
      }

      final endpoint = ApiConfig.exerciseDefinitionByIdEndpoint(exercise.id.toString());
      final body = exercise.toJson();
      _logger.d('Updating exercise definition | endpoint=$endpoint | body=$body');
      final response = await _apiClient.put(
        endpoint,
        body,
        context: 'ExerciseService.updateExerciseDefinition',
      );

      if (response is Map<String, dynamic>) {
        return ExerciseDefinition.fromJson(response);
      } else {
        handleError('Invalid response format when updating exercise definition',
            Exception('Expected an exercise definition object'));
        throw Exception('Failed to update exercise definition');
      }
    } catch (e, stackTrace) {
      handleError('Failed to update exercise definition', e, stackTrace);
      rethrow;
    }
  }


  Future<bool> deleteExerciseDefinition(int id) async {
    try {
      final endpoint = ApiConfig.exerciseDefinitionByIdEndpoint(id.toString());
      _logger.d('Deleting exercise definition | endpoint=$endpoint');
      await _apiClient.delete(
        endpoint,
        context: 'ExerciseService.deleteExerciseDefinition',
      );
      return true;
    } catch (e, stackTrace) {
      handleError('Failed to delete exercise definition', e, stackTrace);
      return false;
    }
  }


  Future<List<ProgressionTemplate>> getTemplates() async {

    return [];
  }

  Future<ExerciseDefinition> uploadExerciseImage({
    required int exerciseId,
    required List<int> bytes,
    required String filename,
    MediaType? contentType,
  }) async {
    try {
      final endpoint = ApiConfig.uploadExerciseImageEndpoint(exerciseId.toString());
      _logger.d('Uploading exercise image | endpoint=$endpoint | filename=$filename | bytes=${bytes.length}');

      final response = await _apiClient.postMultipart(
        endpoint,
        bytes: bytes,
        fileField: 'file',
        filename: filename,
        contentType: contentType,
        context: 'ExerciseService.uploadExerciseImage',
      );

      if (response is Map<String, dynamic>) {
        return ExerciseDefinition.fromJson(response);
      }

      handleError(
        'Invalid response format when uploading exercise image',
        Exception('Expected an exercise definition object'),
      );
      throw Exception('Failed to upload exercise image');
    } catch (e, stackTrace) {
      handleError('Failed to upload exercise image', e, stackTrace);
      rethrow;
    }
  }




  Future<ExerciseInstance> getExerciseInstance(int id) async {
    try {
      final endpoint = ApiConfig.exerciseInstanceByIdEndpoint(id.toString());
      _logger.d('Fetching exercise instance | endpoint=$endpoint');
      final response = await _apiClient.get(
        endpoint,
        context: 'ExerciseService.getExerciseInstance',
      );

      if (response is Map<String, dynamic>) {
        return ExerciseInstance.fromJson(response);
      } else {
        handleError('Invalid response format for exercise instance',
            Exception('Expected an exercise instance object'));
        throw Exception('Failed to get exercise instance');
      }
    } catch (e, stackTrace) {
      handleError('Failed to get exercise instance', e, stackTrace);
      rethrow;
    }
  }


  Future<ExerciseInstance> createExerciseInstance(ExerciseInstance instance) async {
    try {
      final endpoint = ApiConfig.getInstancesByWorkoutEndpoint(instance.workoutId.toString());
      final body = instance.toJson();
      _logger.d('POST ExerciseInstance | endpoint=$endpoint | body=$body');
      final response = await _apiClient.post(
        endpoint,
        body,
        context: 'ExerciseService.createExerciseInstance',
      );

      if (response is Map<String, dynamic>) {
        return ExerciseInstance.fromJson(response);
      } else {
        handleError('Invalid response format when creating exercise instance',
            Exception('Expected an exercise instance object'));
        throw Exception('Failed to create exercise instance');
      }
    } catch (e, stackTrace) {
      handleError('Failed to create exercise instance', e, stackTrace);
      rethrow;
    }
  }


  Future<ExerciseInstance> updateExerciseInstance(ExerciseInstance instance) async {
    try {
      if (instance.id == null) {
        throw Exception('Cannot update exercise instance without an ID');
      }

      final endpoint = ApiConfig.exerciseInstanceByIdEndpoint(instance.id.toString());
      final payload = instance.toJson();
      _logger.d('PUT ExerciseInstance | endpoint=$endpoint | body=$payload');
      final response = await _apiClient.put(
        endpoint,
        payload,
        context: 'ExerciseService.updateExerciseInstance',
      );

      if (response is Map<String, dynamic>) {
        return ExerciseInstance.fromJson(response);
      } else {
        handleError('Invalid response format when updating exercise instance',
            Exception('Expected an exercise instance object'));
        throw Exception('Failed to update exercise instance');
      }
    } catch (e, stackTrace) {
      handleError('Failed to update exercise instance', e, stackTrace);
      rethrow;
    }
  }


  Future<bool> deleteExerciseInstance(int id) async {
    try {
      final endpoint = ApiConfig.exerciseInstanceByIdEndpoint(id.toString());
      _logger.d('DELETE ExerciseInstance | endpoint=$endpoint');
      await _apiClient.delete(
        endpoint,
        context: 'ExerciseService.deleteExerciseInstance',
      );
      return true;
    } catch (e, stackTrace) {
      handleError('Failed to delete exercise instance', e, stackTrace);
      return false;
    }
  }
}
