class ApiConfig {
  // Base URLs (ensure no trailing slashes)
  static const String androidEmulatorBaseUrl = 'http://10.0.2.2:8010';
  static const String localBaseUrl = 'http://localhost:8010';
  static const String productionBaseUrl = 'https://yourproductionapi.com';
  
  // Timeouts
  static const int connectionTimeout = 30;
  static const int receiveTimeout = 30;
  
  // API Version
  static const String apiVersion = 'v1';
  
  // API Base Path
  static const String apiBasePath = 'api';
  
  /// Returns the base URL for API requests
  static String getBaseUrl() => localBaseUrl;
  
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
  static String get healthEndpoint => buildEndpoint('/health');

  // Workout Endpoints
  static String get workoutsEndpoint => buildEndpoint('/workouts');
  static String createWorkoutEndpoint() => buildEndpoint('/workouts/');
  static String workoutByIdEndpoint(String workoutId) => 
      buildEndpoint('/workouts/$workoutId');
  static String workoutCalendarEndpoint(String workoutId) => 
      buildEndpoint('/workouts/$workoutId/calendar');
  static String exerciseInstancesByWorkoutEndpoint(String workoutId) =>
      buildEndpoint('/exercises/workouts/$workoutId/instances');
  static String exerciseInstanceByIdEndpoint(String instanceId) =>
      buildEndpoint('/exercises/instances/$instanceId');
  static String deleteExerciseInstanceEndpoint(String instanceId) =>
      buildEndpoint('/exercises/instances/$instanceId');

  // Exercise Definition Endpoints
  static String get exerciseDefinitionsEndpoint => buildEndpoint('/exercises/list');
  static String exerciseDefinitionByIdEndpoint(String id) => 
      buildEndpoint('/exercises/list/$id');

  // Muscles (enum + labels) Endpoint
  static String get musclesEndpoint => buildEndpoint('/exercises/muscles');

  // Exercise Instance Endpoints
  static String get exerciseInstancesEndpoint => buildEndpoint('/exercise-instances');
  static String exerciseInstanceByWorkoutEndpoint(String workoutId) => 
      buildEndpoint('/exercises/workouts/$workoutId/instances');
  static String updateExerciseInstanceEndpoint(String instanceId) => 
      buildEndpoint('/exercises/instances/$instanceId');
  // Helper for deleting a specific set within an instance
  static String exerciseSetByIdEndpoint(String instanceId, String setId) => 
      buildEndpoint('/exercises/instances/$instanceId/sets/$setId');

  // User Max Endpoints
  static String get userMaxesEndpoint => buildEndpoint('/user-max');
  static String userMaxByIdEndpoint(String maxId) => 
      buildEndpoint('/user-max/$maxId');
  static String userMaxesByExerciseEndpoint(String exerciseId) => 
      buildEndpoint('/user-max/by_exercise/$exerciseId');

  // Progression Template Endpoints
  static String get progressionTemplatesEndpoint => 
      buildEndpoint('/progression-templates');
  static String progressionTemplateByIdEndpoint(String templateId) => 
      buildEndpoint('/progression-templates/$templateId');
  static String progressionTemplateExercisesEndpoint(String templateId) => 
      buildEndpoint('/progression-templates/$templateId/exercises');

  // Calendar Plan Endpoints
  static String get calendarPlansEndpoint => buildEndpoint('/calendar-plans');
  static String calendarPlanByIdEndpoint(String planId) => 
      buildEndpoint('/calendar-plans/$planId');
  static String calendarPlanWorkoutsEndpoint(String planId) => 
      buildEndpoint('/calendar-plans/$planId/workouts');
  // Calendar Plan Favorites
  static String get calendarPlanFavoritesEndpoint => buildEndpoint('/calendar-plans/favorites');
  static String calendarPlanFavoriteByIdEndpoint(String planId) =>
      buildEndpoint('/calendar-plans/$planId/favorite');

  // Calendar Plan Instances
  static String get calendarPlanInstancesEndpoint => buildEndpoint('/calendar-plan-instances');
  static String calendarPlanInstanceByIdEndpoint(String id) => buildEndpoint('/calendar-plan-instances/$id');
  static String createInstanceFromPlanEndpoint(String planId) => buildEndpoint('/calendar-plan-instances/from-plan/$planId');
  static String applyFromInstanceEndpoint(String instanceId) =>
      buildEndpoint('/calendar-plan-instances/$instanceId/apply');
      
  // Applied Calendar Plan Endpoints
  static String get appliedCalendarPlansEndpoint => buildEndpoint('/applied-calendar-plans');
  static String applyCalendarPlanEndpoint(String planId) => 
      buildEndpoint('/applied-calendar-plans/apply/$planId');
  static String get activeAppliedCalendarPlanEndpoint => 
      buildEndpoint('/applied-calendar-plans/active');
  static String get userAppliedCalendarPlansEndpoint =>
      buildEndpoint('/applied-calendar-plans/user');
  static String appliedCalendarPlanEndpoint(String planId) =>
      buildEndpoint('/applied-calendar-plans/user/$planId');
  static String appliedCalendarPlanByIdEndpoint(String planId) => 
      buildEndpoint('/applied-calendar-plans/$planId');

  // Mesocycle & Microcycle Endpoints
  // Mesocycles under a calendar plan
  static String calendarPlanMesocyclesEndpoint(String planId) =>
      buildEndpoint('/calendar-plans/$planId/mesocycles');
  // Single mesocycle by ID
  static String mesocycleByIdEndpoint(String mesocycleId) =>
      buildEndpoint('/mesocycles/$mesocycleId');
  // Microcycles under a mesocycle
  static String mesocycleMicrocyclesEndpoint(String mesocycleId) =>
      buildEndpoint('/mesocycles/$mesocycleId/microcycles');
  // Single microcycle by ID
  static String microcycleByIdEndpoint(String microcycleId) =>
      buildEndpoint('/microcycles/$microcycleId');

  // Workout Session Endpoints
  static String startWorkoutSessionEndpoint(String workoutId) =>
      buildEndpoint('/workouts/$workoutId/start');
  static String activeWorkoutSessionEndpoint(String workoutId) =>
      buildEndpoint('/workouts/$workoutId/active');
  static String workoutSessionHistoryEndpoint(String workoutId) =>
      buildEndpoint('/workouts/$workoutId/history');
  static String sessionSetCompletionEndpoint(
    String sessionId,
    String instanceId,
    String setId,
  ) => buildEndpoint('/sessions/$sessionId/instances/$instanceId/sets/$setId');
  static String finishSessionEndpoint(String sessionId) =>
      buildEndpoint('/sessions/$sessionId/finish');

  // Utils
  static String get rpeEndpoint => buildEndpoint('/rpe');

  // Accounts-service endpoints (proxied via gateway)
  static String get accountsBase => buildEndpoint('/accounts');
  // Me
  static String get accountsMe => buildEndpoint('/accounts/me');
  // Clients
  static String get accountsClients => buildEndpoint('/accounts/clients');
  // Notes
  static String accountsClientNotes(String clientUserId) => buildEndpoint('/accounts/clients/$clientUserId/notes');
  static String accountsNoteById(String noteId) => buildEndpoint('/accounts/notes/$noteId');
  // Tags
  static String get accountsTags => buildEndpoint('/accounts/tags');
  static String accountsClientTags(String clientUserId) => buildEndpoint('/accounts/clients/$clientUserId/tags');
  static String accountsClientTagById(String clientUserId, String tagId) => buildEndpoint('/accounts/clients/$clientUserId/tags/$tagId');
}
