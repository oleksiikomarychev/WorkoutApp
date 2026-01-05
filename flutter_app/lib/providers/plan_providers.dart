import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:workout_app/models/applied_calendar_plan.dart';
import 'package:workout_app/models/calendar_plan.dart';
import 'package:workout_app/config/api_config.dart';
import 'package:workout_app/services/api_client.dart';
import 'package:workout_app/services/plan_service.dart';
import 'dart:async';

final planServiceProvider = Provider<PlanService>((ref) => PlanService(apiClient: ApiClient()));

final activeAppliedPlanProvider = FutureProvider<AppliedCalendarPlan?>((ref) async {
  final svc = ref.watch(planServiceProvider);
  return svc.getActivePlan();
});

final activeAppliedPlanSWRProvider = StreamProvider<AppliedCalendarPlan?>((ref) {
  final svc = ref.watch(planServiceProvider);
  return svc.getActivePlanSWR();
});

class CalendarPlansNotifier extends StateNotifier<AsyncValue<List<CalendarPlan>>> {
  final ApiClient _api;
  StreamSubscription<dynamic>? _sub;

  CalendarPlansNotifier(this._api) : super(const AsyncValue.loading()) {
    load();
  }

  Future<void> load() async {
    await _sub?.cancel();

    if (!state.hasValue) {
      state = const AsyncValue.loading();
    }

    final endpoint = ApiConfig.getAllPlansEndpoint();
    _sub = _api
        .getSWR(
          endpoint,
          queryParams: const <String, dynamic>{'roots_only': 'true'},
          context: 'CalendarPlansNotifier.getAllPlansSWR',
          ttlSeconds: 600,
          groups: const ['plans:list'],
          skipNetworkIfFresh: true,
        )
        .listen(
      (data) {
        if (data is List) {
          final plans = data.whereType<Map<String, dynamic>>().map(CalendarPlan.fromJson).toList();
          state = AsyncValue.data(plans);
        }
      },
      onError: (e, st) {
        state = AsyncValue.error(e, st is StackTrace ? st : StackTrace.current);
      },
    );
  }

  void removeLocal(int planId) {
    if (!state.hasValue) return;
    final current = state.value ?? const <CalendarPlan>[];
    state = AsyncValue.data(current.where((p) => p.id != planId).toList(growable: false));
  }

  @override
  void dispose() {
    _sub?.cancel();
    super.dispose();
  }
}

final calendarPlansProvider = StateNotifierProvider<CalendarPlansNotifier, AsyncValue<List<CalendarPlan>>>((ref) {
  return CalendarPlansNotifier(ApiClient.create());
});
