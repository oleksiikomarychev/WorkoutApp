import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:logger/logger.dart';
import 'package:workout_app/services/api_client.dart';
import 'package:workout_app/services/user_max_service.dart';
import 'package:workout_app/config/api_config.dart';

final apiClientProvider = Provider<ApiClient>((ref) {
  return ApiClient(baseUrl: ApiConfig.baseUrl);
});

final userMaxServiceProvider = Provider<UserMaxService>((ref) {
  return UserMaxService(ref.watch(apiClientProvider));
});


Future<void> init() async {

  await ApiConfig.initialize();
}
