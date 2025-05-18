import '../models/user_max.dart';
import 'api_client.dart';
class UserMaxService {
  final ApiClient _apiClient;
  final String _endpoint = '/user-max';
  UserMaxService(this._apiClient);
  Future<List<UserMax>> getUserMaxes() async {
    final response = await _apiClient.get(_endpoint);
    return (response as List).map((json) => UserMax.fromJson(json)).toList();
  }
  Future<UserMax> getUserMax(int id) async {
    final response = await _apiClient.get('$_endpoint/$id');
    return UserMax.fromJson(response);
  }
  Future<UserMax> createUserMax(UserMax userMax) async {
    final response = await _apiClient.post(_endpoint, userMax.toJson());
    return UserMax.fromJson(response);
  }
  Future<UserMax> updateUserMax(UserMax userMax) async {
    final response = await _apiClient.put('$_endpoint/${userMax.id}', userMax.toJson());
    return UserMax.fromJson(response);
  }
  Future<void> deleteUserMax(int id) async {
    await _apiClient.delete('$_endpoint/$id');
  }
}
