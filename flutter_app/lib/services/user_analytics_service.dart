import 'dart:convert';
import 'package:flutter_dotenv/flutter_dotenv.dart';
import 'package:http/http.dart' as http;
import 'package:workout_app/services/logger_service.dart';

class UserAnalyticsService {
  static UserAnalyticsService? _instance;
  final LoggerService _logger = LoggerService('UserAnalyticsService');
  final String _baseUrl = 'https://api2.amplitude.com/2/httpapi';

  static UserAnalyticsService get instance {
    _instance ??= UserAnalyticsService._();
    return _instance!;
  }

  UserAnalyticsService._();

  Future<bool> _sendEvent(
    String eventType,
    Map<String, dynamic> eventProperties,
  ) async {
    try {
      final apiKey = dotenv.env['AMPLITUDE_API_KEY'];
      if (apiKey == null || apiKey.isEmpty) {
        _logger.w('Amplitude API key not found, skipping event tracking');
        return false;
      }

      final event = {
        'user_id': 'flutter_user_${DateTime.now().millisecondsSinceEpoch}',
        'event_type': eventType,
        'event_properties': eventProperties,
        'time': DateTime.now().millisecondsSinceEpoch,
        'platform': 'Flutter Web',
        'app_version': '1.0.0',
      };

      _logger.i('Sending event: $eventType with properties: $eventProperties');

      try {
        final response = await http
            .post(
              Uri.parse(_baseUrl),
              headers: {'Content-Type': 'application/json', 'Accept': '*/*'},
              body: jsonEncode({
                'api_key': apiKey,
                'events': [event],
              }),
            )
            .timeout(
              const Duration(seconds: 3),
              onTimeout: () {
                _logger.w('Request timeout for event: $eventType');
                throw http.ClientException('Request timeout');
              },
            );

        if (response.statusCode == 200) {
          _logger.i('✅ Event tracked successfully: $eventType');
          return true;
        } else {
          _logger.e(
            '❌ Failed to track event $eventType: ${response.statusCode} - ${response.body}',
          );
          // Fallback: log to console for development
          _logger.i(
            '📊 [FALLBACK] Event would be sent: $eventType | $eventProperties',
          );
          return false;
        }
      } on http.ClientException catch (e) {
        _logger.e('❌ Network error for event $eventType: $e');
        // Fallback: log to console for development
        _logger.i(
          '📊 [FALLBACK] Event would be sent: $eventType | $eventProperties',
        );
        return false;
      } catch (e) {
        _logger.e('❌ Unexpected error for event $eventType: $e');
        // Fallback: log to console for development
        _logger.i(
          '📊 [FALLBACK] Event would be sent: $eventType | $eventProperties',
        );
        return false;
      }
    } catch (e) {
      _logger.e('Failed to track event $eventType: $e');
      return false;
    }
  }

  // Трекинг открытия экранов
  Future<void> trackScreenOpen(
    String screenName, {
    Map<String, dynamic>? properties,
  }) async {
    final eventProperties = <String, dynamic>{
      'screen_name': screenName,
      'action': 'screen_open',
      ...?properties,
    };

    await _sendEvent(screenName, eventProperties);
  }

  // Трекинг действий с тренировками
  Future<void> trackWorkoutAction(
    String action,
    int? workoutId, {
    Map<String, dynamic>? properties,
  }) async {
    final eventType = 'workout_$action';
    final eventProperties = <String, dynamic>{
      if (workoutId != null) 'workout_id': workoutId,
      'action': action,
      ...?properties,
    };

    await _sendEvent(eventType, eventProperties);
  }

  // Трекинг действий с упражнениями
  Future<void> trackExerciseAction(
    String action,
    int? exerciseId, {
    Map<String, dynamic>? properties,
  }) async {
    final eventType = 'exercise_$action';
    final eventProperties = <String, dynamic>{
      if (exerciseId != null) 'exercise_id': exerciseId,
      'action': action,
      ...?properties,
    };

    await _sendEvent(eventType, eventProperties);
  }

  // Трекинг пользовательских событий
  Future<void> trackUserAction(
    String action, {
    Map<String, dynamic>? properties,
  }) async {
    final eventType = 'user_$action';
    final eventProperties = <String, dynamic>{'action': action, ...?properties};

    await _sendEvent(eventType, eventProperties);
  }

  // Трекинг ошибок
  Future<void> trackError(
    String errorType,
    String errorMessage, {
    String? context,
  }) async {
    final eventProperties = {
      'error_type': errorType,
      'error_message': errorMessage,
      if (context != null) 'context': context,
      'timestamp': DateTime.now().toIso8601String(),
    };

    await _sendEvent('error_occurred', eventProperties);
  }

  // Тестовое событие для проверки работы
  Future<void> trackTestEvent() async {
    final eventProperties = {
      'timestamp': DateTime.now().toIso8601String(),
      'app_version': '1.0.0',
      'platform': 'flutter_web',
      'test_data': 'Analytics service test event via HTTP API',
      'debug_mode': true,
    };

    _logger.i('🧪 Testing Amplitude Analytics...');
    _logger.i('📍 API Endpoint: $_baseUrl');
    _logger.i(
      '🔑 API Key: ${dotenv.env['AMPLITUDE_API_KEY']?.substring(0, 8)}...',
    );
    _logger.i('📦 Event Type: test_analytics_event');
    _logger.i('📋 Event Properties: $eventProperties');

    final success = await _sendEvent('test_analytics_event', eventProperties);

    if (success) {
      _logger.i('🎉 Test event sent successfully to Amplitude!');
    } else {
      _logger.w('⚠️ Test event failed - check console for details');
      _logger.i(
        '💡 Tip: Disable ad-blocker or check CORS settings for production',
      );
    }
  }

