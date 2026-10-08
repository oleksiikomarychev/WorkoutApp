import 'package:flutter/foundation.dart'
    show kIsWeb, defaultTargetPlatform, TargetPlatform, kReleaseMode;
import 'dart:io' show Platform;
import 'package:http/http.dart' as http;
import 'package:flutter_dotenv/flutter_dotenv.dart';

class ApiConfig {
  static bool useProd = false;

  static String get localBaseUrl {
    // 1. Если это Web, жестко возвращаем localhost
    if (kIsWeb) {
      return 'http://127.0.0.1:8000';
    }

    // 2. Если это не Web, пробуем взять из .env, если нет - дефолтный IP
    return dotenv.maybeGet('LOCAL_API_BASE_URL') ?? 'http://192.168.31.75:8000';
  }

  static final String productionBaseUrl =
      dotenv.maybeGet('PROD_API_BASE_URL') ?? 'http://46.62.207.163:8000';

  static const int connectionTimeout = 60;
  static const int receiveTimeout = 60;
  static const String apiVersion = 'v1';
  static const String apiBasePath = 'api';

  static String getBaseUrl() {
    return useProd ? productionBaseUrl : localBaseUrl;
  }

  static String get baseUrl => getBaseUrl();

  static String buildEndpoint(String path) {
    final cleanPath = path.startsWith('/') ? path.substring(1) : path;
    return '$apiBasePath/$apiVersion/$cleanPath';
  }

  static String buildFullUrl(String path) {
    final baseUrl = getBaseUrl().endsWith('/')
        ? getBaseUrl().substring(0, getBaseUrl().length - 1)
        : getBaseUrl();
    final cleanPath = path.startsWith('/') ? path.substring(1) : path;
    return '$baseUrl/$cleanPath';
  }

  static String get rpeHealthEndpoint => buildEndpoint('/rpe/health');
  static String get healthEndpoint => buildEndpoint('/health');
  static String get exercisesHealthEndpoint =>
      buildEndpoint('/exercises/health');
  static String get musclesEndpoint => buildEndpoint('/exercises/muscles');
  static String get exerciseDefinitionsEndpoint =>
      buildEndpoint('/exercises/definitions');
  static String createExerciseDefinitionEndpoint() =>
      buildEndpoint('/exercises/definitions');
  static String exerciseDefinitionByIdEndpoint(String exerciseListId) =>
      buildEndpoint('/exercises/definitions/$exerciseListId');
  static String updateExerciseDefinitionEndpoint(String exerciseListId) =>
      buildEndpoint('/exercises/definitions/$exerciseListId');
  static String deleteExerciseDefinitionEndpoint(String exerciseListId) =>
      buildEndpoint('/exercises/definitions/$exerciseListId');
  static String uploadExerciseImageEndpoint(String exerciseListId) =>
      buildEndpoint('/exercises/definitions/$exerciseListId/media/image');
  static String uploadExerciseGifEndpoint(String exerciseListId) =>
      buildEndpoint('/exercises/definitions/$exerciseListId/media/gif');
  static String exerciseInstanceByIdEndpoint(String instanceId) =>
      buildEndpoint('/exercises/instances/$instanceId');
  static String updateExerciseInstanceEndpoint(String instanceId) =>
      buildEndpoint('/exercises/instances/$instanceId');
  static String deleteExerciseInstanceEndpoint(String instanceId) =>
      buildEndpoint('/exercises/instances/$instanceId');
  static String createExerciseInstanceEndpoint(String workoutId) =>
      buildEndpoint('/exercises/instances/workouts/$workoutId/instances');
  static String getInstancesByWorkoutEndpoint(String workoutId) =>
      buildEndpoint('/exercises/instances/workouts/$workoutId/instances');
  static String updateExerciseSetEndpoint(String instanceId, String setId) =>
      buildEndpoint('/exercises/instances/$instanceId/sets/$setId');
  static String deleteExerciseSetEndpoint(String instanceId, String setId) =>
      buildEndpoint('/exercises/instances/$instanceId/sets/$setId');
  static String createExerciseInstancesBatchEndpoint() =>
      buildEndpoint('/exercises/instances/batch');
  static String migrateSetIdsEndpoint() =>
      buildEndpoint('/exercises/instances/migrate-set-ids');
  static String get userMaxHealthEndpoint => buildEndpoint('/user-max/health');
  static String createUserMaxEndpoint() => buildEndpoint('/user-max');
  static String getUserMaxesEndpoint() => buildEndpoint('/user-max');
  static String getByExerciseEndpoint(String exerciseId) =>
      buildEndpoint('/user-max/by_exercise/$exerciseId');
  static String getUserMaxEndpoint(String userMaxId) =>
      buildEndpoint('/user-max/$userMaxId');
  static String updateUserMaxEndpoint(String userMaxId) =>
      buildEndpoint('/user-max/$userMaxId');
  static String deleteUserMaxEndpoint(String userMaxId) =>
      buildEndpoint('/user-max/$userMaxId');
  static String calculateTrue1rmEndpoint(String userMaxId) =>
      buildEndpoint('/user-max/$userMaxId/calculate-true-1rm');
  static String getUserMaxesByExercisesEndpoint() =>
      buildEndpoint('/user-max/by-exercises');
  static String verify1rmEndpoint(String userMaxId) =>
      buildEndpoint('/user-max/$userMaxId/verify');
  static String createBulkUserMaxEndpoint() => buildEndpoint('/user-max/bulk');
  static String getWeakMuscleAnalysisEndpoint({bool useLlm = true}) {
    final base = buildEndpoint('/user-max/analysis/weak-muscles');
    return useLlm ? '$base?use_llm=true' : base;
  }

