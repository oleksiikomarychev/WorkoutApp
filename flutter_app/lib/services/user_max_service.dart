import '../models/user_max.dart';
import 'api_client.dart';
import '../config/api_config.dart';
class UserMaxService {
  final ApiClient _apiClient;
  
  UserMaxService(this._apiClient);

  Future<List<UserMax>> getUserMaxes() async {
    final response = await _apiClient.get(ApiConfig.userMaxEndpoint);
    return (response as List).map((json) => UserMax.fromJson(json)).toList();
  }

  Future<UserMax> getUserMax(int id) async {
    final response = await _apiClient.get(ApiConfig.userMaxByIdEndpoint.replaceAll('{user_max_id}', id.toString()));
    return UserMax.fromJson(response);
  }

  Future<UserMax> createUserMax(UserMax userMax) async {
    final response = await _apiClient.post(ApiConfig.userMaxEndpoint, userMax.toJson());
    return UserMax.fromJson(response);
  }

  Future<UserMax> updateUserMax(UserMax userMax) async {
    final response = await _apiClient.put(ApiConfig.userMaxByIdEndpoint.replaceAll('{user_max_id}', userMax.id.toString()), userMax.toJson());
    return UserMax.fromJson(response);
  }

  Future<void> deleteUserMax(int id) async {
    await _apiClient.delete(ApiConfig.userMaxByIdEndpoint.replaceAll('{user_max_id}', id.toString()));
  }
}