  // ===== Воронка первой сделки (Time-to-First-Dollar) =====

  // Шаг 1: Профиль тренера опубликован
  Future<void> trackTrainerProfilePublished({
    Map<String, dynamic>? properties,
  }) async {
    final eventProperties = <String, dynamic>{
      'funnel': 'time_to_first_dollar',
      'step': 1,
      'step_name': 'profile_published',
      'action': 'publish_trainer_profile',
      ...?properties,
    };

    await _sendEvent('trainer_profile_published', eventProperties);
  }

  // Шаг 2: Получена первая заявка/сообщение от клиента
  Future<void> trackInboundRequestReceived({
    required String requestId,
    String? clientUserId,
    Map<String, dynamic>? properties,
  }) async {
    final eventProperties = <String, dynamic>{
      'funnel': 'time_to_first_dollar',
      'step': 2,
      'step_name': 'inbound_request_received',
      'action': 'receive_first_client_request',
      'request_id': requestId,
      if (clientUserId != null) 'client_user_id': clientUserId,
      ...?properties,
    };

    await _sendEvent('inbound_request_received', eventProperties);
  }

  // Шаг 3: Тренер подтвердил работу с клиентом
  Future<void> trackBookingAccepted({
    required String bookingId,
    String? clientUserId,
    Map<String, dynamic>? properties,
  }) async {
    final eventProperties = <String, dynamic>{
      'funnel': 'time_to_first_dollar',
      'step': 3,
      'step_name': 'booking_accepted',
      'action': 'accept_first_booking',
      'booking_id': bookingId,
      if (clientUserId != null) 'client_user_id': clientUserId,
      ...?properties,
    };

    await _sendEvent('booking_accepted', eventProperties);
  }

  // Шаг 4: Деньги поступили на счет тренера (First Dollar!)
  Future<void> trackPayoutReceived({
    required String payoutId,
    required num amount,
    String? currency,
    Map<String, dynamic>? properties,
  }) async {
    final eventProperties = <String, dynamic>{
      'funnel': 'time_to_first_dollar',
      'step': 4,
      'step_name': 'payout_received',
      'action': 'receive_first_payout',
      'payout_id': payoutId,
      'amount': amount,
      'currency': currency ?? 'USD',
      'is_first_payout': true,
      ...?properties,
    };

    await _sendEvent('payout_received', eventProperties);
  }

  // Вспомогательные события для воронки

  // Клиент отправил сообщение тренеру
  Future<void> trackClientMessage({
    required String trainerUserId,
    String? clientUserId,
    Map<String, dynamic>? properties,
  }) async {
    final eventProperties = <String, dynamic>{
      'funnel': 'time_to_first_dollar',
      'step': 2,
      'step_name': 'client_message',
      'action': 'client_send_message',
      'trainer_user_id': trainerUserId,
      if (clientUserId != null) 'client_user_id': clientUserId,
      ...?properties,
    };

    await _sendEvent('client_message', eventProperties);
  }

  // Клиент отправил заявку на тренировку
  Future<void> trackBookingRequest({
    required String trainerUserId,
    String? clientUserId,
    Map<String, dynamic>? properties,
  }) async {
    final eventProperties = <String, dynamic>{
      'funnel': 'time_to_first_dollar',
      'step': 2,
      'step_name': 'booking_request',
      'action': 'client_request_booking',
      'trainer_user_id': trainerUserId,
      if (clientUserId != null) 'client_user_id': clientUserId,
      ...?properties,
    };

    await _sendEvent('booking_request', eventProperties);
  }

  // Расчет конверсии между шагами воронки
  Future<void> trackFunnelConversion({
    required String fromStep,
    required String toStep,
    Map<String, dynamic>? properties,
  }) async {
    final eventProperties = <String, dynamic>{
      'funnel': 'time_to_first_dollar',
      'action': 'funnel_conversion',
      'from_step': fromStep,
      'to_step': toStep,
      ...?properties,
    };

    await _sendEvent('funnel_conversion', eventProperties);
  }

  // ===== ENGAGEMENT METRICS FUNNELS =====

  // Plan View to Apply Rate Funnel
  Future<void> trackPlanListViewed({
    required int totalPlansCount,
    required String source,
    Map<String, dynamic>? properties,
  }) async {
    final eventProperties = <String, dynamic>{
      'funnel': 'plan_view_to_apply_rate',
      'step': 1,
      'step_name': 'plan_list_viewed',
      'total_plans_count': totalPlansCount,
      'source': source, // 'home_tab|direct_link|search'
      ...?properties,
    };

    await _sendEvent('plan_list_viewed', eventProperties);
  }

