import 'package:flutter/foundation.dart' show kIsWeb, defaultTargetPlatform, TargetPlatform;
import 'package:http/http.dart' as http;

class ApiConfig {
  // Base URLs (ensure no trailing slashes)
  static const String androidEmulatorBaseUrl = 'http://10.0.2.2:8000';
  static const String localBaseUrl = 'http://localhost:8000';
  static const String productionBaseUrl = 'https://yourproductionapi.com';
  
  // Timeouts
  static const int connectionTimeout = 30;
  static const int receiveTimeout = 30;
  
  // API Version
  static const String apiVersion = 'v1';
  
  // API Base Path
  static const String apiBasePath = 'api';
  
  /// Returns the base URL for API requests (platform-aware)
  static String getBaseUrl() {
    if (kIsWeb) return localBaseUrl; // web runs in host browser

    // Android emulator cannot reach host via localhost; use 10.0.2.2
    if (defaultTargetPlatform == TargetPlatform.android) {
      return androidEmulatorBaseUrl;
    }

    // iOS simulator and desktop can use localhost to reach host
    return localBaseUrl;
  }
  
  /// Builds a full API URL by combining base URL, API path, and endpoint
  static String buildEndpoint(String path) {
    // Remove any leading slashes from the path to avoid double slashes
    final cleanPath = path.startsWith('/') ? path.substring(1) : path;
    return '$apiBasePath/$apiVersion/$cleanPath';
  }
  
  /// Builds a full URL by combining base URL with the given path
  static String buildFullUrl(String path) {
    final baseUrl = getBaseUrl().endsWith('/')
        ? getBaseUrl().substring(0, getBaseUrl().length - 1)
        : getBaseUrl();
    final cleanPath = path.startsWith('/') ? path.substring(1) : path;
    return '$baseUrl/$cleanPath';
  }

