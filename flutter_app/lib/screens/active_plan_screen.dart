import 'dart:async';
import 'dart:math' as math;
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:fl_chart/fl_chart.dart';
import 'package:table_calendar/table_calendar.dart';
import 'package:intl/intl.dart';
import 'package:workout_app/config/constants/theme_constants.dart';
import 'package:workout_app/models/applied_calendar_plan.dart';
import 'package:workout_app/models/calendar_plan.dart';
import 'package:workout_app/models/workout.dart';
import 'package:workout_app/models/plan_analytics.dart';
import 'package:workout_app/models/exercise_definition.dart';
import 'package:workout_app/screens/workout_detail_screen.dart';
import 'package:workout_app/screens/exercise_selection_screen.dart';
import 'package:workout_app/config/api_config.dart';
import 'package:workout_app/services/plan_service.dart';
import 'package:workout_app/services/service_locator.dart';
import 'package:workout_app/services/logger_service.dart';
import 'package:workout_app/services/rpe_service.dart';
import 'package:workout_app/models/exercise_set_dto.dart';

final _planServiceProvider = Provider<PlanService>((ref) => PlanService(apiClient: ref.watch(apiClientProvider)));

final activePlanProvider = FutureProvider<AppliedCalendarPlan?>((ref) async {
  final svc = ref.watch(_planServiceProvider);
  return await svc.getActivePlan();
});

final activePlanWorkoutsProvider = FutureProvider<List<Workout>>((ref) async {
  final plan = await ref.watch(activePlanProvider.future);
  if (plan == null) return [];
  final workoutSvc = ref.watch(workoutServiceProvider);
  final list = await workoutSvc.getWorkoutsByAppliedPlan(plan.id);
  list.sort((a, b) {
    final ai = a.planOrderIndex ?? 1 << 30;
    final bi = b.planOrderIndex ?? 1 << 30;
    return ai.compareTo(bi);
  });
  return list;
});

final activePlanAnalyticsProvider = FutureProvider<PlanAnalyticsResponse?>((ref) async {
  final plan = await ref.watch(activePlanProvider.future);
  if (plan == null) return null;
  final svc = ref.watch(_planServiceProvider);
  return await svc.getAppliedPlanAnalytics(plan.id, groupBy: 'order');
});

DateTime _dateOnly(DateTime d) => DateTime(d.year, d.month, d.day);

final workoutsByDayProvider = Provider<Map<DateTime, List<Workout>>>((ref) {
  final asyncList = ref.watch(activePlanWorkoutsProvider);
  if (!asyncList.hasValue) return const {};
  final map = <DateTime, List<Workout>>{};
  for (final w in asyncList.value ?? const <Workout>[]) {
    final dt = w.scheduledFor;
    if (dt == null) continue;
    final key = _dateOnly(dt);
    (map[key] ??= <Workout>[]).add(w);
  }
  return map;
});

class ActivePlanScreen extends ConsumerStatefulWidget {
  const ActivePlanScreen({super.key});

  @override
  ConsumerState<ActivePlanScreen> createState() => _ActivePlanScreenState();
}

class _ActivePlanScreenState extends ConsumerState<ActivePlanScreen> {
  final _logger = LoggerService('ActivePlanScreen');
  DateTime _focusedDay = DateTime.now();
  DateTime? _selectedDay;
  final TextEditingController _intensityCtrl = TextEditingController();
  final TextEditingController _rpeCtrl = TextEditingController();
  final TextEditingController _repsCtrl = TextEditingController();
  bool _useIntensity = false;
  bool _useRpe = false;
  bool _useReps = false;
  String _intensityMode = 'set'; // set | offset | scale
  String _repsMode = 'set'; // set | offset | scale
  String _rpeMode = 'set';
  String _recalcTarget = 'auto';
  String _fixStrategy = 'none';
  bool _isApplying = false;
  final Set<int> _selectedExerciseIds = <int>{};
  Map<int, String> _exerciseNames = <int, String>{};
  String _rangeMode = 'future'; // future | cycles
  final Set<int> _selectedMesoIds = <int>{};
  final Set<int> _selectedMicroIds = <int>{};
  Map<int, List<int>> _microToGlobalIndices = <int, List<int>>{};
  // Caches for the lifetime of the Mass Edit dialog
  final Map<int, Set<int>> _exerciseIdsByWorkout = <int, Set<int>>{}; // workoutId -> set of exerciseListIds
  final Map<int, String> _exerciseNameCache = <int, String>{}; // exerciseListId -> name
  Timer? _rangeRefreshTimer;

  final List<String> _metrics = const ['sets_count', 'volume_sum', 'intensity_avg', 'effort_avg'];
  String _metricX = 'effort_avg';
  String _metricY = 'effort_avg';

  @override
  void initState() {
    super.initState();
    _selectedDay = _dateOnly(DateTime.now());
  }

  @override
  void dispose() {
    _intensityCtrl.dispose();
    _rpeCtrl.dispose();
    _repsCtrl.dispose();
    _rangeRefreshTimer?.cancel();
    super.dispose();
  }