  Future<void> trackPlanDetailViewed({
    required int planId,
    required String planName,
    required int planDurationWeeks,
    required int? planFrequency,
    required String? planGoal,
    required String? planExperienceLevel,
    required bool hasUserMaxes,
    Map<String, dynamic>? properties,
  }) async {
    final eventProperties = <String, dynamic>{
      'funnel': 'plan_view_to_apply_rate',
      'step': 2,
      'step_name': 'plan_detail_viewed',
      'plan_id': planId,
      'plan_name': planName,
      'plan_duration_weeks': planDurationWeeks,
      'plan_frequency': planFrequency,
      'plan_goal': planGoal,
      'plan_experience_level': planExperienceLevel,
      'has_user_maxes': hasUserMaxes,
      ...?properties,
    };

    await _sendEvent('plan_detail_viewed', eventProperties);
  }

  Future<void> trackPlanInteraction({
    required int planId,
    required String interactionType,
    required int timeSpentSeconds,
    Map<String, dynamic>? properties,
  }) async {
    final eventProperties = <String, dynamic>{
      'funnel': 'plan_view_to_apply_rate',
      'step': 2,
      'step_name': 'plan_interaction',
      'plan_id': planId,
      'interaction_type':
          interactionType, // 'scroll|expand_meso|expand_micro|view_exercises'
      'time_spent_seconds': timeSpentSeconds,
      ...?properties,
    };

    await _sendEvent('plan_interaction', eventProperties);
  }

  Future<void> trackPlanApplyStarted({
    required int planId,
    required int userMaxesCount,
    required String customLevel,
    Map<String, dynamic>? properties,
  }) async {
    final eventProperties = <String, dynamic>{
      'funnel': 'plan_view_to_apply_rate',
      'step': 3,
      'step_name': 'plan_apply_started',
      'plan_id': planId,
      'user_maxes_count': userMaxesCount,
      'customization_level': customLevel, // 'none|basic|advanced'
      ...?properties,
    };

    await _sendEvent('plan_apply_started', eventProperties);
  }

  Future<void> trackPlanApplied({
    required int planId,
    required int appliedPlanId,
    required int userMaxesCount,
    required bool computeWeights,
    required int timeToApplySeconds,
    required int customizationChanges,
    Map<String, dynamic>? properties,
  }) async {
    final eventProperties = <String, dynamic>{
      'funnel': 'plan_view_to_apply_rate',
      'step': 4,
      'step_name': 'plan_applied',
      'plan_id': planId,
      'applied_plan_id': appliedPlanId,
      'user_maxes_count': userMaxesCount,
      'compute_weights': computeWeights,
      'time_to_apply_seconds': timeToApplySeconds,
      'customization_changes': customizationChanges,
      ...?properties,
    };

    await _sendEvent('plan_applied', eventProperties);
  }

  Future<void> trackPlanApplyFailed({
    required int planId,
    required String errorType,
    required String errorMessage,
    required int userMaxesCount,
    Map<String, dynamic>? properties,
  }) async {
    final eventProperties = <String, dynamic>{
      'funnel': 'plan_view_to_apply_rate',
      'step': 3,
      'step_name': 'plan_apply_failed',
      'plan_id': planId,
      'error_type': errorType, // 'validation|network|server|user_maxes_missing'
      'error_message': errorMessage,
      'user_maxes_count': userMaxesCount,
      ...?properties,
    };

    await _sendEvent('plan_apply_failed', eventProperties);
  }

  // First Week Adherence Funnel
  Future<void> trackPlanActivated({
    required int appliedPlanId,
    required String planName,
    required int totalWorkoutsInPlan,
    Map<String, dynamic>? properties,
  }) async {
    final eventProperties = <String, dynamic>{
      'funnel': 'first_week_adherence',
      'step': 1,
      'step_name': 'plan_activated',
      'applied_plan_id': appliedPlanId,
      'plan_name': planName,
      'activation_day': 'day_0',
      'total_workouts_in_plan': totalWorkoutsInPlan,
      ...?properties,
    };

    await _sendEvent('plan_activated', eventProperties);
  }

  Future<void> trackFirstWeekScheduleViewed({
    required int appliedPlanId,
    required int scheduledWorkoutsWeek1,
    required String? firstWorkoutDate,
    Map<String, dynamic>? properties,
  }) async {
    final eventProperties = <String, dynamic>{
      'funnel': 'first_week_adherence',
      'step': 2,
      'step_name': 'first_week_schedule_viewed',
      'applied_plan_id': appliedPlanId,
      'scheduled_workouts_week_1': scheduledWorkoutsWeek1,
      'first_workout_date': firstWorkoutDate,
      ...?properties,
    };

    await _sendEvent('first_week_schedule_viewed', eventProperties);
  }

  Future<void> trackFirstWeekWorkoutStarted({
    required int appliedPlanId,
    required int workoutId,
    required int planDayIndex,
    required bool isFirstWeekWorkout,
    required int daysSincePlanStart,
    Map<String, dynamic>? properties,
  }) async {
    final eventProperties = <String, dynamic>{
      'funnel': 'first_week_adherence',
      'step': 3,
      'step_name': 'first_week_workout_started',
      'applied_plan_id': appliedPlanId,
      'workout_id': workoutId,
      'plan_day_index': planDayIndex,
      'is_first_week_workout': isFirstWeekWorkout,
      'days_since_plan_start': daysSincePlanStart,
      ...?properties,
    };

    await _sendEvent('first_week_workout_started', eventProperties);
  }

