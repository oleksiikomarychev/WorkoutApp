import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:workout_app/services/api_client.dart';
import 'package:workout_app/services/exercise_service.dart';
import 'package:workout_app/services/workout_service.dart';
import 'package:workout_app/services/workout_session_service.dart';
import 'package:workout_app/services/mesocycle_service.dart';
import 'package:workout_app/services/logger_service.dart';
import 'package:workout_app/services/rpe_service.dart';
import 'package:workout_app/services/analytics_service.dart';
import 'package:workout_app/services/avatar_service.dart';
import 'package:workout_app/services/profile_service.dart';
import 'package:workout_app/services/crm_relationships_service.dart';
import 'package:workout_app/services/crm_coach_service.dart';
import 'package:workout_app/services/crm_analytics_service.dart';
import 'package:workout_app/services/crm_billing_service.dart';
import 'package:workout_app/services/users_service.dart';
import 'package:workout_app/services/social_service.dart';
import 'package:workout_app/services/messaging_service.dart';
import 'package:workout_app/services/crm_coach_mass_edit_service.dart';
import 'package:workout_app/services/agent_mass_edit_service.dart';


final apiClientProvider = Provider<ApiClient>((ref) {
  return ApiClient();
});

final loggerServiceProvider = Provider<LoggerService>((ref) {
  return LoggerService('ServiceLocator');
});

final exerciseServiceProvider = Provider<ExerciseService>((ref) {
  return ExerciseService(ref.watch(apiClientProvider));
});

final workoutServiceProvider = Provider<WorkoutService>((ref) {
  return WorkoutService(apiClient: ref.read(apiClientProvider));
});

final workoutSessionServiceProvider = Provider<WorkoutSessionService>((ref) {
  return WorkoutSessionService(ref.watch(apiClientProvider));
});


final apiClientProviderVerify = Provider((ref) => ApiClient());

final mesocycleServiceProvider = Provider((ref) => MesocycleService(apiClient: ref.read(apiClientProvider)));
final workoutServiceProviderVerify = Provider((ref) => WorkoutService(apiClient: ref.read(apiClientProvider)));

final rpeServiceProvider = Provider<RpeService>((ref) => RpeService(ref.watch(apiClientProvider)));
final analyticsServiceProvider = Provider<AnalyticsService>((ref) => AnalyticsService(ref.watch(apiClientProvider)));
final usersServiceProvider = Provider<UsersService>((ref) => UsersService(ref.watch(apiClientProvider)));
final avatarServiceProvider = Provider<AvatarService>((ref) => AvatarService());
final profileServiceProvider = Provider<ProfileService>((ref) => ProfileService(ref.watch(apiClientProvider)));

final crmRelationshipsServiceProvider = Provider<CrmRelationshipsService>((ref) {
  return CrmRelationshipsService(ref.watch(apiClientProvider));
});

final crmCoachServiceProvider = Provider<CrmCoachService>((ref) {
  return CrmCoachService(ref.watch(apiClientProvider));
});

final crmBillingServiceProvider = Provider<CrmBillingService>((ref) {
  return CrmBillingService(ref.watch(apiClientProvider));
});

final crmAnalyticsServiceProvider = Provider<CrmAnalyticsService>((ref) {
  return CrmAnalyticsService(ref.watch(apiClientProvider));
});

final crmCoachMassEditServiceProvider = Provider<CrmCoachMassEditService>((ref) {
  return CrmCoachMassEditService(ref.watch(apiClientProvider));
});

final agentAppliedPlanMassEditServiceProvider = Provider<AgentAppliedPlanMassEditService>((ref) {
  return AgentAppliedPlanMassEditService(ref.watch(apiClientProvider));
});

final socialServiceProvider = Provider<SocialService>((ref) {
  return SocialService(ref.watch(apiClientProvider));
});

final messagingServiceProvider = Provider<MessagingService>((ref) {
  return MessagingService(ref.watch(apiClientProvider));
});



class ServiceProvider extends ConsumerWidget {
  final Widget child;

  const ServiceProvider({
    super.key,
    required this.child,
  });

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return child;
  }
}