  void _showSnack(BuildContext context, String text) {
    ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(text)));
  }

  Future<List<Workout>> _filterWorkoutsByRange(DateTime start, DateTime end) async {
    final list = await ref.read(activePlanWorkoutsProvider.future);
    final s = DateTime(start.year, start.month, start.day);
    final e = DateTime(end.year, end.month, end.day, 23, 59, 59);
    final now = DateTime.now();
    return list.where((w) {
      final dt = w.scheduledFor;
      if (dt == null) return false;
      if (dt.isBefore(now)) return false; // only future
      return dt.isAfter(s.subtract(const Duration(seconds: 1))) && dt.isBefore(e.add(const Duration(seconds: 1)));
    }).toList();
  }

  // Build mapping microcycleId -> list of global plan indices (1-based) across entire plan order
  Map<int, List<int>> _buildMicroToGlobalIndexMap(AppliedCalendarPlan plan) {
    final map = <int, List<int>>{};
    int idx = 1;
    final mesoSorted = List.of(plan.calendarPlan.mesocycles)..sort((a, b) => a.orderIndex.compareTo(b.orderIndex));
    for (final meso in mesoSorted) {
      final microSorted = List.of(meso.microcycles)..sort((a, b) => a.orderIndex.compareTo(b.orderIndex));
      for (final micro in microSorted) {
        final len = micro.planWorkouts.isNotEmpty
            ? micro.planWorkouts.length
            : (micro.daysCount ?? 0);
        if (len <= 0) { map[micro.id] = const <int>[]; continue; }
        final list = <int>[];
        for (int i = 0; i < len; i++) { list.add(idx++); }
        map[micro.id] = list;
      }
    }
    return map;
  }

  Future<List<Workout>> _filterWorkoutsByPlanIndices(Set<int> indices) async {
    if (indices.isEmpty) return const <Workout>[];
    final list = await ref.read(activePlanWorkoutsProvider.future);
    final now = DateTime.now();
    return list.where((w) {
      final dt = w.scheduledFor;
      if (dt == null || dt.isBefore(now)) return false; // only future
      final idx = w.planOrderIndex;
      if (idx == null) return false;
      return indices.contains(idx);
    }).toList();
  }

  Set<int> _computeSelectedPlanIndices() {
    final set = <int>{};
    for (final microId in _selectedMicroIds) {
      final list = _microToGlobalIndices[microId];
      if (list != null) set.addAll(list);
    }
    return set;
  }

  Future<void> _refreshExerciseNamesForSelection({
    required AppliedCalendarPlan plan,
    required DateTime start,
    required DateTime end,
    required StateSetter setModalState,
  }) async {
    Iterable<Workout> workouts;
    if (_rangeMode == 'cycles') {
      final indices = _computeSelectedPlanIndices();
      workouts = await _filterWorkoutsByPlanIndices(indices);
    } else {
      workouts = await _filterWorkoutsByRange(start, end);
    }
    final map = await _collectExerciseChoices(workouts);
    setModalState(() {
      _exerciseNames = map;
      if (_selectedExerciseIds.isEmpty) {
        _selectedExerciseIds.addAll(map.keys);
      } else {
        _selectedExerciseIds.removeWhere((id) => !map.containsKey(id));
      }
    });
  }

  // Warm-up caches for exercise IDs and names by fetching details once for provided workouts
  Future<void> _warmupExerciseCaches(Iterable<Workout> workouts) async {
    final workoutSvc = ref.read(workoutServiceProvider);
    for (final w in workouts) {
      final wid = w.id;
      if (wid == null) continue;
      if (_exerciseIdsByWorkout.containsKey(wid)) continue;
      try {
        final details = await workoutSvc.getWorkoutWithDetails(wid);
        final ids = <int>{};
        for (final inst in details.exerciseInstances) {
          ids.add(inst.exerciseListId);
          final dname = inst.exerciseDefinition?.name;
          if (dname != null && dname.isNotEmpty) {
            _exerciseNameCache[inst.exerciseListId] = dname;
          }
        }
        _exerciseIdsByWorkout[wid] = ids;
      } catch (_) {
        // ignore errors in warm-up; they'll be retried on demand
      }
    }
  }

  void _debounceRefreshSelection({
    required AppliedCalendarPlan plan,
    required DateTime start,
    required DateTime end,
    required StateSetter setModalState,
    Duration delay = const Duration(milliseconds: 220),
  }) {
    _rangeRefreshTimer?.cancel();
    _rangeRefreshTimer = Timer(delay, () {
      // ignore returned future
      _refreshExerciseNamesForSelection(
        plan: plan,
        start: start,
        end: end,
        setModalState: setModalState,
      );
    });
  }

  Future<Map<int, String>> _collectExerciseChoices(Iterable<Workout> workouts) async {
    final workoutSvc = ref.read(workoutServiceProvider);
    final result = <int, String>{};
    for (final w in workouts) {
      final wid = w.id;
      if (wid == null) continue;
      Set<int> ids;
      if (_exerciseIdsByWorkout.containsKey(wid)) {
        ids = _exerciseIdsByWorkout[wid]!;
      } else {
        try {
          final details = await workoutSvc.getWorkoutWithDetails(wid);
          ids = <int>{};
          for (final inst in details.exerciseInstances) {
            ids.add(inst.exerciseListId);
            final dname = inst.exerciseDefinition?.name;
            if (dname != null && dname.isNotEmpty) {
              _exerciseNameCache[inst.exerciseListId] = dname;
            }
          }
          _exerciseIdsByWorkout[wid] = ids;
        } catch (_) {
          continue;
        }
      }
      for (final id in ids) {
        final name = _exerciseNameCache[id];
        result[id] = name != null && name.isNotEmpty ? name : 'Exercise $id';
      }
    }
    return result;
  }

  Future<void> _openMassEditDialog() async {
    final plan = await ref.read(activePlanProvider.future);
    if (plan == null) {
      if (mounted) _showSnack(context, 'No active plan');
      return;
    }
    final start = (_selectedDay ?? DateTime.now()).monday;
    final end = plan.endDate;
    _microToGlobalIndices = _buildMicroToGlobalIndexMap(plan);
    // Warm-up caches once for all future workouts to speed up first use
    final futureWorkouts = await _filterWorkoutsByRange(start, end);
    await _warmupExerciseCaches(futureWorkouts);
    if (_exerciseNames.isEmpty) {
      _exerciseNames = await _collectExerciseChoices(futureWorkouts);
      if (_selectedExerciseIds.isEmpty) {
        _selectedExerciseIds.addAll(_exerciseNames.keys);
      }
    }
    await showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      showDragHandle: true,
      builder: (ctx) {
        return StatefulBuilder(builder: (ctx, setModalState) {
          return SafeArea(
            child: Padding(
              padding: EdgeInsets.only(
                left: 16,
                right: 16,
                top: 12,
                bottom: MediaQuery.of(ctx).viewInsets.bottom + 16,
              ),
              child: Column(
                mainAxisSize: MainAxisSize.min,
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  Text('Mass edit (from ${DateFormat('MMM d').format(start)} to ${DateFormat('MMM d').format(end)})', style: AppTextStyles.titleMedium),
                  const SizedBox(height: 8),
                  // Range selection: future vs meso/micro cycles
                  Row(
                    children: [
                      const Text('Range:'),
                      const SizedBox(width: 12),
                      DropdownButton<String>(
                        value: _rangeMode,
                        onChanged: (v) async {
                          setModalState(() { _rangeMode = v ?? 'future'; });
                          if (_rangeMode == 'cycles' && _selectedMicroIds.isEmpty) {
                            // preselect all microcycles by default
                            final allMicroIds = <int>{};
                            for (final m in plan.calendarPlan.mesocycles) {
                              for (final mc in m.microcycles) { allMicroIds.add(mc.id); }
                            }
                            setModalState(() { _selectedMicroIds
                              ..clear()
                              ..addAll(allMicroIds); });
                          }
                          _debounceRefreshSelection(plan: plan, start: start, end: end, setModalState: setModalState);
                        },
                        items: const [
                          DropdownMenuItem(value: 'future', child: Text('Future from week')),
                          DropdownMenuItem(value: 'cycles', child: Text('By meso/micro')),
                        ],
                      ),
                    ],
                  ),
                  if (_rangeMode == 'cycles') ...[
                    const SizedBox(height: 6),
                    // Mesocycle/Microcycle selection UI
                    SizedBox(
                      height: 200,
                      child: Scrollbar(
                        child: ListView(
                          children: plan.calendarPlan.mesocycles
                              .map((meso) {
                                final mesoChecked = meso.microcycles.every((mc) => _selectedMicroIds.contains(mc.id));
                                return ExpansionTile(
                                  title: Row(
                                    children: [
                                      Checkbox(
                                        value: mesoChecked,
                                        onChanged: (v) async {
                                          setModalState(() {
                                            if (v == true) {
                                              for (final mc in meso.microcycles) { _selectedMicroIds.add(mc.id); }
                                            } else {
                                              for (final mc in meso.microcycles) { _selectedMicroIds.remove(mc.id); }
                                            }
                                          });
                                          _debounceRefreshSelection(plan: plan, start: start, end: end, setModalState: setModalState);
                                        },
                                      ),
                                      Expanded(child: Text(meso.name)),
                                    ],
                                  ),
                                  children: meso.microcycles.map((mc) {
                                    final checked = _selectedMicroIds.contains(mc.id);
                                    return CheckboxListTile(
                                      dense: true,
                                      value: checked,
                                      onChanged: (v) async {
                                        setModalState(() {
                                          if (v == true) { _selectedMicroIds.add(mc.id); } else { _selectedMicroIds.remove(mc.id); }
                                        });
                                        _debounceRefreshSelection(plan: plan, start: start, end: end, setModalState: setModalState);
                                      },
                                      title: Text(mc.name),
                                      controlAffinity: ListTileControlAffinity.leading,
                                    );
                                  }).toList(),
                                );
                              })
                              .toList(),
                        ),
                      ),
                    ),
                  ],
                  Wrap(
                    spacing: 8,
                    runSpacing: 8,
                    children: _exerciseNames.entries.map((e) {
                      final selected = _selectedExerciseIds.contains(e.key);
                      return FilterChip(
                        label: Text(e.value),
                        selected: selected,
                        onSelected: (val) {
                          setModalState(() {
                            if (val) {
                              _selectedExerciseIds.add(e.key);
                            } else {
                              _selectedExerciseIds.remove(e.key);
                            }
                          });
                        },
                      );
                    }).toList(),
                  ),
                  const SizedBox(height: 12),
                  Row(
                    children: [
                      Switch(value: _useIntensity, onChanged: (v) => setModalState(() => _useIntensity = v)),
                      const SizedBox(width: 8),
                      const Text('Intensity %'),
                      const SizedBox(width: 8),
                      DropdownButton<String>(
                        value: _intensityMode,
                        onChanged: _useIntensity
                            ? (v) => setModalState(() => _intensityMode = v ?? 'set')
                            : null,
                        items: const [
                          DropdownMenuItem(value: 'set', child: Text('Set')),
                          DropdownMenuItem(value: 'offset', child: Text('Offset')),
                          DropdownMenuItem(value: 'scale', child: Text('Scale')),
                        ],
                      ),
                      const SizedBox(width: 12),
                      Expanded(
                        child: TextField(
                          controller: _intensityCtrl,
                          enabled: _useIntensity,
                          keyboardType: const TextInputType.numberWithOptions(decimal: true),
                          decoration: InputDecoration(
                            hintText: _intensityMode == 'set'
                                ? 'e.g. 75'
                                : (_intensityMode == 'offset' ? '+/- % (e.g. -2)' : '× factor (e.g. 1.05)'),
                          ),
                        ),
                      ),
                    ],
                  ),
                  Row(
                    children: [
                      Switch(value: _useRpe, onChanged: (v) => setModalState(() => _useRpe = v)),
                      const SizedBox(width: 8),
                      const Text('RPE'),
                      const SizedBox(width: 8),
                      DropdownButton<String>(
                        value: _rpeMode,
                        onChanged: _useRpe
                            ? (v) => setModalState(() => _rpeMode = v ?? 'set')
                            : null,
                        items: const [
                          DropdownMenuItem(value: 'set', child: Text('Set')),
                          DropdownMenuItem(value: 'offset', child: Text('Offset')),
                        ],
                      ),
                      const SizedBox(width: 12),
                      Expanded(
                        child: TextField(
                          controller: _rpeCtrl,
                          enabled: _useRpe,
                          keyboardType: const TextInputType.numberWithOptions(decimal: true),
                          decoration: const InputDecoration(hintText: 'e.g. 8'),
                        ),
                      ),
                    ],
                  ),
                  Row(
                    children: [
                      Switch(value: _useReps, onChanged: (v) => setModalState(() => _useReps = v)),
                      const SizedBox(width: 8),
                      const Text('Reps'),
                      const SizedBox(width: 8),
                      DropdownButton<String>(
                        value: _repsMode,
                        onChanged: _useReps
                            ? (v) => setModalState(() => _repsMode = v ?? 'set')
                            : null,
                        items: const [
                          DropdownMenuItem(value: 'set', child: Text('Set')),
                          DropdownMenuItem(value: 'offset', child: Text('Offset')),
                          DropdownMenuItem(value: 'scale', child: Text('Scale')),
                        ],
                      ),
                      const SizedBox(width: 12),
                      Expanded(
                        child: TextField(
                          controller: _repsCtrl,
                          enabled: _useReps,
                          keyboardType: TextInputType.number,
                          decoration: InputDecoration(
                            hintText: _repsMode == 'set'
                                ? 'e.g. 5'
                                : (_repsMode == 'offset' ? '+/- reps (e.g. +1)' : '× factor (e.g. 0.9)'),
                          ),
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 8),
                  Row(
                    children: [
                      const Text('Recalc target:'),
                      const SizedBox(width: 12),
                      DropdownButton<String>(
                        value: _recalcTarget,
                        onChanged: (v) => setModalState(() => _recalcTarget = v ?? 'auto'),
                        items: const [
                          DropdownMenuItem(value: 'auto', child: Text('Auto')),
                          DropdownMenuItem(value: 'reps', child: Text('Reps')),
                          DropdownMenuItem(value: 'rpe', child: Text('RPE')),
                          DropdownMenuItem(value: 'intensity', child: Text('Intensity')),
                        ],
                      ),
                    ],
                  ),
                  if (_recalcTarget == 'rpe')
                    Row(
                      children: [
                        const Text('Validator:'),
                        const SizedBox(width: 12),
                        DropdownButton<String>(
                          value: _fixStrategy,
                          onChanged: (v) => setModalState(() => _fixStrategy = v ?? 'none'),
                          items: const [
                            DropdownMenuItem(value: 'none', child: Text('None')),
                            DropdownMenuItem(value: 'fixReps', child: Text('Fix Reps')),
                            DropdownMenuItem(value: 'fixIntensity', child: Text('Fix Intensity')),
                          ],
                        ),
                      ],
                    ),
                  const SizedBox(height: 12),
                  Row(
                    mainAxisAlignment: MainAxisAlignment.end,
                    children: [
                      TextButton(onPressed: () => Navigator.of(ctx).pop(), child: const Text('Cancel')),
                      const SizedBox(width: 8),
                      FilledButton(
                        onPressed: () async {
                          if (_selectedExerciseIds.isEmpty) {
                            _showSnack(context, 'Select at least one exercise');
                            return;
                          }
                          if (!(_useIntensity || _useRpe || _useReps)) {
                            _showSnack(context, 'Select at least one parameter');
                            return;
                          }
                          Navigator.of(ctx).pop();
                          Set<int>? planIdxFilter;
                          if (_rangeMode == 'cycles') {
                            planIdxFilter = _computeSelectedPlanIndices();
                          }
                          await _applyMassEdits(start, end, planIndexFilter: planIdxFilter);
                        },
                        child: const Text('Apply'),
                      ),
                    ],
                  ),
                ],
              ),
            ),
          );
        });
      },
    );
    // Clear caches when dialog is closed to avoid stale memory and force fresh warm-up next time
    setState(() {
      _exerciseIdsByWorkout.clear();
      _exerciseNameCache.clear();
    });
  }

  Future<void> _applyMassEdits(DateTime start, DateTime end, {Set<int>? planIndexFilter}) async {
    if (_isApplying) return;
    setState(() => _isApplying = true);
    final plan = await ref.read(activePlanProvider.future);
    if (plan == null) {
      if (mounted) _showSnack(context, 'No active plan');
      setState(() => _isApplying = false);
      return;
    }
    final rpeSvc = ref.read(rpeServiceProvider);
    final workoutSvc = ref.read(workoutServiceProvider);
    final oneRmByExercise = <int, double>{};
    for (final um in plan.userMaxes) {
      oneRmByExercise[um.exerciseId] = um.maxWeight.toDouble();
    }
    double? parseDouble(String s) => double.tryParse(s.replaceAll(',', '.').trim());
    final intensityInput = _useIntensity ? parseDouble(_intensityCtrl.text) : null;
    final rpeInput = _useRpe ? parseDouble(_rpeCtrl.text) : null;
    final repsInput = _useReps ? parseDouble(_repsCtrl.text) : null;
    try {
      final workouts = (planIndexFilter != null && planIndexFilter.isNotEmpty)
          ? await _filterWorkoutsByPlanIndices(planIndexFilter)
          : await _filterWorkoutsByRange(start, end);
      int updatedSets = 0;
      for (final w in workouts) {
        if (w.isCompleted || w.isLiveInProgress) continue;
        if (w.id == null) continue;
        final details = await workoutSvc.getWorkoutWithDetails(w.id!);
        for (final inst in details.exerciseInstances) {
          if (!_selectedExerciseIds.contains(inst.exerciseListId)) continue;
          final oneRm = oneRmByExercise[inst.exerciseListId];
          for (int i = 0; i < inst.sets.length; i++) {
            final set = inst.sets[i];
            final baseReps = set.reps;
            final baseRpe = set.rpe;
            double? baseIntensity;
            if (oneRm != null && oneRm > 0 && set.weight > 0) {
              baseIntensity = (set.weight / oneRm) * 100.0;
            }
            int? reps = baseReps;
            double? intensity;
            double? rpe = baseRpe;

            if (_useReps && repsInput != null) {
              if (_repsMode == 'set') {
                reps = repsInput.round().clampInt(1, 100);
              } else if (_repsMode == 'offset') {
                reps = (baseReps + repsInput).round().clampInt(1, 100);
              } else {
                reps = (baseReps * repsInput).round().clampInt(1, 100);
              }
            }

            if (_useRpe && rpeInput != null) {
              if (_rpeMode == 'set') {
                rpe = rpeInput.clampDouble(1, 10);
              } else {
                if (baseRpe != null) {
                  rpe = (baseRpe + rpeInput).clampDouble(1, 10);
                }
              }
            }

            if (_useIntensity && intensityInput != null) {
              if (_intensityMode == 'set') {
                intensity = intensityInput.clampDouble(30, 100);
              } else {
                double? b = baseIntensity;
                if (b == null && baseRpe != null && baseReps != null) {
                  final calc = await rpeSvc.calculateIntensity(baseReps, baseRpe);
                  if (calc != null) b = calc;
                }
                if (b != null) {
                  if (_intensityMode == 'offset') {
                    intensity = (b + intensityInput).clampDouble(30, 100);
                  } else {
                    intensity = (b * intensityInput).clampDouble(30, 100);
                  }
                }
              }
            }

            final bool chI = intensity != null && (baseIntensity == null || (intensity - baseIntensity).abs() > 0.001);
            final bool chE = rpe != null && (baseRpe == null || (rpe - baseRpe).abs() > 0.001);
            final bool chV = reps != null && reps != baseReps;

            String recalc = _recalcTarget;
            if (recalc == 'auto') {
              if ((chI || chE) && !chV) {
                recalc = 'reps';
              } else if (chV && !(chI || chE)) {
                recalc = 'intensity';
              } else if (chI && chV && !chE) {
                recalc = 'rpe';
              } else {
                recalc = 'none';
              }
            }

            if (recalc == 'reps') {
              if (intensity != null && rpe != null) {
                final calc = await rpeSvc.calculateReps(intensity, rpe);
                if (calc != null) {
                  reps = calc.clampInt(1, 100);
                }
              }
            } else if (recalc == 'rpe') {
              if (intensity != null && reps != null) {
                double? rr = await rpeSvc.calculateRpe(intensity, reps);
                if (rr == null) {
                  if (_fixStrategy == 'fixReps') {
                    int bestReps = reps;
                    double? bestRpe;
                    int bestDelta = 1 << 30;
                    int start = reps - 6; if (start < 1) start = 1;
                    int end = reps + 6; if (end > 100) end = 100;
                    for (int cand = start; cand <= end; cand++) {
                      final r2 = await rpeSvc.calculateRpe(intensity, cand);
                      if (r2 != null) {
                        final d = (cand - reps).abs();
                        if (d < bestDelta) { bestDelta = d; bestReps = cand; bestRpe = r2; if (d == 0) break; }
                      }
                    }
                    if (bestRpe != null) { reps = bestReps; rpe = bestRpe; }
                  } else if (_fixStrategy == 'fixIntensity' && reps != null) {
                    final ii = await rpeSvc.calculateIntensity(reps, 10);
                    if (ii != null) {
                      intensity = ii.clampDouble(30, 100);
                      final r2 = await rpeSvc.calculateRpe(intensity, reps);
                      if (r2 != null) rpe = r2;
                    }
                  }
                } else {
                  rpe = rr;
                }
              }
            } else if (recalc == 'intensity') {
              if (reps != null && rpe != null) {
                final ii = await rpeSvc.calculateIntensity(reps, rpe);
                if (ii != null) intensity = ii.clampDouble(30, 100);
              }
            }

            double? newWeight;
            if (intensity != null && oneRm != null && oneRm > 0) {
              newWeight = (oneRm * (intensity / 100.0)).roundTo2p5();
            }
            final bool changeReps = ((_useReps || recalc == 'reps') && reps != null && reps != set.reps);
            final bool changeRpe = ((_useRpe || recalc == 'rpe') && rpe != null && (set.rpe == null || (rpe - (set.rpe ?? 0)).abs() > 0.001));
            final bool changeWeight = ((_useIntensity || recalc == 'intensity' || (intensity != null)) && newWeight != null && (newWeight - set.weight).abs() > 0.001);
            if (!(changeReps || changeRpe || changeWeight)) continue;
            final instanceId = inst.id;
            final setId = set.id;
            if (instanceId != null && setId != null) {
              await workoutSvc.updateExerciseSet(
                instanceId: instanceId,
                setId: setId,
                reps: changeReps ? reps : null,
                weight: changeWeight ? newWeight : null,
                rpe: changeRpe ? rpe : null,
              );
              updatedSets++;
            } else {
              final newSets = List<ExerciseSetDto>.from(inst.sets);
              newSets[i] = set.copyWith(
                reps: changeReps ? (reps ?? set.reps) : set.reps,
                rpe: changeRpe ? (rpe ?? set.rpe) : set.rpe,
                weight: changeWeight ? (newWeight ?? set.weight) : set.weight,
              );
              await workoutSvc.updateExerciseInstance(inst.copyWith(sets: newSets));
              updatedSets++;
            }
          }
        }
      }
      if (mounted) _showSnack(context, 'Updated $updatedSets sets');
      ref.invalidate(activePlanWorkoutsProvider);
      ref.invalidate(activePlanAnalyticsProvider);
    } catch (e) {
      if (mounted) _showSnack(context, 'Failed: $e');
    } finally {
      if (mounted) setState(() => _isApplying = false);
    }
  }

  Future<void> _openReplaceDialog() async {
    final plan = await ref.read(activePlanProvider.future);
    if (plan == null) {
      if (mounted) _showSnack(context, 'No active plan');
      return;
    }
    final start = (_selectedDay ?? DateTime.now()).monday;
    final end = plan.endDate;
    if (_exerciseNames.isEmpty) {
      final list = await _filterWorkoutsByRange(start, end);
      _exerciseNames = await _collectExerciseChoices(list);
    }

    Set<int> selectedSource = <int>{};
    ExerciseDefinition? target;
    bool preserveIntensity = true; // default per user preference

    await showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      showDragHandle: true,
      builder: (ctx) {
        return StatefulBuilder(builder: (ctx, setModalState) {
          return SafeArea(
            child: Padding(
              padding: EdgeInsets.only(
                left: 16,
                right: 16,
                top: 12,
                bottom: MediaQuery.of(ctx).viewInsets.bottom + 16,
              ),
              child: Column(
                mainAxisSize: MainAxisSize.min,
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  Text('Replace exercises (from ${DateFormat('MMM d').format(start)} to ${DateFormat('MMM d').format(end)})', style: AppTextStyles.titleMedium),
                  const SizedBox(height: 8),
                  Text('Select source exercises:', style: AppTextStyles.titleSmall),
                  const SizedBox(height: 6),
                  Wrap(
                    spacing: 8,
                    runSpacing: 8,
                    children: _exerciseNames.entries.map((e) {
                      final selected = selectedSource.contains(e.key);
                      return FilterChip(
                        label: Text(e.value),
                        selected: selected,
                        onSelected: (val) {
                          setModalState(() {
                            if (val) {
                              selectedSource.add(e.key);
                            } else {
                              selectedSource.remove(e.key);
                            }
                          });
                        },
                      );
                    }).toList(),
                  ),
                  const SizedBox(height: 12),
                  ListTile(
                    contentPadding: EdgeInsets.zero,
                    title: Text(target?.name ?? 'Select target exercise'),
                    trailing: const Icon(Icons.chevron_right),
                    onTap: () async {
                      final res = await Navigator.of(ctx).push(
                        MaterialPageRoute(builder: (_) => const ExerciseSelectionScreen()),
                      );
                      if (res is ExerciseDefinition) {
                        setModalState(() => target = res);
                      }
                    },
                  ),
                  Row(
                    children: [
                      Switch(
                        value: preserveIntensity,
                        onChanged: (v) => setModalState(() => preserveIntensity = v),
                      ),
                      const SizedBox(width: 8),
                      const Text('Preserve intensity via 1RM'),
                    ],
                  ),
                  const SizedBox(height: 12),
                  Row(
                    mainAxisAlignment: MainAxisAlignment.end,
                    children: [
                      TextButton(onPressed: () => Navigator.of(ctx).pop(), child: const Text('Cancel')),
                      const SizedBox(width: 8),
                      FilledButton(
                        onPressed: () async {
                          if (selectedSource.isEmpty) {
                            _showSnack(context, 'Select at least one source exercise');
                            return;
                          }
                          if (target?.id == null) {
                            _showSnack(context, 'Select a target exercise');
                            return;
                          }
                          Navigator.of(ctx).pop();
                          await _confirmAndApplyReplace(
                            sourceExerciseIds: selectedSource,
                            target: target!,
                            start: start,
                            end: end,
                            preserveIntensity: preserveIntensity,
                          );
                        },
                        child: const Text('Apply'),
                      ),
                    ],
                  ),
                ],
              ),
            ),
          );
        });
      },
    );
  }

  Future<void> _confirmAndApplyReplace({
    required Set<int> sourceExerciseIds,
    required ExerciseDefinition target,
    required DateTime start,
    required DateTime end,
    required bool preserveIntensity,
  }) async {
    final preview = await _simulateReplaceDiffForActivePlan(sourceExerciseIds, start, end);
    final totalEx = preview['instances'] ?? 0;
    final totalSets = preview['sets'] ?? 0;
    if (!mounted) return;
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Preview replacement'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('Target: ${target.name}'),
            Text('Exercises to replace: $totalEx'),
            Text('Sets affected: $totalSets'),
          ],
        ),
        actions: [
          TextButton(onPressed: () => Navigator.of(ctx).pop(false), child: const Text('Cancel')),
          FilledButton(onPressed: () => Navigator.of(ctx).pop(true), child: const Text('Apply')),
        ],
      ),
    );
    if (confirmed == true) {
      await _applyExerciseReplace(
        sourceExerciseIds: sourceExerciseIds,
        target: target,
        start: start,
        end: end,
        preserveIntensity: preserveIntensity,
      );
    }
  }

  Future<Map<String, int>> _simulateReplaceDiffForActivePlan(Set<int> sourceExerciseIds, DateTime start, DateTime end) async {
    final workoutSvc = ref.read(workoutServiceProvider);
    final workouts = await _filterWorkoutsByRange(start, end);
    int instCount = 0, setCount = 0;
    for (final w in workouts) {
      if (w.isCompleted || w.isLiveInProgress) continue;
      if (w.id == null) continue;
      try {
        final details = await workoutSvc.getWorkoutWithDetails(w.id!);
        for (final inst in details.exerciseInstances) {
          if (sourceExerciseIds.contains(inst.exerciseListId)) {
            instCount += 1;
            setCount += inst.sets.length;
          }
        }
      } catch (_) {}
    }
    return {'instances': instCount, 'sets': setCount};
  }

  Future<void> _applyExerciseReplace({
    required Set<int> sourceExerciseIds,
    required ExerciseDefinition target,
    required DateTime start,
    required DateTime end,
    required bool preserveIntensity,
  }) async {
    if (_isApplying) return;
    setState(() => _isApplying = true);
    try {
      final plan = await ref.read(activePlanProvider.future);
      if (plan == null) {
        if (mounted) _showSnack(context, 'No active plan');
        return;
      }
      final rpeSvc = ref.read(rpeServiceProvider);
      final workoutSvc = ref.read(workoutServiceProvider);
      final oneRmByExercise = <int, double>{};
      for (final um in plan.userMaxes) {
        oneRmByExercise[um.exerciseId] = um.maxWeight.toDouble();
      }
      _logger.d('Replace: have ${plan.userMaxes.length} userMaxes; keys=${oneRmByExercise.keys.toList()}');
      double? targetOneRm = target.id != null ? oneRmByExercise[target.id!] : null;
      _logger.d('Replace: target exerciseId=${target.id}; mapped 1RM from plan=$targetOneRm');
      if (preserveIntensity) {
        if (targetOneRm == null || targetOneRm <= 0) {
          if (target.id != null) {
            final fetched = await _fetchUserMax1RmByExerciseId(target.id!);
            _logger.d('Replace: fetched 1RM via API for ${target.id} = $fetched');
            if (fetched != null && fetched > 0) {
              targetOneRm = fetched;
              oneRmByExercise[target.id!] = fetched;
            }
          }
          if (targetOneRm == null || targetOneRm <= 0) {
            targetOneRm = await _promptForOneRm(target);
          }
          if (targetOneRm == null) {
            if (mounted) {
              _showSnack(context, 'Replacement cancelled: 1RM required');
            }
            return;
          }
          if (target.id != null) {
            oneRmByExercise[target.id!] = targetOneRm;
          }
        }
      }

      int replacedInstances = 0;
      int updatedSets = 0;
      final workouts = await _filterWorkoutsByRange(start, end);
      for (final w in workouts) {
        if (w.isCompleted || w.isLiveInProgress) continue;
        if (w.id == null) continue;
        final details = await workoutSvc.getWorkoutWithDetails(w.id!);
        for (final inst in details.exerciseInstances) {
          if (!sourceExerciseIds.contains(inst.exerciseListId)) continue;
          final double? sourceOneRm = oneRmByExercise[inst.exerciseListId];
          final newSets = <ExerciseSetDto>[];
          for (final set in inst.sets) {
            double newWeight = set.weight;
            if (preserveIntensity) {
              double? intensity; // percent
              if (sourceOneRm != null && sourceOneRm > 0 && set.weight > 0) {
                intensity = (set.weight / sourceOneRm) * 100.0;
              } else if (set.rpe != null) {
                // derive via RPE table if reps+RPE are known
                final calc = await rpeSvc.calculateIntensity(set.reps, set.rpe!);
                if (calc != null) intensity = calc;
              }
              if (intensity != null && targetOneRm != null && targetOneRm > 0) {
                newWeight = (targetOneRm * (intensity / 100.0)).roundTo2p5();
              }
            }
            newSets.add(set.copyWith(weight: newWeight));
          }
          final updated = inst.copyWith(
            exerciseListId: target.id!,
            sets: newSets,
          );
          await workoutSvc.updateExerciseInstance(updated);
          replacedInstances++;
          updatedSets += newSets.length;
        }
      }
      if (mounted) _showSnack(context, 'Replaced $replacedInstances exercises, updated $updatedSets sets');
      ref.invalidate(activePlanWorkoutsProvider);
    } catch (e) {
      if (mounted) _showSnack(context, 'Replace failed: $e');
    } finally {
      if (mounted) setState(() => _isApplying = false);
    }
  }

  Future<double?> _promptForOneRm(ExerciseDefinition target) async {
    final ctrl = TextEditingController();
    String? error;
    final result = await showDialog<double?>(
      context: context,
      barrierDismissible: false,
      builder: (ctx) {
        return StatefulBuilder(
          builder: (ctx, setState) {
            return AlertDialog(
              title: Text('Enter 1RM for ${target.name}'),
              content: Column(
                mainAxisSize: MainAxisSize.min,
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  TextField(
                    controller: ctrl,
                    keyboardType: const TextInputType.numberWithOptions(decimal: true),
                    decoration: InputDecoration(
                      labelText: '1RM (kg)',
                      hintText: 'e.g. 120',
                      errorText: error,
                    ),
                  ),
                  const SizedBox(height: 8),
                  const Text('Введите ваш текущий максимум для этого упражнения.'),
                ],
              ),
              actions: [
                TextButton(
                  onPressed: () => Navigator.of(ctx).pop(null),
                  child: const Text('Cancel'),
                ),
                FilledButton(
                  onPressed: () {
                    final parsed = double.tryParse(ctrl.text.replaceAll(',', '.').trim());
                    if (parsed == null || parsed <= 0) {
                      setState(() => error = 'Введите число > 0');
                      return;
                    }
                    Navigator.of(ctx).pop(parsed);
                  },
                  child: const Text('Save'),
                ),
              ],
            );
          },
        );
      },
    );
    ctrl.dispose();
    return result;
  }

  Future<double?> _fetchUserMax1RmByExerciseId(int exerciseId) async {
    try {
      final api = ref.read(apiClientProvider);
      final resp = await api.get(
        ApiConfig.getByExerciseEndpoint(exerciseId.toString()),
        context: 'ActivePlanScreen.fetchUserMax',
      );
      if (resp is List) {
        double best = 0;
        for (final item in resp) {
          final map = item is Map<String, dynamic>
              ? item
              : Map<String, dynamic>.from(item as Map);
          final true1rm = (map['true_1rm'] as num?)?.toDouble() ?? 0.0;
          final maxW = (map['max_weight'] as num?)?.toDouble() ?? 0.0;
          final candidate = true1rm > 0 ? true1rm : maxW;
          if (candidate > best) best = candidate;
        }
        _logger.d('FetchUserMax: best for exercise $exerciseId = $best');
        return best > 0 ? best : null;
      }
    } catch (e) {
      _logger.e('FetchUserMax failed for exercise $exerciseId: $e');
    }
    return null;
  }

  Future<void> _shiftScheduleFromSelectedWeek({required int days}) async {
    if (_isApplying) return;
    setState(() => _isApplying = true);
    try {
      final plan = await ref.read(activePlanProvider.future);
      if (plan == null) {
        if (mounted) _showSnack(context, 'No active plan');
        return;
      }
      final start = (_selectedDay ?? DateTime.now()).monday;
      final end = plan.endDate;
      final workoutSvc = ref.read(workoutServiceProvider);
      final targets = await _filterWorkoutsByRange(start, end);
      int shifted = 0;
      for (final w in targets) {
        if (w.isCompleted || w.isLiveInProgress) continue;
        if (w.scheduledFor == null || w.id == null) continue;
        final newDate = w.scheduledFor!.add(Duration(days: days));
        final updated = w.copyWith(scheduledFor: newDate);
        await workoutSvc.updateWorkout(updated);
        shifted++;
      }
      if (mounted) _showSnack(context, 'Shifted $shifted workouts by +$days day(s)');
      ref.invalidate(activePlanWorkoutsProvider);
    } catch (e) {
      if (mounted) _showSnack(context, 'Shift failed: $e');
    } finally {
      if (mounted) setState(() => _isApplying = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final eventsByDay = ref.watch(workoutsByDayProvider);
    final planAsync = ref.watch(activePlanProvider);

    return Scaffold(
      backgroundColor: AppColors.background,
      appBar: AppBar(
        title: const Text('Active Plan'),
        backgroundColor: Colors.white,
        elevation: 0,
        actions: [
          IconButton(
            tooltip: 'Mass edit',
            icon: const Icon(Icons.tune, color: AppColors.textPrimary),
            onPressed: _openMassEditDialog,
          ),
          IconButton(
            tooltip: 'Replace exercises',
            icon: const Icon(Icons.swap_horiz, color: AppColors.textPrimary),
            onPressed: _openReplaceDialog,
          ),
          PopupMenuButton<String>(
            onSelected: (value) async {
              if (value == 'shift_plus_1') {
                await _shiftScheduleFromSelectedWeek(days: 1);
              }
            },
            itemBuilder: (ctx) => const [
              PopupMenuItem(
                value: 'shift_plus_1',
                child: Text('Shift future +1 day (week→end)'),
              ),
            ],
          ),
        ],
      ),
      body: planAsync.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (e, st) => Center(child: Text('Error: $e')),
        data: (plan) {
          if (plan == null) {
            return const Center(child: Text('No active plan'));
          }
          final analyticsAsync = ref.watch(activePlanAnalyticsProvider);
          return Column(
            children: [
              _buildCalendar(eventsByDay),
              const SizedBox(height: 8),
              _buildAnalyticsAsyncSection(analyticsAsync),
              const SizedBox(height: 8),
              _buildDayHeader(),
              Expanded(child: _buildDayList(eventsByDay)),
            ],
          );
        },
      ),
    );
  }

  Widget _buildAnalyticsAsyncSection(AsyncValue<PlanAnalyticsResponse?> analyticsAsync) {
    return analyticsAsync.when(
      loading: () => const SizedBox(
        height: 240,
        child: Center(child: CircularProgressIndicator()),
      ),
      error: (error, stack) => SizedBox(
        height: 240,
        child: Center(child: Text('Failed to load analytics: $error')),
      ),
      data: (resp) {
        final points = _mapAnalyticsResponse(resp);
        final totals = resp?.totals;
        return _buildActiveAnalyticsSection(points, totals: totals);
      },
    );
  }

  Widget _buildCalendar(Map<DateTime, List<Workout>> eventsByDay) {
    return Container(
      color: Colors.white,
      child: TableCalendar<Workout>(
        firstDay: DateTime.utc(2018, 1, 1),
        lastDay: DateTime.utc(2100, 12, 31),
        focusedDay: _focusedDay,
        startingDayOfWeek: StartingDayOfWeek.monday,
        selectedDayPredicate: (day) => isSameDay(_selectedDay, day),
        eventLoader: (day) => eventsByDay[_dateOnly(day)] ?? const <Workout>[],
        calendarFormat: CalendarFormat.month,
        onDaySelected: (selectedDay, focusedDay) {
          setState(() {
            _selectedDay = _dateOnly(selectedDay);
            _focusedDay = focusedDay;
          });
          _openDaySheet();
        },
        calendarBuilders: CalendarBuilders(
          markerBuilder: (context, date, events) {
            if (events.isEmpty) return const SizedBox.shrink();
            final List<Workout> list = events.cast<Workout>();
            final counts = _statusCounts(list);
            return Padding(
              padding: const EdgeInsets.only(top: 30.0),
              child: Row(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  if (counts.completed > 0) _dot(Colors.green),
                  if (counts.inProgress > 0) _dot(AppColors.primary),
                  if (counts.planned > 0) _dot(Colors.redAccent),
                ],
              ),
            );
          },
        ),
      ),
    );
  }

  Widget _buildDayHeader() {
    final day = _selectedDay ?? _dateOnly(DateTime.now());
    final title = DateFormat('EEEE, MMM d, yyyy').format(day);
    return Padding(
      padding: const EdgeInsets.fromLTRB(16, 4, 16, 4),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Text(title, style: AppTextStyles.titleMedium),
          TextButton(
            onPressed: _openDaySheet,
            child: const Text('View day'),
          ),
        ],
      ),
    );
  }

  Widget _buildDayList(Map<DateTime, List<Workout>> eventsByDay) {
    final day = _selectedDay ?? _dateOnly(DateTime.now());
    final workouts = eventsByDay[day] ?? const <Workout>[];
    if (workouts.isEmpty) {
      return const Center(child: Text('No workouts'));
    }
    return ListView.separated(
      padding: const EdgeInsets.fromLTRB(16, 0, 16, 16),
      itemBuilder: (ctx, i) {
        final w = workouts[i];
        final st = _statusOf(w);
        return Container(
          decoration: BoxDecoration(
            color: Colors.white,
            borderRadius: BorderRadius.circular(16),
            boxShadow: AppShadows.sm,
          ),
          child: ListTile(
            title: Text(w.name, style: AppTextStyles.titleSmall.copyWith(fontWeight: FontWeight.w600)),
            subtitle: Text(_timeOrDate(w)),
            trailing: Container(
              padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
              decoration: BoxDecoration(
                color: st.background,
                borderRadius: BorderRadius.circular(20),
              ),
              child: Text(st.label, style: TextStyle(color: st.textColor, fontWeight: FontWeight.w600)),
            ),
            onTap: () async {
              if (w.id != null) {
                await Navigator.of(context).push(
                  MaterialPageRoute(builder: (_) => WorkoutDetailScreen(workoutId: w.id!)),
                );
                if (!mounted) return;
                ref.invalidate(activePlanWorkoutsProvider);
                ref.invalidate(activePlanAnalyticsProvider);
              }
            },
          ),
        );
      },
      separatorBuilder: (_, __) => const SizedBox(height: 12),
      itemCount: workouts.length,
    );
  }

  void _openDaySheet() {
    final eventsByDay = ref.read(workoutsByDayProvider);
    final day = _selectedDay ?? _dateOnly(DateTime.now());
    final workouts = eventsByDay[day] ?? const <Workout>[];
    showModalBottomSheet(
      context: context,
      showDragHandle: true,
      isScrollControlled: true,
      builder: (ctx) {
        return SafeArea(
          child: Padding(
            padding: const EdgeInsets.fromLTRB(16, 8, 16, 16),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                Text(DateFormat('EEEE, MMM d, yyyy').format(day), style: AppTextStyles.titleMedium),
                const SizedBox(height: 8),
                if (workouts.isEmpty)
                  const Padding(
                    padding: EdgeInsets.symmetric(vertical: 24),
                    child: Center(child: Text('No workouts')),
                  )
                else
                  Flexible(
                    child: ListView.separated(
                      shrinkWrap: true,
                      itemBuilder: (ctx, i) {
                        final w = workouts[i];
                        final st = _statusOf(w);
                        return ListTile(
                          leading: CircleAvatar(backgroundColor: st.dotColor, radius: 6),
                          title: Text(w.name),
                          subtitle: Text(_timeOrDate(w)),
                          trailing: IconButton(
                            icon: const Icon(Icons.open_in_new),
                            onPressed: () async {
                              if (w.id != null) {
                                await Navigator.of(context).push(
                                  MaterialPageRoute(builder: (_) => WorkoutDetailScreen(workoutId: w.id!)),
                                );
                                if (!mounted) return;
                                ref.invalidate(activePlanWorkoutsProvider);
                                ref.invalidate(activePlanAnalyticsProvider);
                              }
                            },
                          ),
                          onTap: () async {
                            if (w.id != null) {
                              await Navigator.of(context).push(
                                MaterialPageRoute(builder: (_) => WorkoutDetailScreen(workoutId: w.id!)),
                              );
                              if (!mounted) return;
                              ref.invalidate(activePlanWorkoutsProvider);
                              ref.invalidate(activePlanAnalyticsProvider);
                            }
                          },
                        );
                      },
                      separatorBuilder: (_, __) => const Divider(height: 1),
                      itemCount: workouts.length,
                    ),
                  ),
              ],
            ),
          ),
        );
      },
    );
  }

  String _timeOrDate(Workout w) {
    final dt = w.scheduledFor;
    if (dt == null) return 'Unscheduled';
    return DateFormat('MMM d, yyyy – HH:mm').format(dt);
  }

  _StatusView _statusOf(Workout w) {
    final completed = (w.status?.toLowerCase() == 'completed') || (w.completedAt != null);
    final inProgress = (w.startedAt != null) && (w.completedAt == null);
    if (completed) {
      return _StatusView('Completed', const Color(0xFFEFF8F2), Colors.green, Colors.green);
    } else if (inProgress) {
      return _StatusView('In Progress', const Color(0xFFEAEFFF), AppColors.primary, AppColors.primary);
    } else {
      return _StatusView('Planned', const Color(0xFFFFEBEE), Colors.redAccent, Colors.redAccent);
    }
  }

  ({int planned, int inProgress, int completed}) _statusCounts(List<Workout> list) {
    int p = 0, i = 0, c = 0;
    for (final w in list) {
      final completedB = (w.status?.toLowerCase() == 'completed') || (w.completedAt != null);
      final inProgressB = (w.startedAt != null) && (w.completedAt == null);
      if (completedB) c++; else if (inProgressB) i++; else p++;
    }
    return (planned: p, inProgress: i, completed: c);
  }

  Widget _dot(Color color) {
    return Container(
      margin: const EdgeInsets.symmetric(horizontal: 1.5),
      width: 6,
      height: 6,
      decoration: BoxDecoration(color: color, shape: BoxShape.circle),
    );
  }
}

