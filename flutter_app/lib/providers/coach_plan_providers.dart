import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:workout_app/models/applied_calendar_plan.dart';
import 'package:workout_app/models/workout.dart';
import 'package:workout_app/services/service_locator.dart';
import 'package:workout_app/services/crm_coach_service.dart';

DateTime _dateOnly(DateTime dt) => DateTime(dt.year, dt.month, dt.day);

final coachActivePlanProvider = FutureProvider.autoDispose.family<AppliedCalendarPlan?, String>((ref, athleteId) async {
  final svc = ref.watch(crmCoachServiceProvider);
  return await svc.getAthleteActivePlan(athleteId);
});

final coachActivePlanWorkoutsProvider = FutureProvider.autoDispose.family<List<Workout>, String>((ref, athleteId) async {
  final svc = ref.watch(crmCoachServiceProvider);
  final workouts = await svc.getAthleteActivePlanWorkouts(athleteId);
  workouts.sort((a, b) {
    final ai = a.planOrderIndex ?? 1 << 30;
    final bi = b.planOrderIndex ?? 1 << 30;
    if (ai != bi) return ai.compareTo(bi);
    final ad = a.scheduledFor;
    final bd = b.scheduledFor;
    if (ad == null && bd == null) return 0;
    if (ad == null) return 1;
    if (bd == null) return -1;
    return ad.compareTo(bd);
  });
  return workouts;
});

final coachWorkoutsByDayProvider = Provider.autoDispose.family<Map<DateTime, List<Workout>>, String>((ref, athleteId) {
  final asyncList = ref.watch(coachActivePlanWorkoutsProvider(athleteId));
  if (!asyncList.hasValue) return const {};
  final list = asyncList.value ?? const <Workout>[];
  final map = <DateTime, List<Workout>>{};
  for (final w in list) {
    final dt = w.scheduledFor;
    if (dt == null) continue;
    final key = _dateOnly(dt);
    (map[key] ??= <Workout>[]).add(w);
  }
  return map;
});
