import '../models/user_max.dart';
import 'api_client.dart';
import 'base_api_service.dart';
import '../config/api_config.dart';

/// Service for managing user maximum weight records
class UserMaxService extends BaseApiService {
  /// Creates a new UserMaxService instance
  UserMaxService(ApiClient apiClient) : super(apiClient);

  /// Fetches all user max records for the authenticated user
  /// 
  /// Throws [ApiException] if the request fails
  Future<List<UserMax>> getUserMaxes() async {
    return getList<UserMax>(
      ApiConfig.userMaxesEndpoint,
      UserMax.fromJson,
    );
  }

  /// Fetches a specific user max record by ID
  /// 
  /// Throws [ApiException] if the request fails or the record is not found
  Future<UserMax> getUserMax(String id) async {
    return get<UserMax>(
      ApiConfig.userMaxByIdEndpoint(id),
      UserMax.fromJson,
    );
  }

  /// Fetches all user max records for a specific exercise
  /// 
  /// Throws [ApiException] if the request fails
  Future<List<UserMax>> getUserMaxesByExercise(String exerciseId) async {
    return getList<UserMax>(
      ApiConfig.userMaxesByExerciseEndpoint(exerciseId),
      UserMax.fromJson,
    );
  }

  /// Creates a new user max record
  /// 
  /// Throws [ApiException] if the request fails
  Future<UserMax> createUserMax(UserMax userMax) async {
    if (!userMax.validate()) {
      throw const FormatException('Invalid user max data');
    }

    return post<UserMax>(
      ApiConfig.userMaxesEndpoint,
      userMax.toJson(),
      UserMax.fromJson,
    );
  }

  /// Updates an existing user max record
  /// 
  /// Throws [ApiException] if the request fails
  Future<UserMax> updateUserMax(UserMax userMax) async {
    if (userMax.id == null) {
      throw ArgumentError('Cannot update user max without an ID');
    }

    if (!userMax.validate()) {
      throw const FormatException('Invalid user max data');
    }

    return put<UserMax>(
      ApiConfig.userMaxByIdEndpoint(userMax.id.toString()),
      userMax.toJson(),
      UserMax.fromJson,
    );
  }

  /// Deletes a user max record
  /// 
  /// Throws [ApiException] if the request fails
  Future<void> deleteUserMax(String id) async {
    await delete(ApiConfig.userMaxByIdEndpoint(id));
  }
}