  Future<void> trackFirstWeekWorkoutCompleted({
    required int appliedPlanId,
    required int workoutId,
    required int planDayIndex,
    required bool isFirstWeekWorkout,
    required double completionRate,
    required int actualVsPlannedDuration,
    Map<String, dynamic>? properties,
  }) async {
    final eventProperties = <String, dynamic>{
      'funnel': 'first_week_adherence',
      'step': 4,
      'step_name': 'first_week_workout_completed',
      'applied_plan_id': appliedPlanId,
      'workout_id': workoutId,
      'plan_day_index': planDayIndex,
      'is_first_week_workout': isFirstWeekWorkout,
      'completion_rate': completionRate,
      'actual_vs_planned_duration': actualVsPlannedDuration,
      ...?properties,
    };

    await _sendEvent('first_week_workout_completed', eventProperties);
  }

  Future<void> trackFirstWeekCompleted({
    required int appliedPlanId,
    required int plannedWorkouts,
    required int completedWorkouts,
    required double adherenceRate,
    required int totalTrainingTime,
    required double avgIntensity,
    Map<String, dynamic>? properties,
  }) async {
    final eventProperties = <String, dynamic>{
      'funnel': 'first_week_adherence',
      'step': 5,
      'step_name': 'first_week_completed',
      'applied_plan_id': appliedPlanId,
      'planned_workouts': plannedWorkouts,
      'completed_workouts': completedWorkouts,
      'adherence_rate': adherenceRate,
      'total_training_time': totalTrainingTime,
      'avg_intensity': avgIntensity,
      ...?properties,
    };

    await _sendEvent('first_week_completed', eventProperties);
  }

  // 30-Day Retention Funnel
  Future<void> trackDailyPlanCheck({
    required int appliedPlanId,
    required int daysSincePlanStart,
    required bool hasWorkoutToday,
    required int consecutiveDays,
    Map<String, dynamic>? properties,
  }) async {
    final eventProperties = <String, dynamic>{
      'funnel': 'day_30_retention',
      'step': 1,
      'step_name': 'daily_plan_check',
      'applied_plan_id': appliedPlanId,
      'days_since_plan_start': daysSincePlanStart,
      'has_workout_today': hasWorkoutToday,
      'consecutive_days': consecutiveDays,
      ...?properties,
    };

    await _sendEvent('daily_plan_check', eventProperties);
  }

  Future<void> trackWeeklyMilestone({
    required int appliedPlanId,
    required int weekNumber,
    required int totalWorkoutsCompleted,
    required double cumulativeAdherence,
    required double strengthProgress,
    Map<String, dynamic>? properties,
  }) async {
    final eventProperties = <String, dynamic>{
      'funnel': 'day_30_retention',
      'step': 2,
      'step_name': 'weekly_milestone',
      'applied_plan_id': appliedPlanId,
      'week_number': weekNumber,
      'total_workouts_completed': totalWorkoutsCompleted,
      'cumulative_adherence': cumulativeAdherence,
      'strength_progress': strengthProgress,
      ...?properties,
    };

    await _sendEvent('weekly_milestone', eventProperties);
  }

  Future<void> trackDay30Milestone({
    required int appliedPlanId,
    required int totalPlannedWorkouts,
    required int totalCompletedWorkouts,
    required double overallAdherenceRate,
    required double strengthImprovement,
    required double weightProgress,
    required double userSatisfactionScore,
    Map<String, dynamic>? properties,
  }) async {
    final eventProperties = <String, dynamic>{
      'funnel': 'day_30_retention',
      'step': 3,
      'step_name': 'day_30_milestone',
      'applied_plan_id': appliedPlanId,
      'total_planned_workouts': totalPlannedWorkouts,
      'total_completed_workouts': totalCompletedWorkouts,
      'overall_adherence_rate': overallAdherenceRate,
      'strength_improvement': strengthImprovement,
      'weight_progress': weightProgress,
      'user_satisfaction_score': userSatisfactionScore,
      ...?properties,
    };

    await _sendEvent('day_30_milestone', eventProperties);
  }

  Future<void> trackUserChurnRisk({
    required int appliedPlanId,
    required int daysSinceLastActivity,
    required String lastActivityDate,
    required String churnRiskLevel,
    Map<String, dynamic>? properties,
  }) async {
    final eventProperties = <String, dynamic>{
      'funnel': 'day_30_retention',
      'step': 4,
      'step_name': 'user_churn_risk',
      'applied_plan_id': appliedPlanId,
      'days_since_last_activity': daysSinceLastActivity,
      'last_activity_date': lastActivityDate,
      'churn_risk_level': churnRiskLevel, // 'low|medium|high|critical'
      ...?properties,
    };

    await _sendEvent('user_churn_risk', eventProperties);
  }

  Future<void> trackUserReactivated({
    required int appliedPlanId,
    required int daysInactive,
    required String reactivationTrigger,
    Map<String, dynamic>? properties,
  }) async {
    final eventProperties = <String, dynamic>{
      'funnel': 'day_30_retention',
      'step': 5,
      'step_name': 'user_reactivated',
      'applied_plan_id': appliedPlanId,
      'days_inactive': daysInactive,
      'reactivation_trigger':
          reactivationTrigger, // 'notification|email|organic'
      ...?properties,
    };

    await _sendEvent('user_reactivated', eventProperties);
  }