  static String get workoutsAnalyticsHistoryEndpoint =>
      buildEndpoint('/workouts/analytics/history');
  static String createWorkoutEndpoint() => buildEndpoint('/workouts');
  static String get workoutsEndpoint => buildEndpoint('/workouts/');
  static String getWorkoutsEndpoint() => buildEndpoint('/workouts');
  static String getWorkoutEndpoint(String workoutId) =>
      buildEndpoint('/workouts/$workoutId');
  static String updateWorkoutEndpoint(String workoutId) =>
      buildEndpoint('/workouts/$workoutId');
  static String deleteWorkoutEndpoint(String workoutId) =>
      buildEndpoint('/workouts/$workoutId');
  static String createWorkoutsBatchEndpoint() =>
      buildEndpoint('/workouts/batch');
  static String startWorkoutSessionEndpoint(String workoutId) =>
      buildEndpoint('/workouts/sessions/$workoutId/start');
  static String getActiveSessionEndpoint(String workoutId) =>
      buildEndpoint('/workouts/sessions/$workoutId/active');
  static String getSessionHistoryEndpoint(String workoutId) =>
      buildEndpoint('/workouts/sessions/$workoutId/history');
  static String getAllSessionsHistoryEndpoint() =>
      buildEndpoint('/workouts/sessions/history/all');
  static String finishSessionEndpoint(String sessionId) =>
      buildEndpoint('/workouts/sessions/$sessionId/finish');

  static String startWorkoutBffEndpoint(String workoutId) =>
      buildEndpoint('/workouts/$workoutId/start');
  static String finishWorkoutBffEndpoint(String workoutId) =>
      buildEndpoint('/workouts/$workoutId/finish');
  static String generateWorkoutsEndpoint() =>
      buildEndpoint('/workouts/workout-generation/generate');
  static String get rootEndpoint => buildEndpoint('/');
  static String get rpeTableEndpoint => buildEndpoint('/rpe/table');
  static String computeRpeSetEndpoint() => buildEndpoint('/rpe/compute');
  static String applyPlanEndpoint(String planId) =>
      buildEndpoint('/plans/applied-plans/apply/$planId');
  static String applyPlanAsyncEndpoint(String planId) =>
      buildEndpoint('/plans/applied-plans/apply-async/$planId');
  static String plansTaskStatusEndpoint(String taskId) =>
      buildEndpoint('/plans/applied-plans/tasks/$taskId');
  static String getUserAppliedPlansEndpoint() =>
      buildEndpoint('/plans/applied-plans/user');
  static String getAppliedPlanDetailsEndpoint(String planId) =>
      buildEndpoint('/plans/applied-plans/$planId');
  static String getAppliedPlansEndpoint() =>
      buildEndpoint('/plans/applied-plans');
  static String advanceAppliedPlanIndexEndpoint(String appliedPlanId) =>
      buildEndpoint('/plans/applied-plans/$appliedPlanId/advance-index');
  static String getAllPlansEndpoint() => buildEndpoint('/plans/calendar-plans');
  static String createCalendarPlanEndpoint() =>
      buildEndpoint('/plans/calendar-plans');
  static String getFavoritePlansEndpoint() =>
      buildEndpoint('/plans/calendar-plans/favorites');
  static String get calendarPlansEndpoint =>
      buildEndpoint('/plans/calendar-plans');
  static String getCalendarPlanEndpoint(String planId) =>
      buildEndpoint('/plans/calendar-plans/$planId');
  static String updateCalendarPlanEndpoint(String planId) =>
      buildEndpoint('/plans/calendar-plans/$planId');
  static String deleteCalendarPlanEndpoint(String planId) =>
      buildEndpoint('/plans/calendar-plans/$planId');