  // Health Check
  static String get rpeHealthEndpoint => buildEndpoint('/rpe/health');
  static String get healthEndpoint => buildEndpoint('/health');
  static String get exercisesHealthEndpoint => buildEndpoint('/exercises/health');
  static String get musclesEndpoint => buildEndpoint('/exercises/muscles');
  static String get exerciseDefinitionsEndpoint => buildEndpoint('/exercises/definitions');
  static String createExerciseDefinitionEndpoint() => buildEndpoint('/exercises/definitions');
  static String exerciseDefinitionByIdEndpoint(String exerciseListId) => buildEndpoint('/exercises/definitions/$exerciseListId');
  static String updateExerciseDefinitionEndpoint(String exerciseListId) => buildEndpoint('/exercises/definitions/$exerciseListId');
  static String deleteExerciseDefinitionEndpoint(String exerciseListId) => buildEndpoint('/exercises/definitions/$exerciseListId');
  static String exerciseInstanceByIdEndpoint(String instanceId) => buildEndpoint('/exercises/instances/$instanceId');
  static String updateExerciseInstanceEndpoint(String instanceId) => buildEndpoint('/exercises/instances/$instanceId');
  static String deleteExerciseInstanceEndpoint(String instanceId) => buildEndpoint('/exercises/instances/$instanceId');
  static String createExerciseInstanceEndpoint(String workoutId) => buildEndpoint('/exercises/instances/workouts/$workoutId/instances');
  static String getInstancesByWorkoutEndpoint(String workoutId) => buildEndpoint('/exercises/instances/workouts/$workoutId/instances');
  static String updateExerciseSetEndpoint(String instanceId, String setId) => buildEndpoint('/exercises/instances/$instanceId/sets/$setId');
  static String deleteExerciseSetEndpoint(String instanceId, String setId) => buildEndpoint('/exercises/instances/$instanceId/sets/$setId');
  static String createExerciseInstancesBatchEndpoint() => buildEndpoint('/exercises/instances/batch');
  static String migrateSetIdsEndpoint() => buildEndpoint('/exercises/instances/migrate-set-ids');
  static String get userMaxHealthEndpoint => buildEndpoint('/user-max/health');
  static String createUserMaxEndpoint() => buildEndpoint('/user-max');
  static String getUserMaxesEndpoint() => buildEndpoint('/user-max');
  static String getByExerciseEndpoint(String exerciseId) => buildEndpoint('/user-max/by_exercise/$exerciseId');
  static String getUserMaxEndpoint(String userMaxId) => buildEndpoint('/user-max/$userMaxId');
  static String updateUserMaxEndpoint(String userMaxId) => buildEndpoint('/user-max/$userMaxId');
  static String deleteUserMaxEndpoint(String userMaxId) => buildEndpoint('/user-max/$userMaxId');
  static String calculateTrue1rmEndpoint(String userMaxId) => buildEndpoint('/user-max/$userMaxId/calculate-true-1rm');
  static String getUserMaxesByExercisesEndpoint() => buildEndpoint('/user-max/by-exercises');
  static String verify1rmEndpoint(String userMaxId) => buildEndpoint('/user-max/$userMaxId/verify');
  static String createBulkUserMaxEndpoint() => buildEndpoint('/user-max/bulk');
  static String getWeakMuscleAnalysisEndpoint({bool useLlm = true}) {
    final base = buildEndpoint('/user-max/analysis/weak-muscles');
    return useLlm ? '$base?use_llm=true' : base;
  }
  static String createWorkoutEndpoint() => buildEndpoint('/workouts');
  static String get workoutsEndpoint => buildEndpoint('/workouts/');
  static String getWorkoutsEndpoint() => buildEndpoint('/workouts');
  static String getWorkoutEndpoint(String workoutId) => buildEndpoint('/workouts/$workoutId');
  static String updateWorkoutEndpoint(String workoutId) => buildEndpoint('/workouts/$workoutId');
  static String deleteWorkoutEndpoint(String workoutId) => buildEndpoint('/workouts/$workoutId');
  static String createWorkoutsBatchEndpoint() => buildEndpoint('/workouts/batch');
  static String startWorkoutSessionEndpoint(String workoutId) => buildEndpoint('/workouts/sessions/$workoutId/start');
  static String getActiveSessionEndpoint(String workoutId) => buildEndpoint('/workouts/sessions/$workoutId/active');
  static String getSessionHistoryEndpoint(String workoutId) => buildEndpoint('/workouts/sessions/$workoutId/history');
  static String getAllSessionsHistoryEndpoint() => buildEndpoint('/workouts/sessions/history/all');
  static String finishSessionEndpoint(String sessionId) => buildEndpoint('/workouts/sessions/$sessionId/finish');
  // BFF endpoints (gateway) for starting/finishing a workout and returning aggregated workout
  static String startWorkoutBffEndpoint(String workoutId) => buildEndpoint('/workouts/$workoutId/start');
  static String finishWorkoutBffEndpoint(String workoutId) => buildEndpoint('/workouts/$workoutId/finish');
  static String generateWorkoutsEndpoint() => buildEndpoint('/workouts/workout-generation/generate');
  static String get rootEndpoint => buildEndpoint('/');
  static String get rpeTableEndpoint => buildEndpoint('/rpe/table');
  static String computeRpeSetEndpoint() => buildEndpoint('/rpe/compute');
  static String applyPlanEndpoint(String planId) => buildEndpoint('/plans/applied-plans/apply/$planId');
  static String getUserAppliedPlansEndpoint() => buildEndpoint('/plans/applied-plans/user');
  static String getAppliedPlanDetailsEndpoint(String planId) => buildEndpoint('/plans/applied-plans/$planId');
  static String getAppliedPlansEndpoint() => buildEndpoint('/plans/applied-plans');
  static String getAllPlansEndpoint() => buildEndpoint('/plans/calendar-plans');
  static String createCalendarPlanEndpoint() => buildEndpoint('/plans/calendar-plans');
  static String getFavoritePlansEndpoint() => buildEndpoint('/plans/calendar-plans/favorites');
  static String get calendarPlansEndpoint => buildEndpoint('/plans/calendar-plans');
  static String getCalendarPlanEndpoint(String planId) => buildEndpoint('/plans/calendar-plans/$planId');
  static String updateCalendarPlanEndpoint(String planId) => buildEndpoint('/plans/calendar-plans/$planId');
  static String deleteCalendarPlanEndpoint(String planId) => buildEndpoint('/plans/calendar-plans/$planId');
  static String getPlanWorkoutsEndpoint(String planId) => buildEndpoint('/plans/calendar-plans/$planId/workouts');
  static String addFavoritePlanEndpoint(String planId) => buildEndpoint('/plans/calendar-plans/$planId/favorite');
  static String removeFavoritePlanEndpoint(String planId) => buildEndpoint('/plans/calendar-plans/$planId/favorite');
  static String listMesocyclesEndpoint(String planId) => buildEndpoint('/plans/mesocycles/$planId/mesocycles');
  static String createMesocycleEndpoint(String planId) => buildEndpoint('/plans/mesocycles/$planId/mesocycles');
  static String updateMesocycleEndpoint(String mesocycleId) => buildEndpoint('/plans/mesocycles/$mesocycleId');
  static String deleteMesocycleEndpoint(String mesocycleId) => buildEndpoint('/plans/mesocycles/$mesocycleId');
  static String listMicrocyclesEndpoint(String mesocycleId) => buildEndpoint('/plans/mesocycles/$mesocycleId/microcycles');
  static String createMicrocycleEndpoint(String mesocycleId) => buildEndpoint('/plans/mesocycles/$mesocycleId/microcycles');
  static String getMicrocycleEndpoint(String mesocycleId, String microcycleId) => buildEndpoint('/plans/mesocycles/$mesocycleId/microcycles/$microcycleId');
  static String updateMicrocycleEndpoint(String microcycleId) => buildEndpoint('/plans/mesocycles/microcycles/$microcycleId');
  static String deleteMicrocycleEndpoint(String microcycleId) => buildEndpoint('/plans/mesocycles/microcycles/$microcycleId');
  static String userMaxesByExerciseEndpoint(String exerciseId) => getByExerciseEndpoint(exerciseId);
  static String sessionSetCompletionEndpoint(String sessionId, String instanceId, String setId) => buildEndpoint('/workouts/sessions/$sessionId/instances/$instanceId/sets/$setId/completion');
  static String workoutsEndpointWithPagination(int skip, int limit) => "${buildEndpoint('/workouts/')}?skip=$skip&limit=$limit";