  // Additional Engagement Metrics
  Future<void> trackCohortAssignment({
    required String cohortType,
    required String cohortValue,
    Map<String, dynamic>? properties,
  }) async {
    final eventProperties = <String, dynamic>{
      'cohort_type': cohortType, // 'plan_duration|frequency|goal|experience'
      'cohort_value': cohortValue,
      'join_date': DateTime.now().toIso8601String(),
      ...?properties,
    };

    await _sendEvent('cohort_assignment', eventProperties);
  }

  Future<void> trackUserBehaviorSegment({
    required String segment,
    required double avgSessionsPerWeek,
    required double aiUsageFrequency,
    required double socialEngagement,
    Map<String, dynamic>? properties,
  }) async {
    final eventProperties = <String, dynamic>{
      'segment': segment, // 'power_user|regular|casual|at_risk'
      'avg_sessions_per_week': avgSessionsPerWeek,
      'ai_usage_frequency': aiUsageFrequency,
      'social_engagement': socialEngagement,
      ...?properties,
    };

    await _sendEvent('user_behavior_segment', eventProperties);
  }

  Future<void> trackABTestExposure({
    required String testName,
    required String variant,
    Map<String, dynamic>? properties,
  }) async {
    final eventProperties = <String, dynamic>{
      'test_name': testName, // 'plan_application_flow|ui_changes|onboarding'
      'variant': variant, // 'control|variant_a|variant_b'
      'exposure_date': DateTime.now().toIso8601String(),
      ...?properties,
    };

    await _sendEvent('ab_test_exposure', eventProperties);
  }

  // ===== SUCCESS METRICS =====

  // Plan Completion Rate Tracking
  Future<void> trackPlanCompletionStarted({
    required int appliedPlanId,
    required String planName,
    required int totalWorkouts,
    required int planDurationWeeks,
    Map<String, dynamic>? properties,
  }) async {
    final eventProperties = <String, dynamic>{
      'metric': 'plan_completion_rate',
      'phase': 'started',
      'applied_plan_id': appliedPlanId,
      'plan_name': planName,
      'total_workouts': totalWorkouts,
      'plan_duration_weeks': planDurationWeeks,
      'start_date': DateTime.now().toIso8601String(),
      ...?properties,
    };

    await _sendEvent('plan_completion_started', eventProperties);
  }

  Future<void> trackPlanCompletionProgress({
    required int appliedPlanId,
    required int completedWorkouts,
    required int totalWorkouts,
    required double completionPercentage,
    required int weeksElapsed,
    Map<String, dynamic>? properties,
  }) async {
    final eventProperties = <String, dynamic>{
      'metric': 'plan_completion_rate',
      'phase': 'progress',
      'applied_plan_id': appliedPlanId,
      'completed_workouts': completedWorkouts,
      'total_workouts': totalWorkouts,
      'completion_percentage': completionPercentage,
      'weeks_elapsed': weeksElapsed,
      'on_track_percentage': (completedWorkouts / totalWorkouts) * 100,
      ...?properties,
    };

    await _sendEvent('plan_completion_progress', eventProperties);
  }

  Future<void> trackPlanCompleted({
    required int appliedPlanId,
    required String planName,
    required int totalWorkouts,
    required int completedWorkouts,
    required double finalCompletionRate,
    required int actualDurationWeeks,
    required double avgWeeklyAdherence,
    required double strengthImprovement,
    Map<String, dynamic>? properties,
  }) async {
    final eventProperties = <String, dynamic>{
      'metric': 'plan_completion_rate',
      'phase': 'completed',
      'applied_plan_id': appliedPlanId,
      'plan_name': planName,
      'total_workouts': totalWorkouts,
      'completed_workouts': completedWorkouts,
      'final_completion_rate': finalCompletionRate,
      'planned_duration_weeks': (totalWorkouts / 3)
          .round(), // Предполагаем 3 тренировки в неделю
      'actual_duration_weeks': actualDurationWeeks,
      'avg_weekly_adherence': avgWeeklyAdherence,
      'strength_improvement': strengthImprovement,
      'completion_status': finalCompletionRate >= 80.0 ? 'success' : 'partial',
      'end_date': DateTime.now().toIso8601String(),
      ...?properties,
    };

    await _sendEvent('plan_completed', eventProperties);
  }

  Future<void> trackPlanAbandoned({
    required int appliedPlanId,
    required String planName,
    required int completedWorkouts,
    required int totalWorkouts,
    required double completionAtAbandon,
    required String abandonmentReason,
    required int weeksActive,
    Map<String, dynamic>? properties,
  }) async {
    final eventProperties = <String, dynamic>{
      'metric': 'plan_completion_rate',
      'phase': 'abandoned',
      'applied_plan_id': appliedPlanId,
      'plan_name': planName,
      'completed_workouts': completedWorkouts,
      'total_workouts': totalWorkouts,
      'completion_at_abandon': completionAtAbandon,
      'abandonment_reason':
          abandonmentReason, // 'too_hard|injury|time|lost_motivation|found_alternative'
      'weeks_active': weeksActive,
      'abandonment_week': (completedWorkouts / 3)
          .round(), // Предполагаем 3 тренировки в неделю
      ...?properties,
    };

    await _sendEvent('plan_abandoned', eventProperties);
  }