  static String listMacrosEndpoint(String planId) =>
      buildEndpoint('/plans/calendar-plans/$planId/macros');
  static String createMacroEndpoint(String planId) =>
      buildEndpoint('/plans/calendar-plans/$planId/macros');
  static String updateMacroEndpoint(String planId, String macroId) =>
      buildEndpoint('/plans/calendar-plans/$planId/macros/$macroId');
  static String deleteMacroEndpoint(String planId, String macroId) =>
      buildEndpoint('/plans/calendar-plans/$planId/macros/$macroId');
  static String runMacrosEndpoint(String appliedPlanId) =>
      buildEndpoint('/plans/applied-plans/$appliedPlanId/run-macros');
  static String applyMacrosEndpoint(String appliedPlanId) =>
      buildEndpoint('/plans/applied-plans/$appliedPlanId/apply-macros');
  static String cancelAppliedPlanEndpoint(String appliedPlanId) =>
      buildEndpoint('/plans/applied-plans/$appliedPlanId/cancel');
  static String getPlanWorkoutsEndpoint(String planId) =>
      buildEndpoint('/plans/calendar-plans/$planId/workouts');
  static String listPlanVariantsEndpoint(String planId) =>
      buildEndpoint('/plans/calendar-plans/$planId/variants');
  static String createPlanVariantEndpoint(String planId) =>
      buildEndpoint('/plans/calendar-plans/$planId/variants');
  static String addFavoritePlanEndpoint(String planId) =>
      buildEndpoint('/plans/calendar-plans/$planId/favorite');
  static String removeFavoritePlanEndpoint(String planId) =>
      buildEndpoint('/plans/calendar-plans/$planId/favorite');
  static String recalcCalendarPlanSetsEndpoint(String planId) =>
      buildEndpoint('/plans/calendar-plans/$planId/recalc-sets');
  static String rootPlanAdoptersStatsEndpoint(String rootPlanId) =>
      buildEndpoint('/plans/adoption/root-plans/$rootPlanId/stats');
  static String listMesocyclesEndpoint(String planId) =>
      buildEndpoint('/plans/mesocycles/$planId/mesocycles');
  static String createMesocycleEndpoint(String planId) =>
      buildEndpoint('/plans/mesocycles/$planId/mesocycles');
  static String updateMesocycleEndpoint(String mesocycleId) =>
      buildEndpoint('/plans/mesocycles/$mesocycleId');
  static String deleteMesocycleEndpoint(String mesocycleId) =>
      buildEndpoint('/plans/mesocycles/$mesocycleId');
  static String listMicrocyclesEndpoint(String mesocycleId) =>
      buildEndpoint('/plans/mesocycles/$mesocycleId/microcycles');
  static String createMicrocycleEndpoint(String mesocycleId) =>
      buildEndpoint('/plans/mesocycles/$mesocycleId/microcycles');
  static String getMicrocycleEndpoint(
    String mesocycleId,
    String microcycleId,
  ) =>
      buildEndpoint('/plans/mesocycles/$mesocycleId/microcycles/$microcycleId');
  static String updateMicrocycleEndpoint(String microcycleId) =>
      buildEndpoint('/plans/mesocycles/microcycles/$microcycleId');
  static String deleteMicrocycleEndpoint(String microcycleId) =>
      buildEndpoint('/plans/mesocycles/microcycles/$microcycleId');
  static String validateMicrocyclesEndpoint() =>
      buildEndpoint('/plans/mesocycles/validate');
  static String userMaxesByExerciseEndpoint(String exerciseId) =>
      getByExerciseEndpoint(exerciseId);
  static String sessionSetCompletionEndpoint(
    String sessionId,
    String instanceId,
    String setId,
  ) => buildEndpoint(
    '/workouts/sessions/$sessionId/instances/$instanceId/sets/$setId/completion',
  );
  static String sessionCompleteAllEndpoint(String sessionId) =>
      buildEndpoint('/workouts/sessions/$sessionId/complete-all');
  static String workoutsEndpointWithPagination(int skip, int limit) =>
      "${buildEndpoint('/workouts/')}?skip=$skip&limit=$limit";

  static String workoutsByTypeEndpoint(String type) =>
      "${buildEndpoint('/workouts/')}?type=$type";
  static String get firstGeneratedWorkoutEndpoint =>
      buildEndpoint('/workouts/generated/first');
  static String get nextGeneratedWorkoutEndpoint =>
      buildEndpoint('/workouts/generated/next');
  static String nextWorkoutInPlanEndpoint(String workoutId) =>
      buildEndpoint('/workouts/$workoutId/next');

