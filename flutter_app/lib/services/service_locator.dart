import 'package:flutter/material.dart';
import 'package:provider/provider.dart' as provider;
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'api_client.dart';
import 'exercise_service.dart';
import 'workout_service.dart';
import 'logger_service.dart';
import 'calendar_plan_service.dart';
import 'calendar_plan_instance_service.dart';
import 'user_max_service.dart';
import 'applied_calendar_plan_service.dart';
import 'workout_session_service.dart';
import 'mesocycle_service.dart';
import 'rpe_service.dart';
import 'accounts_service.dart';

// Riverpod Providers
final workoutServiceProvider = Provider<WorkoutService>((ref) {
  final apiClient = ref.watch(apiClientProvider);
  return WorkoutService(apiClient);
});

final exerciseServiceProvider = Provider<ExerciseService>((ref) {
  final apiClient = ref.watch(apiClientProvider);
  return ExerciseService(apiClient);
});

final workoutSessionServiceProvider = Provider<WorkoutSessionService>((ref) {
  final apiClient = ref.watch(apiClientProvider);
  return WorkoutSessionService(apiClient);
});

final calendarPlanServiceProvider = Provider<CalendarPlanService>((ref) {
  final apiClient = ref.watch(apiClientProvider);
  return CalendarPlanService(apiClient);
});

final calendarPlanInstanceServiceProvider = Provider<CalendarPlanInstanceService>((ref) {
  final apiClient = ref.watch(apiClientProvider);
  return CalendarPlanInstanceService(apiClient);
});

final appliedCalendarPlanServiceProvider = Provider<AppliedCalendarPlanService>((ref) {
  final apiClient = ref.watch(apiClientProvider);
  return AppliedCalendarPlanService(apiClient);
});

final mesocycleServiceProvider = Provider<MesocycleService>((ref) {
  final apiClient = ref.watch(apiClientProvider);
  return MesocycleService(apiClient);
});

final rpeServiceProvider = Provider<RpeService>((ref) {
  final apiClient = ref.watch(apiClientProvider);
  return RpeService(apiClient);
});

final accountsServiceProvider = Provider<AccountsService>((ref) {
  final apiClient = ref.watch(apiClientProvider);
  return AccountsService(apiClient);
});

final apiClientProvider = Provider<ApiClient>((ref) {
  return ApiClient.create();
});

class ServiceProvider extends StatelessWidget {
  final Widget child;
  
  const ServiceProvider({
    Key? key,
    required this.child,
  }) : super(key: key);

  @override
  Widget build(BuildContext context) {
    return provider.MultiProvider(
      providers: [
        // Core Services
        provider.Provider(create: (_) => LoggerService('ServiceLocator')),
        
        // API Client
        provider.Provider(
          create: (context) => ApiClient.create(),
          dispose: (_, client) => client.dispose(),
        ),
        
        // Business Logic Services
        provider.ProxyProvider<ApiClient, ExerciseService>(
          update: (_, apiClient, __) => ExerciseService(apiClient),
        ),
        
        provider.ProxyProvider<ApiClient, WorkoutService>(
          update: (_, apiClient, __) => WorkoutService(apiClient),
        ),
        
        provider.ProxyProvider<ApiClient, CalendarPlanService>(
          update: (_, apiClient, __) => CalendarPlanService(apiClient),
        ),
        
        provider.ProxyProvider<ApiClient, CalendarPlanInstanceService>(
          update: (_, apiClient, __) => CalendarPlanInstanceService(apiClient),
        ),
        
        provider.ProxyProvider<ApiClient, UserMaxService>(
          update: (_, apiClient, __) => UserMaxService(apiClient),
        ),

        provider.ProxyProvider<ApiClient, AppliedCalendarPlanService>(
          update: (_, apiClient, __) => AppliedCalendarPlanService(apiClient),
        ),

        provider.ProxyProvider<ApiClient, WorkoutSessionService>(
          update: (_, apiClient, __) => WorkoutSessionService(apiClient),
        ),

        provider.ProxyProvider<ApiClient, MesocycleService>(
          update: (_, apiClient, __) => MesocycleService(apiClient),
        ),

        provider.ProxyProvider<ApiClient, AccountsService>(
          update: (_, apiClient, __) => AccountsService(apiClient),
        ),
      ],
      child: child,
    );
  }
}

// Extension to easily access services from BuildContext
extension ServiceExtension on BuildContext {
  T getService<T>() {
    try {
      return provider.Provider.of<T>(this, listen: false);
    } on provider.ProviderNotFoundException catch (e) {
      throw FlutterError('''
        Service not found: $T
        This might happen if you forgot to add the service to the ServiceProvider
        or if you're trying to access it before the app is fully initialized.
      ''');
    }
  }
  
  // Convenience getters for commonly used services
  LoggerService get logger => getService<LoggerService>();
  ApiClient get apiClient => getService<ApiClient>();
  ExerciseService get exerciseService => getService<ExerciseService>();
  WorkoutService get workoutService => getService<WorkoutService>();
  CalendarPlanService get calendarPlanService => getService<CalendarPlanService>();
  CalendarPlanInstanceService get calendarPlanInstanceService => getService<CalendarPlanInstanceService>();
  UserMaxService get userMaxService => getService<UserMaxService>();
  AppliedCalendarPlanService get appliedCalendarPlanService => getService<AppliedCalendarPlanService>();
  WorkoutSessionService get workoutSessionService => getService<WorkoutSessionService>();
  MesocycleService get mesocycleService => getService<MesocycleService>();
  AccountsService get accountsService => getService<AccountsService>();
}