class _APPlanAnalyticsPoint {
  final int order;
  final String label;
  final Map<String, double> values;
  const _APPlanAnalyticsPoint({required this.order, required this.label, required this.values});
}

extension _APMetricLabels on _ActivePlanScreenState {
  String _metricLabel(String m) {
    switch (m) {
      case 'sets_count':
        return 'Сеты';
      case 'volume_sum':
        return 'Повторения';
      case 'intensity_avg':
        return 'Интенсивность (ср.)';
      case 'effort_avg':
        return 'Усилие (RPE ср.)';
      default:
        return m;
    }
  }
}

extension _APAnalytics on _ActivePlanScreenState {
  List<_APPlanAnalyticsPoint> _mapAnalyticsResponse(PlanAnalyticsResponse? resp) {
    if (resp == null) return const [];
    final items = List.of(resp.items);
    items.sort((a, b) {
      final ao = a.orderIndex ?? 1 << 30;
      final bo = b.orderIndex ?? 1 << 30;
      if (ao != bo) return ao.compareTo(bo);
      return a.workoutId.compareTo(b.workoutId);
    });
    int order = 0;
    return items.map((item) {
      final label = item.date != null
          ? DateFormat('MMM d').format(item.date!.toLocal())
          : (item.orderIndex != null ? 'Day ${item.orderIndex}' : '#${order + 1}');
      return _APPlanAnalyticsPoint(order: order++, label: label, values: item.metrics);
    }).toList(growable: false);
  }