  // Average Adherence Percentage Tracking
  Future<void> trackWeeklyAdherence({
    required int appliedPlanId,
    required int weekNumber,
    required int plannedWorkouts,
    required int completedWorkouts,
    required double weeklyAdherence,
    required double cumulativeAdherence,
    required int totalCompletedWorkouts,
    required int totalPlannedWorkouts,
    Map<String, dynamic>? properties,
  }) async {
    final eventProperties = <String, dynamic>{
      'metric': 'avg_adherence_pct',
      'type': 'weekly',
      'applied_plan_id': appliedPlanId,
      'week_number': weekNumber,
      'planned_workouts': plannedWorkouts,
      'completed_workouts': completedWorkouts,
      'weekly_adherence': weeklyAdherence,
      'cumulative_adherence': cumulativeAdherence,
      'total_completed_workouts': totalCompletedWorkouts,
      'total_planned_workouts': totalPlannedWorkouts,
      'running_avg_adherence':
          (totalCompletedWorkouts / totalPlannedWorkouts) * 100,
      ...?properties,
    };

    await _sendEvent('weekly_adherence', eventProperties);
  }

  Future<void> trackMonthlyAdherenceSummary({
    required int appliedPlanId,
    required int monthNumber,
    required double avgWeeklyAdherence,
    required double monthlyAdherence,
    required int totalWorkoutsMonth,
    required double adherenceTrend, // 'improving|stable|declining'
    required double bestWeekAdherence,
    required double worstWeekAdherence,
    Map<String, dynamic>? properties,
  }) async {
    final eventProperties = <String, dynamic>{
      'metric': 'avg_adherence_pct',
      'type': 'monthly_summary',
      'applied_plan_id': appliedPlanId,
      'month_number': monthNumber,
      'avg_weekly_adherence': avgWeeklyAdherence,
      'monthly_adherence': monthlyAdherence,
      'total_workouts_month': totalWorkoutsMonth,
      'adherence_trend': adherenceTrend,
      'best_week_adherence': bestWeekAdherence,
      'worst_week_adherence': worstWeekAdherence,
      'month': DateTime(DateTime.now().year, monthNumber, 1).toIso8601String(),
      ...?properties,
    };

    await _sendEvent('monthly_adherence_summary', eventProperties);
  }

  Future<void> trackOverallAdherenceCalculated({
    required int appliedPlanId,
    required double overallAdherence,
    required int totalActiveWeeks,
    required int totalCompletedWorkouts,
    required int totalPlannedWorkouts,
    required double consistencyScore, // Стандартное отклонение adherence
    required String performanceLevel, // 'excellent|good|average|poor'
    Map<String, dynamic>? properties,
  }) async {
    final eventProperties = <String, dynamic>{
      'metric': 'avg_adherence_pct',
      'type': 'overall',
      'applied_plan_id': appliedPlanId,
      'overall_adherence': overallAdherence,
      'total_active_weeks': totalActiveWeeks,
      'total_completed_workouts': totalCompletedWorkouts,
      'total_planned_workouts': totalPlannedWorkouts,
      'consistency_score':
          consistencyScore, // 0-100, где 100 = идеальная последовательность
      'performance_level': performanceLevel,
      'adherence_grade': _getAdherenceGrade(overallAdherence),
      'calculation_date': DateTime.now().toIso8601String(),
      ...?properties,
    };

    await _sendEvent('overall_adherence_calculated', eventProperties);
  }

  // ===== PRODUCT METRICS =====

  // AI Assistant Adoption Tracking
  Future<void> trackAIAssistantFirstUse({
    required String featureUsed,
    required String entryPoint,
    required String context,
    Map<String, dynamic>? properties,
  }) async {
    final eventProperties = <String, dynamic>{
      'metric': 'ai_assistant_adoption',
      'event': 'first_use',
      'feature_used':
          featureUsed, // 'mass_edit|exercise_replace|plan_generation|intensity_adjustment'
      'entry_point':
          entryPoint, // 'workout_detail|plan_editor|chat_button|voice_command'
      'context': context, // 'active_plan|plan_creation|troubleshooting'
      'user_experience_level': _getUserExperienceLevel(),
      'first_use_date': DateTime.now().toIso8601String(),
      ...?properties,
    };

    await _sendEvent('ai_assistant_first_use', eventProperties);
  }

  Future<void> trackAIAssistantUsage({
    required String featureUsed,
    required String entryPoint,
    required int usageCount,
    required double successRate,
    required int timeSpentSeconds,
    required String userSatisfaction,
    Map<String, dynamic>? properties,
  }) async {
    final eventProperties = <String, dynamic>{
      'metric': 'ai_assistant_adoption',
      'event': 'usage',
      'feature_used': featureUsed,
      'entry_point': entryPoint,
      'usage_count': usageCount,
      'success_rate': successRate,
      'time_spent_seconds': timeSpentSeconds,
      'user_satisfaction':
          userSatisfaction, // 'very_satisfied|satisfied|neutral|dissatisfied'
      'session_type': _getAISessionType(usageCount),
      'adoption_level': _getAdoptionLevel(usageCount, successRate),
      ...?properties,
    };

    await _sendEvent('ai_assistant_usage', eventProperties);
  }