  // New endpoints for workout filtering
  static String workoutsByTypeEndpoint(String type) => "${buildEndpoint('/workouts/')}?type=$type";
  static String get firstGeneratedWorkoutEndpoint => buildEndpoint('/workouts/generated/first');
  static String get nextGeneratedWorkoutEndpoint => buildEndpoint('/workouts/generated/next');
  static String nextWorkoutInPlanEndpoint(String workoutId) => buildEndpoint('/workouts/$workoutId/next');

  static String get getActivePlanEndpoint => buildEndpoint('plans/applied-plans/active');

  static String get activePlanEndpoint => buildEndpoint('plans/applied-plans/active');
  static String get activePlanWorkoutsEndpoint => buildEndpoint('$activePlanEndpoint/workouts');
  static String nextWorkoutInActivePlanEndpoint(String planId) => 
      buildEndpoint('/plans/$planId/next-workout');

  // Chat endpoint
  static String get chatEndpoint => buildEndpoint('/chat');

  // Progression Templates endpoints
  static String get progressionTemplatesEndpoint => buildEndpoint('/progressions/templates');
  static String progressionTemplateByIdEndpoint(String id) => buildEndpoint('/progressions/templates/$id');

  // Analytics endpoint
  static String get workoutMetricsEndpoint => buildEndpoint('/workout-metrics');
  static String get profileAggregatesEndpoint => buildEndpoint('/profile/aggregates');

  static void logApiError(http.Response response) {
    print('API Error: ${response.statusCode}');
    print('URL: ${response.request?.url}');
    print('Body: ${response.body}');
  }
}