  Widget _buildActiveAnalyticsSection(List<_APPlanAnalyticsPoint> analytics, {Map<String, double>? totals}) {
    return Card(
      elevation: 1,
      color: Colors.white,
      margin: const EdgeInsets.symmetric(horizontal: 12),
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
      child: Padding(
        padding: const EdgeInsets.fromLTRB(12, 10, 12, 10),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Expanded(
                  child: DropdownButtonFormField<String>(
                    value: _metricX,
                    decoration: const InputDecoration(labelText: 'Ось X'),
                    items: _metrics
                        .map((m) => DropdownMenuItem<String>(value: m, child: Text(_metricLabel(m))))
                        .toList(),
                    onChanged: (v) => setState(() => _metricX = v ?? _metricX),
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: DropdownButtonFormField<String>(
                    value: _metricY,
                    decoration: const InputDecoration(labelText: 'Ось Y'),
                    items: _metrics
                        .map((m) => DropdownMenuItem<String>(value: m, child: Text(_metricLabel(m))))
                        .toList(),
                    onChanged: (v) => setState(() => _metricY = v ?? _metricY),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 10),
            if (totals != null && totals.isNotEmpty)
              Padding(
                padding: const EdgeInsets.only(bottom: 12),
                child: Wrap(
                  spacing: 8,
                  runSpacing: 8,
                  children: totals.entries.map((entry) {
                    final label = _metricLabel(entry.key);
                    final value = entry.value;
                    return Chip(
                      label: Text('$label: ${value.toStringAsFixed(2)}'),
                    );
                  }).toList(),
                ),
              ),
            SizedBox(
              height: 240,
              child: _buildActiveAnalyticsChart(analytics),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildActiveAnalyticsChart(List<_APPlanAnalyticsPoint> analytics) {
    if (analytics.isEmpty) {
      return const Center(child: Text('Нет данных для плана'));
    }
    final mx = _metricX;
    final my = _metricY;
    if (mx == my) {
      final points = <FlSpot>[];
      final labels = <String>[];
      for (var i = 0; i < analytics.length; i++) {
        final p = analytics[i];
        final val = p.values[mx] ?? 0;
        points.add(FlSpot(i.toDouble(), val));
        labels.add(p.label);
      }
      if (points.isEmpty) return const Center(child: Text('Нет данных для выбранных метрик'));
      final yValues = points.map((p) => p.y).toList();
      final minY = yValues.reduce(math.min);
      final maxY = yValues.reduce(math.max);
      final span = maxY - minY;
      double computeNiceInterval(double target) {
        if (target <= 0) return 1.0;
        final exponent = (math.log(target) / math.ln10).floor();
        final magnitude = math.pow(10, exponent).toDouble();
        final normalized = target / magnitude;
        double niceNormalized;
        if (normalized <= 1) {
          niceNormalized = 1;
        } else if (normalized <= 2) {
          niceNormalized = 2;
        } else if (normalized <= 5) {
          niceNormalized = 5;
        } else {
          niceNormalized = 10;
        }
        return niceNormalized * magnitude;
      }
      double yInterval;
      if (span == 0) {
        yInterval = 1.0;
      } else {
        final rawInterval = span / 5;
        yInterval = rawInterval < 1 ? 1.0 : computeNiceInterval(rawInterval);
      }
      double chartMinY;
      double chartMaxY;
      if (span == 0) {
        chartMinY = minY - yInterval;
        chartMaxY = maxY + yInterval;
      } else {
        chartMinY = (minY / yInterval).floor() * yInterval - yInterval;
        chartMaxY = (maxY / yInterval).ceil() * yInterval + yInterval;
      }
      if (chartMinY == chartMaxY) {
        chartMaxY = chartMinY + yInterval;
      }
      const showEvery = 2;
      return LineChart(
        LineChartData(
          minY: chartMinY,
          maxY: chartMaxY,
          titlesData: FlTitlesData(
            bottomTitles: AxisTitles(
              sideTitles: SideTitles(
                showTitles: true,
                interval: 1,
                getTitlesWidget: (value, meta) {
                  final idx = value.toInt();
                  if (idx < 0 || idx >= labels.length) return const SizedBox.shrink();
                  if (idx % showEvery != 0) return const SizedBox.shrink();
                  return SideTitleWidget(meta: meta, child: Text(labels[idx], style: const TextStyle(fontSize: 10)));
                },
              ),
            ),
            leftTitles: AxisTitles(
              sideTitles: SideTitles(
                showTitles: true,
                interval: yInterval,
                reservedSize: 44,
                getTitlesWidget: (value, meta) {
                  return SideTitleWidget(meta: meta, child: Text(value.toStringAsFixed(0), style: const TextStyle(fontSize: 10)));
                },
              ),
            ),
            topTitles: const AxisTitles(sideTitles: SideTitles(showTitles: false)),
            rightTitles: const AxisTitles(sideTitles: SideTitles(showTitles: false)),
          ),
          lineTouchData: LineTouchData(
            touchTooltipData: LineTouchTooltipData(
              getTooltipColor: (touchedSpot) => Colors.black.withOpacity(0.75),
              getTooltipItems: (touchedSpots) => touchedSpots
                  .map((spot) => LineTooltipItem(spot.y.toStringAsFixed(2), const TextStyle(color: Colors.white, fontWeight: FontWeight.w600)))
                  .toList(),
            ),
          ),
          lineBarsData: [
            LineChartBarData(
              spots: points,
              isCurved: true,
              color: Colors.blue,
              dotData: const FlDotData(show: false),
            ),
          ],
        ),
      );
    }
    final scatters = <ScatterSpot>[];
    for (final p in analytics) {
      final vx = p.values[mx];
      final vy = p.values[my];
      if (vx != null && vy != null) scatters.add(ScatterSpot(vx, vy));
    }
    if (scatters.isEmpty) return const Center(child: Text('Нет данных для выбранных метрик'));
    return ScatterChart(
      ScatterChartData(
        scatterSpots: scatters,
        titlesData: const FlTitlesData(
          topTitles: AxisTitles(sideTitles: SideTitles(showTitles: false)),
          rightTitles: AxisTitles(sideTitles: SideTitles(showTitles: false)),
        ),
      ),
    );
  }
}

class _StatusView {
  final String label;
  final Color background;
  final Color textColor;
  final Color dotColor;
  const _StatusView(this.label, this.background, this.textColor, this.dotColor);
}

extension on DateTime {
  DateTime get monday {
    final d = weekday;
    return DateTime(year, month, day).subtract(Duration(days: d == DateTime.monday ? 0 : d - 1));
  }
}

extension on num {
  double roundTo2p5() => (this / 2.5).round() * 2.5;
}

extension on double {
  double clampDouble(double min, double max) => this < min ? min : (this > max ? max : this);
}

extension on int {
  int clampInt(int min, int max) => this < min ? min : (this > max ? max : this);
}

extension _DateOnly on DateTime {
  bool isSameOrAfter(DateTime other) {
    final a = DateTime(year, month, day);
    final b = DateTime(other.year, other.month, other.day);
    return !a.isBefore(b);
  }
}

extension _WorkoutGuards on Workout {
  bool get isCompleted => (status?.toLowerCase() == 'completed') || (completedAt != null);
  bool get isLiveInProgress => (startedAt != null) && (completedAt == null);
}
