import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:workout_app/models/applied_calendar_plan.dart';
import 'package:workout_app/services/api_client.dart';
import 'package:workout_app/services/plan_service.dart';

final planServiceProvider = Provider<PlanService>((ref) => PlanService(apiClient: ApiClient()));

final activeAppliedPlanProvider = FutureProvider<AppliedCalendarPlan?>((ref) async {
  final svc = ref.watch(planServiceProvider);
  return svc.getActivePlan();
});