  static String get getActivePlanEndpoint =>
      buildEndpoint('plans/applied-plans/active');

  static String get activePlanEndpoint =>
      buildEndpoint('plans/applied-plans/active');
  static String get activePlanWorkoutsEndpoint =>
      buildEndpoint('plans/applied-plans/active/workouts');
  static String nextWorkoutInActivePlanEndpoint(String planId) =>
      buildEndpoint('/plans/$planId/next-workout');
  static String appliedPlanAnalyticsEndpoint(String planId) =>
      buildEndpoint('/plans/applied-plans/$planId/analytics');

  static String get chatEndpoint => buildEndpoint('/chat');
  static String get agentAppliedPlanMassEditEndpoint =>
      buildEndpoint('/agent/applied-plan-mass-edit');
  static String agentMassEditTaskStatusEndpoint(String taskId) =>
      buildEndpoint('/agent/plan-mass-edit/tasks/$taskId');

  static String get socialPostsEndpoint => buildEndpoint('/social/posts');
  static String socialPostCommentsEndpoint(String postId) =>
      buildEndpoint('/social/posts/$postId/comments');
  static String socialPostReactionsEndpoint(String postId) =>
      buildEndpoint('/social/posts/$postId/reactions');

  static String get messagingChannelsEndpoint =>
      buildEndpoint('/messaging/channels');
  static String messagingChannelMessagesEndpoint(String channelId) =>
      buildEndpoint('/messaging/channels/$channelId/messages');

  static String get progressionTemplatesEndpoint =>
      buildEndpoint('/progressions/templates');
  static String progressionTemplateByIdEndpoint(String id) =>
      buildEndpoint('/progressions/templates/$id');

  static String get workoutMetricsEndpoint => buildEndpoint('/workout-metrics');
  static String get profileAggregatesEndpoint =>
      buildEndpoint('/profile/aggregates');
  static String get profileMeEndpoint => buildEndpoint('/profile/me');
  static String profileByIdEndpoint(String userId) =>
      buildEndpoint('/profile/$userId');
  static String get profileMeCoachingEndpoint =>
      buildEndpoint('/profile/me/coaching');
  static String get profileMeStripeConnectOnboardingEndpoint =>
      buildEndpoint('/profile/me/stripe/connect/onboarding-link');
  static String get profileSettingsEndpoint =>
      buildEndpoint('/profile/settings');
  static String get usersAllEndpoint => buildEndpoint('/users/all');

  static String get accountPurgeEndpoint => buildEndpoint('/account/purge');
  static String get accountUsersEndpoint => buildEndpoint('/account/users');

  static String get avatarsGenerateEndpoint =>
      buildEndpoint('/avatars/generate');
  static String get applyProfilePhotoEndpoint =>
      buildEndpoint('/profile/photo/apply');

  static String get mesocycleTemplatesEndpoint =>
      buildEndpoint('/plans/mesocycle-templates');
  static String mesocycleTemplateByIdEndpoint(String id) =>
      buildEndpoint('/plans/mesocycle-templates/$id');

  static String get crmMyRelationshipsEndpoint =>
      buildEndpoint('/crm/relationships/my/athletes');
  static String get crmMyCoachesEndpoint =>
      buildEndpoint('/crm/relationships/my/coaches');
  static String get crmRelationshipsEndpoint =>
      buildEndpoint('/crm/relationships');
  static String crmRelationshipStatusEndpoint(String id) =>
      buildEndpoint('/crm/relationships/$id/status');

  static String crmCoachActivePlanEndpoint(String athleteId) =>
      buildEndpoint('/crm/coach/athletes/$athleteId/active-plan');
  static String crmCoachActivePlanWorkoutsEndpoint(String athleteId) =>
      buildEndpoint('/crm/coach/athletes/$athleteId/active-plan/workouts');
  static String crmCoachActivePlanAnalyticsEndpoint(String athleteId) =>
      buildEndpoint('/crm/coach/athletes/$athleteId/active-plan/analytics');
  static String crmCoachWorkoutEndpoint(String athleteId, int workoutId) =>
      buildEndpoint('/crm/coach/athletes/$athleteId/workouts/$workoutId');
  static String crmCoachWorkoutExercisesEndpoint(
    String athleteId,
    int workoutId,
  ) => buildEndpoint(
    '/crm/coach/athletes/$athleteId/workouts/$workoutId/exercises',
  );
  static String crmCoachExerciseEndpoint(String athleteId, int instanceId) =>
      buildEndpoint('/crm/coach/athletes/$athleteId/exercises/$instanceId');
  static String crmCoachMassEditEndpoint(String athleteId) =>
      buildEndpoint('/crm/coach/athletes/$athleteId/workouts/mass-edit');
  static String crmBillingSubscriptionEndpoint(int linkId) =>
      buildEndpoint('/crm/billing/links/$linkId/subscription');
  static String crmBillingCheckoutSessionEndpoint(int linkId) =>
      buildEndpoint('/crm/billing/links/$linkId/checkout-session');