  Future<void> trackAIAssistantPowerUser({
    required int totalUsages,
    required double weeklyFrequency,
    required List<String> featuresUsed,
    required double avgSuccessRate,
    required String mostUsedFeature,
    required int daysSinceFirstUse,
    Map<String, dynamic>? properties,
  }) async {
    final eventProperties = <String, dynamic>{
      'metric': 'ai_assistant_adoption',
      'event': 'power_user_achieved',
      'total_usages': totalUsages,
      'weekly_frequency': weeklyFrequency,
      'features_used': featuresUsed,
      'avg_success_rate': avgSuccessRate,
      'most_used_feature': mostUsedFeature,
      'days_since_first_use': daysSinceFirstUse,
      'power_user_level': _getPowerUserLevel(weeklyFrequency, avgSuccessRate),
      'adoption_score': _calculateAdoptionScore(
        totalUsages,
        weeklyFrequency,
        avgSuccessRate,
      ),
      ...?properties,
    };

    await _sendEvent('ai_assistant_power_user', eventProperties);
  }

  // Dropout Analysis Tracking
  Future<void> trackDropoutRiskStarted({
    required int appliedPlanId,
    required String riskFactors,
    required double currentAdherence,
    required int consecutiveMissedWorkouts,
    required String riskLevel,
    Map<String, dynamic>? properties,
  }) async {
    final eventProperties = <String, dynamic>{
      'metric': 'dropout_analysis',
      'event': 'risk_started',
      'applied_plan_id': appliedPlanId,
      'risk_factors':
          riskFactors, // 'low_adherence|missed_workouts|low_engagement|negative_feedback'
      'current_adherence': currentAdherence,
      'consecutive_missed_workouts': consecutiveMissedWorkouts,
      'risk_level': riskLevel, // 'low|medium|high|critical'
      'risk_start_date': DateTime.now().toIso8601String(),
      ...?properties,
    };

    await _sendEvent('dropout_risk_started', eventProperties);
  }

  Future<void> trackDropoutReason({
    required int appliedPlanId,
    required String primaryReason,
    required String? secondaryReason,
    required int weekOfDropout,
    required double adherenceAtDropout,
    required String userFeedback,
    required bool wouldRecommend,
    Map<String, dynamic>? properties,
  }) async {
    final eventProperties = <String, dynamic>{
      'metric': 'dropout_analysis',
      'event': 'dropout_occurred',
      'applied_plan_id': appliedPlanId,
      'primary_reason':
          primaryReason, // 'too_difficult|injury|time_constraints|lost_motivation|technical_issues|cost'
      'secondary_reason': secondaryReason,
      'week_of_dropout': weekOfDropout,
      'adherence_at_dropout': adherenceAtDropout,
      'user_feedback': userFeedback,
      'would_recommend': wouldRecommend,
      'dropout_category': _categorizeDropoutReason(primaryReason),
      'preventable': _isDropoutPreventable(primaryReason),
      'dropout_date': DateTime.now().toIso8601String(),
      ...?properties,
    };

    await _sendEvent('dropout_reason', eventProperties);
  }

  Future<void> trackDropoutIntervention({
    required int appliedPlanId,
    required String interventionType,
    required bool userResponded,
    required String? outcome,
    required int daysSinceRisk,
    Map<String, dynamic>? properties,
  }) async {
    final eventProperties = <String, dynamic>{
      'metric': 'dropout_analysis',
      'event': 'intervention_attempted',
      'applied_plan_id': appliedPlanId,
      'intervention_type':
          interventionType, // 'email|notification|in_app_message|coach_outreach|difficulty_adjustment'
      'user_responded': userResponded,
      'outcome': outcome, // 'user_retained|plan_modified|user_still_dropped'
      'days_since_risk': daysSinceRisk,
      'intervention_success':
          userResponded && (outcome?.contains('retained') == true),
      ...?properties,
    };

    await _sendEvent('dropout_intervention', eventProperties);
  }

  Future<void> trackDropoutAnalysisSummary({
    required int totalDropouts,
    required Map<String, int> dropoutReasons,
    required double avgWeeksBeforeDropout,
    required double avgAdherenceAtDropout,
    required List<String> topRiskFactors,
    required double interventionSuccessRate,
    Map<String, dynamic>? properties,
  }) async {
    final eventProperties = <String, dynamic>{
      'metric': 'dropout_analysis',
      'event': 'summary_analysis',
      'total_dropouts': totalDropouts,
      'dropout_reasons': dropoutReasons,
      'avg_weeks_before_dropout': avgWeeksBeforeDropout,
      'avg_adherence_at_dropout': avgAdherenceAtDropout,
      'top_risk_factors': topRiskFactors,
      'intervention_success_rate': interventionSuccessRate,
      'most_common_reason': _getMostCommonReason(dropoutReasons),
      'dropout_rate': _calculateDropoutRate(totalDropouts),
      'analysis_period': DateTime.now().toIso8601String(),
      ...?properties,
    };

    await _sendEvent('dropout_analysis_summary', eventProperties);
  }

  // Helper methods for Success and Product Metrics
  String _getAdherenceGrade(double adherence) {
    if (adherence >= 90) return 'A';
    if (adherence >= 80) return 'B';
    if (adherence >= 70) return 'C';
    if (adherence >= 60) return 'D';
    return 'F';
  }

