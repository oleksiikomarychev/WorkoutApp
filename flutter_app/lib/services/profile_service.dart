import '../config/api_config.dart';
import '../models/user_profile.dart';
import 'api_client.dart';
import 'base_api_service.dart';

class ProfileService extends BaseApiService {
  final ApiClient apiClient;

  ProfileService(this.apiClient) : super(apiClient);

  Future<UserProfile> fetchProfile() async {
    try {
      final response = await apiClient.get(
        ApiConfig.profileMeEndpoint,
        context: 'ProfileService.fetchProfile',
      );
      if (response is Map<String, dynamic>) {
        return UserProfile.fromJson(response);
      }
      throw Exception('Unexpected profile response: $response');
    } catch (e, st) {
      handleError('Failed to fetch profile', e, st);
      rethrow;
    }
  }

  Future<UserProfile> updateProfile({
    String? displayName,
    String? bio,
    bool? isPublic,
    double? bodyweightKg,
    double? heightCm,
    int? age,
    String? sex,
    double? trainingExperienceYears,
    String? trainingExperienceLevel,
    String? primaryDefaultGoal,
    String? trainingEnvironment,
  }) async {
    final payload = <String, dynamic>{};
    if (displayName != null) payload['display_name'] = displayName;
    if (bio != null) payload['bio'] = bio;
    if (isPublic != null) payload['is_public'] = isPublic;
    if (bodyweightKg != null) payload['bodyweight_kg'] = bodyweightKg;
    if (heightCm != null) payload['height_cm'] = heightCm;
    if (age != null) payload['age'] = age;
    if (sex != null) payload['sex'] = sex;
    if (trainingExperienceYears != null) {
      payload['training_experience_years'] = trainingExperienceYears;
    }
    if (trainingExperienceLevel != null) {
      payload['training_experience_level'] = trainingExperienceLevel;
    }
    if (primaryDefaultGoal != null) {
      payload['primary_default_goal'] = primaryDefaultGoal;
    }
    if (trainingEnvironment != null) {
      payload['training_environment'] = trainingEnvironment;
    }

    try {
      final response = await apiClient.patch(
        ApiConfig.profileMeEndpoint,
        payload,
        context: 'ProfileService.updateProfile',
      );
      if (response is Map<String, dynamic>) {
        return UserProfile.fromJson(response);
      }
      throw Exception('Unexpected profile update response: $response');
    } catch (e, st) {
      handleError('Failed to update profile', e, st);
      rethrow;
    }
  }

  Future<UserSettings> updateSettings({
    String? unitSystem,
    String? locale,
    String? timezone,
    bool? notificationsEnabled,
  }) async {
    final payload = <String, dynamic>{};
    if (unitSystem != null) payload['unit_system'] = unitSystem;
    if (locale != null) payload['locale'] = locale;
    if (timezone != null) payload['timezone'] = timezone;
    if (notificationsEnabled != null) payload['notifications_enabled'] = notificationsEnabled;

    try {
      final response = await apiClient.patch(
        ApiConfig.profileSettingsEndpoint,
        payload,
        context: 'ProfileService.updateSettings',
      );
      if (response is Map<String, dynamic>) {
        return UserSettings.fromJson(response);
      }
      throw Exception('Unexpected settings update response: $response');
    } catch (e, st) {
      handleError('Failed to update settings', e, st);
      rethrow;
    }
  }
}