  static String get crmAnalyticsMyAthletesEndpoint =>
      buildEndpoint('/crm/analytics/coaches/my/athletes');
  static String get crmAnalyticsMySummaryEndpoint =>
      buildEndpoint('/crm/analytics/coaches/my/summary');
  static String crmAnalyticsAthleteEndpoint(String athleteId) =>
      buildEndpoint('/crm/analytics/athletes/$athleteId');

  static String crmReviewsCreateEndpoint(int linkId) =>
      buildEndpoint('/crm/reviews/links/$linkId/reviews');
  static String crmReviewsCoachEndpoint(String coachId) =>
      buildEndpoint('/crm/reviews/coaches/$coachId/reviews');

  static String replaceExerciseIdEndpoint(int workoutId) =>
      buildEndpoint('/workouts/$workoutId/exercises/replace');

  static String get importHevyCsvEndpoint =>
      buildEndpoint('/workouts/import/hevy');
  static String importHevyTaskStatusEndpoint(String taskId) =>
      buildEndpoint('/workouts/import/hevy/tasks/$taskId');

  static String createFoodEndpoint() =>
      buildEndpoint('/workouts/supplements/food');
  static String getFoodEndpoint(int foodId) =>
      buildEndpoint('/workouts/supplements/food/$foodId');
  static String getAllFoodEndpoint() =>
      buildEndpoint('/workouts/supplements/food');
  static String updateFoodEndpoint(int foodId) =>
      buildEndpoint('/workouts/supplements/food/$foodId');
  static String deleteFoodEndpoint(int foodId) =>
      buildEndpoint('/workouts/supplements/food/$foodId');

  static String createSupplementEndpoint() =>
      buildEndpoint('/workouts/supplements/supplement');
  static String getSupplementEndpoint(int supplementId) =>
      buildEndpoint('/workouts/supplements/supplement/$supplementId');
  static String getAllSupplementsEndpoint() =>
      buildEndpoint('/workouts/supplements/supplement');
  static String updateSupplementEndpoint(int supplementId) =>
      buildEndpoint('/workouts/supplements/supplement/$supplementId');
  static String deleteSupplementEndpoint(int supplementId) =>
      buildEndpoint('/workouts/supplements/supplement/$supplementId');

  static String createMedicationEndpoint() =>
      buildEndpoint('/workouts/supplements/medication');
  static String getMedicationEndpoint(int medicationId) =>
      buildEndpoint('/workouts/supplements/medication/$medicationId');
  static String getAllMedicationsEndpoint() =>
      buildEndpoint('/workouts/supplements/medication');
  static String updateMedicationEndpoint(int medicationId) =>
      buildEndpoint('/workouts/supplements/medication/$medicationId');
  static String deleteMedicationEndpoint(int medicationId) =>
      buildEndpoint('/workouts/supplements/medication/$medicationId');

  static String createSessionEndpoint() =>
      buildEndpoint('/workouts/supplements/session');
  static String getSessionEndpoint(String sessionId) =>
      buildEndpoint('/workouts/supplements/session/$sessionId');
  static String getSessionByUserIdEndpoint(int userId) =>
      buildEndpoint('/workouts/supplements/session/user/$userId');
  static String getSessionByWorkoutIdEndpoint(int workoutId) =>
      buildEndpoint('/workouts/supplements/session/workout/$workoutId');
  static String getSessionByAppliedPlanWorkoutIdEndpoint(
    int appliedPlanWorkoutId,
  ) => buildEndpoint(
    '/workouts/supplements/session/applied-plan-workout/$appliedPlanWorkoutId',
  );
  static String getAllSessionsEndpoint() =>
      buildEndpoint('/workouts/supplements/session');
  static String updateSessionEndpoint(String sessionId) =>
      buildEndpoint('/workouts/supplements/session/$sessionId');
  static String deleteSessionEndpoint(String sessionId) =>
      buildEndpoint('/workouts/supplements/session/$sessionId');

  static void logApiError(http.Response response) {
    print('API Error: ${response.statusCode}');
    print('URL: ${response.request?.url}');
    print('Body: ${response.body}');
  }
}