  String _getUserExperienceLevel() {
    // This would typically come from user profile or plan data
    return 'intermediate'; // Placeholder
  }

  String _getAISessionType(int usageCount) {
    if (usageCount == 1) return 'first_time';
    if (usageCount <= 5) return 'exploring';
    if (usageCount <= 15) return 'regular';
    return 'power';
  }

  String _getAdoptionLevel(int usageCount, double successRate) {
    if (usageCount >= 10 && successRate >= 0.8) return 'adopted';
    if (usageCount >= 5) return 'experimenting';
    if (usageCount >= 2) return 'curious';
    return 'aware';
  }

  String _getPowerUserLevel(double weeklyFrequency, double avgSuccessRate) {
    if (weeklyFrequency >= 3 && avgSuccessRate >= 0.9) return 'super_power';
    if (weeklyFrequency >= 2 && avgSuccessRate >= 0.8) return 'power';
    if (weeklyFrequency >= 1) return 'regular';
    return 'casual';
  }

  double _calculateAdoptionScore(
    int totalUsages,
    double weeklyFrequency,
    double avgSuccessRate,
  ) {
    final usageScore = (totalUsages / 10.0).clamp(0.0, 1.0) * 40;
    final frequencyScore = (weeklyFrequency / 3.0).clamp(0.0, 1.0) * 35;
    final successScore = avgSuccessRate * 25;
    return usageScore + frequencyScore + successScore;
  }

  String _categorizeDropoutReason(String reason) {
    final categoryMap = {
      'too_difficult': 'difficulty',
      'injury': 'health',
      'time_constraints': 'time',
      'lost_motivation': 'motivation',
      'technical_issues': 'technical',
      'cost': 'financial',
    };
    return categoryMap[reason] ?? 'other';
  }

  bool _isDropoutPreventable(String reason) {
    final preventableReasons = [
      'too_difficult',
      'time_constraints',
      'lost_motivation',
      'technical_issues',
    ];
    return preventableReasons.contains(reason);
  }

  String _getMostCommonReason(Map<String, int> reasons) {
    if (reasons.isEmpty) return 'none';
    final sortedEntries = reasons.entries.toList()
      ..sort((a, b) => b.value.compareTo(a.value));
    return sortedEntries.first.key;
  }

  double _calculateDropoutRate(int totalDropouts) {
    // This would need total active plans context
    // For now, returning a placeholder calculation
    return (totalDropouts / 100.0) * 100; // Placeholder
  }

  // Метод для отладки - показывает информацию о сервисе
  void debugInfo() {
    _logger.i('🔍 UserAnalyticsService Debug Info:');
    _logger.i('📍 Base URL: $_baseUrl');
    _logger.i(
      '🔑 API Key configured: ${dotenv.env['AMPLITUDE_API_KEY']?.isNotEmpty == true}',
    );
    _logger.i('🌐 Platform: Flutter Web');
    _logger.i('📦 Available methods:');
    _logger.i('   - trackScreenOpen(String screenName)');
    _logger.i('   - trackWorkoutAction(String action, int? workoutId)');
    _logger.i('   - trackExerciseAction(String action, int? exerciseId)');
    _logger.i('   - trackUserAction(String action)');
    _logger.i('   - trackError(String errorType, String errorMessage)');
    _logger.i('   - trackTestEvent()');
    _logger.i('');
    _logger.i('🎯 Time-to-First-Dollar Funnel:');
    _logger.i('   - trackTrainerProfilePublished()');
    _logger.i('   - trackInboundRequestReceived(requestId, clientUserId)');
    _logger.i('   - trackBookingAccepted(bookingId, clientUserId)');
    _logger.i('   - trackPayoutReceived(payoutId, amount, currency)');
    _logger.i('   - trackClientMessage(trainerUserId, clientUserId)');
    _logger.i('   - trackBookingRequest(trainerUserId, clientUserId)');
    _logger.i('   - trackFunnelConversion(fromStep, toStep)');
    _logger.i('');
    _logger.i('📊 Engagement Metrics Funnels:');
    _logger.i('   - Plan View to Apply Rate:');
    _logger.i('     * trackPlanListViewed()');
    _logger.i('     * trackPlanDetailViewed()');
    _logger.i('     * trackPlanInteraction()');
    _logger.i('     * trackPlanApplyStarted()');
    _logger.i('     * trackPlanApplied()');
    _logger.i('     * trackPlanApplyFailed()');
    _logger.i('   - First Week Adherence:');
    _logger.i('     * trackPlanActivated()');
    _logger.i('     * trackFirstWeekScheduleViewed()');
    _logger.i('     * trackFirstWeekWorkoutStarted()');
    _logger.i('     * trackFirstWeekWorkoutCompleted()');
    _logger.i('     * trackFirstWeekCompleted()');
    _logger.i('   - 30-Day Retention:');
    _logger.i('     * trackDailyPlanCheck()');
    _logger.i('     * trackWeeklyMilestone()');
    _logger.i('     * trackDay30Milestone()');
    _logger.i('     * trackUserChurnRisk()');
    _logger.i('     * trackUserReactivated()');
    _logger.i('   - Additional Metrics:');
    _logger.i('     * trackCohortAssignment()');
    _logger.i('     * trackUserBehaviorSegment()');
    _logger.i('     * trackABTestExposure()');
  }
}
