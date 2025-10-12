import 'dart:math' as math;

import 'package:flutter/material.dart';
import 'package:fl_chart/fl_chart.dart';
import 'package:workout_app/models/calendar_plan.dart';
import 'package:workout_app/models/exercise_definition.dart';
import 'package:workout_app/models/mesocycle.dart';
import 'package:workout_app/models/microcycle.dart';
import 'package:workout_app/models/muscle_info.dart';
import 'package:workout_app/models/user_max.dart';
import 'package:workout_app/services/api_client.dart';
import 'package:workout_app/services/exercise_service.dart';
import 'package:workout_app/src/api/plan_api.dart';
import 'package:workout_app/src/widgets/apply_plan_widget.dart' show ApplyPlanWidget;

class CalendarPlanDetail extends StatefulWidget {
  final CalendarPlan plan;

  const CalendarPlanDetail({super.key, required this.plan});

  @override
  _CalendarPlanDetailState createState() => _CalendarPlanDetailState();
}

enum _TimeBucket { session, microcycle, calendarWeek }

class _PlanAnalyticsPoint {
  final int order;
  final String label;
  final Map<String, double> values;

  const _PlanAnalyticsPoint({
    required this.order,
    required this.label,
    required this.values,
  });
}

class _MultiSelectOption<T> {
  final T value;
  final String label;

  const _MultiSelectOption({
    required this.value,
    required this.label,
  });
}

class _MultiSelectSheet<T> extends StatefulWidget {
  final String title;
  final List<_MultiSelectOption<T>> options;
  final Set<T> initialSelection;

  const _MultiSelectSheet({
    required this.title,
    required this.options,
    required this.initialSelection,
  });

  @override
  State<_MultiSelectSheet<T>> createState() => _MultiSelectSheetState<T>();
}

class _MultiSelectSheetState<T> extends State<_MultiSelectSheet<T>> {
  late final Set<T> _selection;

  @override
  void initState() {
    super.initState();
    _selection = Set<T>.from(widget.initialSelection);
  }

  void _toggle(T value, bool selected) {
    setState(() {
      if (selected) {
        _selection.add(value);
      } else {
        _selection.remove(value);
      }
    });
  }

  @override
  Widget build(BuildContext context) {
    return SafeArea(
      child: Padding(
        padding: const EdgeInsets.only(top: 16, left: 16, right: 16, bottom: 24),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Expanded(
                  child: Text(
                    widget.title,
                    style: Theme.of(context).textTheme.titleMedium,
                  ),
                ),
                IconButton(
                  icon: const Icon(Icons.close),
                  onPressed: () => Navigator.of(context).pop(widget.initialSelection),
                ),
              ],
            ),
            const SizedBox(height: 12),
            Flexible(
              child: SingleChildScrollView(
                child: Column(
                  children: widget.options
                      .map(
                        (option) => CheckboxListTile(
                          value: _selection.contains(option.value),
                          onChanged: (checked) => _toggle(option.value, checked ?? false),
                          title: Text(option.label),
                          controlAffinity: ListTileControlAffinity.leading,
                          contentPadding: EdgeInsets.zero,
                        ),
                      )
                      .toList(),
                ),
              ),
            ),
            const SizedBox(height: 12),
            Row(
              mainAxisAlignment: MainAxisAlignment.end,
              children: [
                TextButton(
                  onPressed: () => Navigator.of(context).pop(widget.initialSelection),
                  child: const Text('Отмена'),
                ),
                const SizedBox(width: 12),
                ElevatedButton(
                  onPressed: () => Navigator.of(context).pop(Set<T>.from(_selection)),
                  child: const Text('Готово'),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}

class _SingleSelectSheet<T> extends StatefulWidget {
  final String title;
  final List<_MultiSelectOption<T>> options;
  final T initialValue;

  const _SingleSelectSheet({
    required this.title,
    required this.options,
    required this.initialValue,
  });

  @override
  State<_SingleSelectSheet<T>> createState() => _SingleSelectSheetState<T>();
}

class _SingleSelectSheetState<T> extends State<_SingleSelectSheet<T>> {
  late T _value;

  @override
  void initState() {
    super.initState();
    _value = widget.initialValue;
  }

  void _select(T value) {
    setState(() {
      _value = value;
    });
  }

  @override
  Widget build(BuildContext context) {
    return SafeArea(
      child: Padding(
        padding: const EdgeInsets.only(top: 16, left: 16, right: 16, bottom: 24),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Expanded(
                  child: Text(
                    widget.title,
                    style: Theme.of(context).textTheme.titleMedium,
                  ),
                ),
                IconButton(
                  icon: const Icon(Icons.close),
                  onPressed: () => Navigator.of(context).pop(),
                ),
              ],
            ),
            const SizedBox(height: 12),
            Flexible(
              child: SingleChildScrollView(
                child: Column(
                  children: widget.options
                      .map(
                        (option) => RadioListTile<T>(
                          value: option.value,
                          groupValue: _value,
                          onChanged: (selected) {
                            if (selected != null) {
                              _select(selected);
                            }
                          },
                          title: Text(option.label),
                          contentPadding: EdgeInsets.zero,
                        ),
                      )
                      .toList(),
                ),
              ),
            ),
            const SizedBox(height: 12),
            Row(
              mainAxisAlignment: MainAxisAlignment.end,
              children: [
                TextButton(
                  onPressed: () => Navigator.of(context).pop(),
                  child: const Text('Отмена'),
                ),
                const SizedBox(width: 12),
                ElevatedButton(
                  onPressed: () => Navigator.of(context).pop(_value),
                  child: const Text('Готово'),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}

class _CalendarPlanDetailState extends State<CalendarPlanDetail> {
  List<UserMax> _userMaxList = [];
  late final Set<int> _planExerciseDefinitionIds;
  late final Set<String> _planExerciseNames;

  // Analytics state (plan-derived)
  final List<String> _metrics = const ['sets', 'volume', 'intensity', 'effort'];
  String _metricX = 'effort';
  String _metricY = 'effort';
  late List<_PlanAnalyticsPoint> _planAnalytics;
  _TimeBucket _timeBucket = _TimeBucket.microcycle;
  bool _analyticsExpanded = true;

  // Filters/meta
  late final ApiClient _apiClient;
  late final ExerciseService _exerciseService;
  List<ExerciseDefinition> _exerciseDefs = [];
  Map<int, ExerciseDefinition> _exDefById = {};
  List<MuscleInfo> _muscles = [];
  final Set<int> _selectedExerciseIds = {};
  final Set<String> _selectedMuscles = {};
  bool _loadingMeta = true;
  String? _metaError;

  Future<void> _fetchUserMaxes() async {
    try {
      final userMaxes = await PlanApi.getUserMaxes();
      setState(() => _userMaxList = userMaxes);
    } catch (e) {
      print('Failed to fetch user maxes: $e');
    }
  }

  @override
  void initState() {
    super.initState();
    _apiClient = ApiClient();
    _exerciseService = ExerciseService(_apiClient);
    final exerciseData = _collectPlanExerciseData(widget.plan);
    _planExerciseDefinitionIds = exerciseData.$1;
    _planExerciseNames = exerciseData.$2;
    _fetchUserMaxes();
    _planAnalytics = _computePlanAnalytics(widget.plan);
    _loadExerciseMeta();
  }

  Future<void> _applyPlan(BuildContext context) async {
    try {
      showModalBottomSheet(
        context: context,
        isScrollControlled: true,
        builder: (context) => ApplyPlanWidget(
          userMaxList: _userMaxList,
          allowedExerciseIds: _planExerciseDefinitionIds,
          allowedExerciseNames: _planExerciseNames,
          planId: widget.plan.id,
          onApply: (settings) async {
            try {
              await PlanApi.applyPlan(
                planId: widget.plan.id,
                userMaxIds: settings['user_max_ids'],
                computeWeights: settings['compute_weights'],
                roundingStep: settings['rounding_step'],
                roundingMode: settings['rounding_mode'],
              );
              Navigator.of(context).pop();
              ScaffoldMessenger.of(context).showSnackBar(
                const SnackBar(content: Text('Plan applied successfully')),
              );
            } catch (e) {
              ScaffoldMessenger.of(context).showSnackBar(
                SnackBar(content: Text('Failed to apply plan: $e')),
              );
            }
          },
        ),
      );
    } catch (e) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Error: $e')),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text(widget.plan.name),
        backgroundColor: Theme.of(context).primaryColor,
        actions: [
          IconButton(
            icon: const Icon(Icons.check),
            onPressed: () => _applyPlan(context),
            tooltip: 'Apply Plan',
          ),
        ],
      ),
      body: Padding(
        padding: const EdgeInsets.all(12.0),
        child: SingleChildScrollView(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              _buildPlanInfo(context),
              const SizedBox(height: 12),
              _buildAnalyticsSection(context),
              const SizedBox(height: 12),
              const Text('Mesocycles', style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold)),
              const SizedBox(height: 8),
              ...widget.plan.mesocycles.map((mesocycle) => _buildMesocycleExpansionTile(mesocycle)),
            ],
          ),
        ),
      ),
    );
  }

  List<_PlanAnalyticsPoint> _computePlanAnalytics(
    CalendarPlan plan, {
    Set<int>? onlyExerciseIds,
    Set<String>? onlyMuscles,
  }) {
    final points = <_PlanAnalyticsPoint>[];
    var order = 0;

    List<PlanWorkout> _sortedWorkouts(Microcycle microcycle) {
      final workouts = [...microcycle.planWorkouts];
      workouts.sort((a, b) => a.orderIndex.compareTo(b.orderIndex));
      return workouts;
    }

    bool _passesFilters(int? exDefId) {
      final filtersActive = (onlyExerciseIds != null && onlyExerciseIds.isNotEmpty) ||
          (onlyMuscles != null && onlyMuscles.isNotEmpty);
      if (!filtersActive) {
        return true;
      }
      if (exDefId == null || exDefId == 0) return false;
      if (onlyExerciseIds != null && onlyExerciseIds.isNotEmpty && !onlyExerciseIds.contains(exDefId)) {
        return false;
      }
      if (onlyMuscles != null && onlyMuscles.isNotEmpty) {
        final def = _exDefById[exDefId];
        if (def == null) return false;
        final all = {...(def.targetMuscles ?? const []), ...(def.synergistMuscles ?? const [])};
        if (all.intersection(onlyMuscles).isEmpty) return false;
      }
      return true;
    }

    Map<String, double> _aggregateSetsFromExercises(List<PlanExercise> exercises) {
      double setsCount = 0;
      double volume = 0;
      double intensitySum = 0;
      int intensityCount = 0;
      double effortSum = 0;
      int effortCount = 0;

      for (final exercise in exercises) {
        if (!_passesFilters(exercise.exerciseDefinitionId)) continue;
        for (final set in exercise.sets) {
          setsCount += 1;
          if (set.volume != null) volume += set.volume!.toDouble();
          if (set.intensity != null) {
            intensitySum += set.intensity!.toDouble();
            intensityCount += 1;
          }
          if (set.effort != null) {
            effortSum += set.effort!.toDouble();
            effortCount += 1;
          }
        }
      }

      return {
        'sets': setsCount,
        'volume': volume,
        'intensity': intensityCount > 0 ? intensitySum / intensityCount : 0,
        'effort': effortCount > 0 ? effortSum / effortCount : 0,
      };
    }

    Map<String, double> _aggregateMicrocycle(Microcycle micro) {
      double setsCount = 0;
      double volume = 0;
      double intensitySum = 0;
      int intensityCount = 0;
      double effortSum = 0;
      int effortCount = 0;

      final workouts = _sortedWorkouts(micro);
      for (final workout in workouts) {
        for (final ex in workout.exercises) {
          if (!_passesFilters(ex.exerciseDefinitionId)) continue;
          for (final set in ex.sets) {
            setsCount += 1;
            if (set.volume != null) volume += set.volume!.toDouble();
            if (set.intensity != null) {
              intensitySum += set.intensity!.toDouble();
              intensityCount += 1;
            }
            if (set.effort != null) {
              effortSum += set.effort!.toDouble();
              effortCount += 1;
            }
          }
        }
      }

      return {
        'sets': setsCount,
        'volume': volume,
        'intensity': intensityCount > 0 ? intensitySum / intensityCount : 0,
        'effort': effortCount > 0 ? effortSum / effortCount : 0,
      };
    }

    final mesocycles = [...plan.mesocycles]..sort((a, b) => a.orderIndex.compareTo(b.orderIndex));
    final totalMicrocyclesCount = mesocycles.fold<int>(0, (sum, meso) => sum + meso.microcycles.length);

    if (_timeBucket == _TimeBucket.session) {
      for (final mesocycle in mesocycles) {
        final microcycles = [...mesocycle.microcycles]..sort((a, b) => a.orderIndex.compareTo(b.orderIndex));
        for (final micro in microcycles) {
          final workouts = _sortedWorkouts(micro);
          if (workouts.isNotEmpty) {
            for (final workout in workouts) {
              order += 1;
              final values = _aggregateSetsFromExercises(workout.exercises);
              final hasAny = values.values.any((v) => v != 0);
              if (hasAny) {
                points.add(_PlanAnalyticsPoint(order: order, label: 'S$order', values: values));
              }
            }
          }
        }
      }
      return points;
    }

    if (_timeBucket == _TimeBucket.microcycle) {
      var mOrder = 0;
      for (final mesocycle in mesocycles) {
        final microcycles = [...mesocycle.microcycles]..sort((a, b) => a.orderIndex.compareTo(b.orderIndex));
        for (final micro in microcycles) {
          final values = _aggregateMicrocycle(micro);
          final hasAny = values.values.any((v) => v != 0);
          if (hasAny) {
            mOrder += 1;
            points.add(_PlanAnalyticsPoint(order: mOrder, label: 'M$mOrder', values: values));
          }
        }
      }
      return points;
    }

    // Calendar week aggregation (real weeks from startDate + microcycle lengths)
    int? _tryParseDayNumber(String key) {
      final match = RegExp(r'\\d+').firstMatch(key);
      if (match == null) return null;
      return int.tryParse(match.group(0)!);
    }

    final startDate = plan.startDate; // may be null
    final sessions = <({Map<String, double> values, double dayOffset})>[];
    double cumulativeDays = 0.0;

    for (final mesocycle in mesocycles) {
      final microcycles = [...mesocycle.microcycles]..sort((a, b) => a.orderIndex.compareTo(b.orderIndex));
      for (final micro in microcycles) {
        final workouts = _sortedWorkouts(micro);

        // Estimate microcycle length in days
        double microLen = (micro.daysCount?.toDouble()) ?? 0.0;
        if (microLen <= 0 && plan.durationWeeks > 0 && totalMicrocyclesCount > 0) {
          microLen = (plan.durationWeeks * 7) / totalMicrocyclesCount;
        }
        if (microLen <= 0 && workouts.isNotEmpty) {
          microLen = workouts.length.toDouble();
        }
        if (microLen <= 0) {
          microLen = 7.0; // final fallback
        }

        final n = workouts.length;
        for (var i = 0; i < n; i++) {
          final workout = workouts[i];
          final values = _aggregateSetsFromExercises(workout.exercises);
          final hasAny = values.values.any((v) => v != 0);
          if (!hasAny) continue;
          final dayWithin = (i + 0.5) * (microLen / n);
          sessions.add((values: values, dayOffset: cumulativeDays + dayWithin));
        }

        cumulativeDays += microLen;
      }
    }

    int weeks;
    if (plan.durationWeeks > 0) {
      weeks = plan.durationWeeks;
    } else {
      weeks = (cumulativeDays / 7).ceil();
      if (weeks <= 0) weeks = sessions.length; // final fallback
    }
    if (weeks <= 0) return points;

    final bins = List.generate(weeks, (_) => {
          'sets': 0.0,
          'volume': 0.0,
          'intensityWeighted': 0.0,
          'effortWeighted': 0.0,
          'weight': 0.0,
        });

    for (final s in sessions) {
      final sets = s.values['sets'] ?? 0;
      final vol = s.values['volume'] ?? 0;
      final intVal = s.values['intensity'] ?? 0;
      final effVal = s.values['effort'] ?? 0;
      int wIdx = (s.dayOffset / 7).floor();
      if (wIdx < 0) wIdx = 0;
      if (wIdx >= weeks) wIdx = weeks - 1;
      bins[wIdx]['sets'] = (bins[wIdx]['sets'] as double) + sets;
      bins[wIdx]['volume'] = (bins[wIdx]['volume'] as double) + vol;
      bins[wIdx]['intensityWeighted'] = (bins[wIdx]['intensityWeighted'] as double) + intVal * sets;
      bins[wIdx]['effortWeighted'] = (bins[wIdx]['effortWeighted'] as double) + effVal * sets;
      bins[wIdx]['weight'] = (bins[wIdx]['weight'] as double) + sets;
    }

    for (var w = 0; w < weeks; w++) {
      final weight = bins[w]['weight'] as double;
      final intensity = weight > 0 ? (bins[w]['intensityWeighted'] as double) / weight : 0.0;
      final effort = weight > 0 ? (bins[w]['effortWeighted'] as double) / weight : 0.0;
      final values = <String, double>{
        'sets': bins[w]['sets'] as double,
        'volume': bins[w]['volume'] as double,
        'intensity': intensity,
        'effort': effort,
      };
      final hasAny = values.values.any((v) => v != 0);
      if (hasAny) {
        points.add(_PlanAnalyticsPoint(order: w + 1, label: 'W${w + 1}', values: values));
      }
    }

    return points;
  }

  Future<void> _loadExerciseMeta() async {
    try {
      setState(() => _loadingMeta = true);
      final defs = await _exerciseService.getExercisesByIds(_planExerciseDefinitionIds.toList());
      final muscles = await _exerciseService.getMuscles();
      final byId = <int, ExerciseDefinition>{
        for (final d in defs)
          if (d.id != null) d.id!: d,
      };
      setState(() {
        _exerciseDefs = defs;
        _exDefById = byId;
        _muscles = muscles;
        _loadingMeta = false;
      });
    } catch (e) {
      setState(() {
        _metaError = 'Не удалось загрузить данные упражнений';
        _loadingMeta = false;
      });
    }
  }

  void _applyFilters({VoidCallback? beforeRecalc}) {
    beforeRecalc?.call();
    final onlyIds = _selectedExerciseIds.isEmpty ? null : _selectedExerciseIds;
    final onlyMuscles = _selectedMuscles.isEmpty ? null : _selectedMuscles;
    setState(() {
      _planAnalytics = _computePlanAnalytics(
        widget.plan,
        onlyExerciseIds: onlyIds,
        onlyMuscles: onlyMuscles,
      );
    });
  }

  Widget _buildAnalyticsSection(BuildContext context) {
    final filtersReady = !_loadingMeta && _metaError == null;
    return Card(
      elevation: 1,
      color: Colors.transparent,
      shadowColor: Colors.deepPurple.withOpacity(0.12),
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
      child: Container(
        decoration: BoxDecoration(
          gradient: const LinearGradient(
            colors: [Color(0xFFFDF7FF), Color(0xFFEFF5FF)],
            begin: Alignment.topLeft,
            end: Alignment.bottomRight,
          ),
          borderRadius: BorderRadius.circular(16),
        ),
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
        child: LayoutBuilder(
          builder: (context, constraints) {
            const spacing = 10.0;
            final width = constraints.maxWidth;
            final twoColumnBreakpoint = 420.0;
            final useTwoColumns = width >= twoColumnBreakpoint;
            final fieldWidth = useTwoColumns
                ? ((width - spacing) / 2).clamp(0.0, 280.0)
                : width;

            Widget buildFilterSummary({required bool forExercises}) {
              return _buildFilterDropdown(
                label: forExercises ? 'Упражнения' : 'Мышцы',
                valueText: filtersReady
                    ? (forExercises ? _exerciseSummaryText() : _muscleSummaryText())
                    : _loadingMeta
                        ? 'Загрузка…'
                        : (_metaError ?? ''),
                enabled: filtersReady,
                onTap: forExercises ? _showExerciseFilter : _showMuscleFilter,
              );
            }

            final expandedContent = Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const SizedBox(height: 8),
                Wrap(
                  spacing: spacing,
                  runSpacing: spacing,
                  children: [
                    SizedBox(width: fieldWidth, child: _buildMetricPicker('Ось X', true)),
                    SizedBox(width: fieldWidth, child: _buildMetricPicker('Ось Y', false)),
                  ],
                ),
                const SizedBox(height: 6),
                Wrap(
                  spacing: spacing,
                  runSpacing: spacing,
                  children: [
                    SizedBox(width: fieldWidth, child: buildFilterSummary(forExercises: true)),
                    SizedBox(width: fieldWidth, child: buildFilterSummary(forExercises: false)),
                  ],
                ),
                const SizedBox(height: 4),
                AnimatedSwitcher(
                  duration: const Duration(milliseconds: 250),
                  child: _metaError != null
                      ? Padding(
                          padding: const EdgeInsets.only(bottom: 4),
                          child: Text(
                            _metaError!,
                            key: const ValueKey('metaError'),
                            style: const TextStyle(color: Colors.redAccent, fontSize: 12),
                          ),
                        )
                      : _loadingMeta
                          ? const Padding(
                              padding: EdgeInsets.only(bottom: 4),
                              child: LinearProgressIndicator(
                                key: ValueKey('metaLoading'),
                                minHeight: 4,
                              ),
                            )
                          : const SizedBox.shrink(key: ValueKey('metaIdle')),
                ),
                const SizedBox(height: 4),
                Builder(
                  builder: (context) {
                    final totalLabel = Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        const Icon(Icons.scatter_plot, size: 16, color: Color(0xFF6B5BFF)),
                        const SizedBox(width: 6),
                        Text(
                          'Всего точек (${_bucketShort()}): ${_planAnalytics.length}',
                          style: const TextStyle(
                            fontSize: 12,
                            fontWeight: FontWeight.w600,
                            color: Color(0xFF443A7A),
                          ),
                        ),
                      ],
                    );

                    if (useTwoColumns) {
                      return Row(
                        crossAxisAlignment: CrossAxisAlignment.center,
                        children: [
                          Expanded(child: totalLabel),
                          SizedBox(
                            width: fieldWidth,
                            child: _buildTimeBucketPicker(),
                          ),
                        ],
                      );
                    }

                    return Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        totalLabel,
                        const SizedBox(height: 6),
                        SizedBox(width: width, child: _buildTimeBucketPicker()),
                      ],
                    );
                  },
                ),
                const SizedBox(height: 8),
                SizedBox(
                  height: useTwoColumns ? 220 : 240,
                  child: ClipRRect(
                    borderRadius: BorderRadius.circular(12),
                    child: DecoratedBox(
                      decoration: BoxDecoration(
                        color: Colors.white,
                        borderRadius: BorderRadius.circular(12),
                        boxShadow: [
                          BoxShadow(
                            color: Colors.deepPurple.withOpacity(0.04),
                            blurRadius: 8,
                            offset: const Offset(0, 2),
                          ),
                        ],
                      ),
                      child: Padding(
                        padding: const EdgeInsets.all(12),
                        child: _buildAnalyticsChart(),
                      ),
                    ),
                  ),
                ),
              ],
            );

            return Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    Container(
                      width: 32,
                      height: 32,
                      decoration: BoxDecoration(
                        color: const Color(0xFF8066FF).withOpacity(0.18),
                        borderRadius: BorderRadius.circular(10),
                      ),
                      child: const Icon(Icons.analytics_outlined, color: Color(0xFF6745FF), size: 18),
                    ),
                    const SizedBox(width: 10),
                    const Expanded(
                      child: Text(
                        'Аналитика плана',
                        style: TextStyle(fontSize: 16, fontWeight: FontWeight.w700),
                      ),
                    ),
                    IconButton(
                      tooltip: _analyticsExpanded ? 'Свернуть' : 'Развернуть',
                      icon: AnimatedRotation(
                        duration: const Duration(milliseconds: 200),
                        turns: _analyticsExpanded ? 0 : 0.5,
                        child: const Icon(Icons.keyboard_arrow_up_rounded),
                      ),
                      onPressed: () {
                        setState(() => _analyticsExpanded = !_analyticsExpanded);
                      },
                    ),
                  ],
                ),
                AnimatedCrossFade(
                  firstChild: const SizedBox.shrink(),
                  secondChild: expandedContent,
                  crossFadeState: _analyticsExpanded ? CrossFadeState.showSecond : CrossFadeState.showFirst,
                  duration: const Duration(milliseconds: 200),
                  alignment: Alignment.topCenter,
                ),
              ],
            );
          },
        ),
      ),
    );
  }

  List<ExerciseDefinition> _availableExercises() {
    final defs = _exerciseDefs
        .where((d) => d.id != null && _planExerciseDefinitionIds.contains(d.id))
        .toList()
      ..sort((a, b) => a.name.compareTo(b.name));
    return defs;
  }

  List<MapEntry<String, String>> _availableMuscles() {
    final presentMuscles = <String, String>{};
    String labelFor(String key) {
      for (final muscle in _muscles) {
        if (muscle.key == key) return muscle.label;
      }
      return key;
    }

    for (final def in _exerciseDefs) {
      if (def.id == null || !_planExerciseDefinitionIds.contains(def.id)) continue;
      for (final key in (def.targetMuscles ?? const [])) {
        presentMuscles[key] = labelFor(key);
      }
      for (final key in (def.synergistMuscles ?? const [])) {
        presentMuscles[key] = labelFor(key);
      }
    }

    final entries = presentMuscles.entries.toList()
      ..sort((a, b) => a.value.compareTo(b.value));
    return entries;
  }

  String _exerciseSummaryText() {
    if (_selectedExerciseIds.isEmpty) return 'Все упражнения';
    final defs = _availableExercises();
    final selected = defs.where((d) => d.id != null && _selectedExerciseIds.contains(d.id)).toList();
    if (selected.isEmpty) return 'Фильтр не содержит данных';
    if (selected.length <= 2) {
      return selected.map((d) => d.name).join(', ');
    }
    final displayed = selected.take(2).map((d) => d.name).join(', ');
    return '$displayed и еще ${selected.length - 2}';
  }

  String _muscleSummaryText() {
    if (_selectedMuscles.isEmpty) return 'Все мышцы';
    final options = _availableMuscles();
    final selected = options.where((entry) => _selectedMuscles.contains(entry.key)).toList();
    if (selected.isEmpty) return 'Фильтр не содержит данных';
    if (selected.length <= 2) {
      return selected.map((entry) => entry.value).join(', ');
    }
    final displayed = selected.take(2).map((entry) => entry.value).join(', ');
    return '$displayed и еще ${selected.length - 2}';
  }

  Widget _buildFilterDropdown({
    required String label,
    required String valueText,
    required VoidCallback onTap,
    bool enabled = true,
  }) {
    final theme = Theme.of(context);
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(label, style: theme.textTheme.bodySmall?.copyWith(color: Colors.grey[700])),
        const SizedBox(height: 2),
        GestureDetector(
          onTap: enabled ? onTap : null,
          child: InputDecorator(
            decoration: InputDecoration(
              suffixIcon: const Icon(Icons.keyboard_arrow_down_rounded, size: 18),
              suffixIconConstraints: const BoxConstraints(minWidth: 28, minHeight: 28),
              isDense: true,
              contentPadding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
              border: OutlineInputBorder(borderRadius: BorderRadius.circular(10)),
            ),
            child: Text(
              valueText,
              style: theme.textTheme.bodyMedium?.copyWith(
                color: enabled ? theme.textTheme.bodyMedium?.color : Colors.grey,
              ),
            ),
          ),
        ),
      ],
    );
  }

  Future<void> _showExerciseFilter() async {
    final options = _availableExercises();
    final initial = Set<int>.from(_selectedExerciseIds);
    final result = await _showMultiSelectSheet<int>(
      title: 'Выберите упражнения',
      options: options
          .map((def) => _MultiSelectOption<int>(value: def.id!, label: def.name))
          .toList(),
      initialSelection: initial,
    );
    if (result == null) return;
    _applyFilters(beforeRecalc: () {
      _selectedExerciseIds
        ..clear()
        ..addAll(result);
    });
  }

  Future<void> _showMuscleFilter() async {
    final options = _availableMuscles();
    final initial = Set<String>.from(_selectedMuscles);
    final result = await _showMultiSelectSheet<String>(
      title: 'Выберите мышцы',
      options: options
          .map((entry) => _MultiSelectOption<String>(value: entry.key, label: entry.value))
          .toList(),
      initialSelection: initial,
    );
    if (result == null) return;
    _applyFilters(beforeRecalc: () {
      _selectedMuscles
        ..clear()
        ..addAll(result);
    });
  }

  Future<void> _showMetricPicker({required bool isX}) async {
    final current = isX ? _metricX : _metricY;
    final options = _metrics
        .map((metric) => _MultiSelectOption<String>(value: metric, label: _metricLabel(metric)))
        .toList();

    final result = await showModalBottomSheet<String>(
      context: context,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(16)),
      ),
      builder: (context) => _SingleSelectSheet<String>(
        title: isX ? 'Выберите метрику для оси X' : 'Выберите метрику для оси Y',
        options: options,
        initialValue: current,
      ),
    );

    if (result == null || result == current) return;
    setState(() {
      if (isX) {
        _metricX = result;
      } else {
        _metricY = result;
      }
    });
  }

  Future<Set<T>?> _showMultiSelectSheet<T>({
    required String title,
    required List<_MultiSelectOption<T>> options,
    required Set<T> initialSelection,
  }) async {
    if (options.isEmpty) return initialSelection;

    final result = await showModalBottomSheet<Set<T>>(
      context: context,
      isScrollControlled: true,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(16)),
      ),
      builder: (context) {
        return _MultiSelectSheet<T>(
          title: title,
          options: options,
          initialSelection: initialSelection,
        );
      },
    );

    return result ?? initialSelection;
  }

  void _clearFilters() {
    if (_selectedExerciseIds.isEmpty && _selectedMuscles.isEmpty) return;
    _applyFilters(beforeRecalc: () {
      _selectedExerciseIds.clear();
      _selectedMuscles.clear();
    });
  }

  Widget _buildMetricPicker(String label, bool isX) {
    return _buildFilterDropdown(
      label: label,
      valueText: _metricLabel(isX ? _metricX : _metricY),
      onTap: () => _showMetricPicker(isX: isX),
    );
  }

  String _metricLabel(String m) {
    switch (m) {
      case 'sets':
        return 'Сеты';
      case 'volume':
        return 'Повторения (volume)';
      case 'intensity':
        return 'Интенсивность (%)';
      case 'effort':
        return 'Усилие (RPE)';
      default:
        return m;
    }
  }

  String _timeBucketLabel(_TimeBucket b) {
    switch (b) {
      case _TimeBucket.session:
        return 'Сессии';
      case _TimeBucket.microcycle:
        return 'Микроциклы';
      case _TimeBucket.calendarWeek:
        return 'Недели';
    }
  }

  String _bucketShort() {
    switch (_timeBucket) {
      case _TimeBucket.session:
        return 'S';
      case _TimeBucket.microcycle:
        return 'M';
      case _TimeBucket.calendarWeek:
        return 'W';
    }
  }

  Widget _buildTimeBucketPicker() {
    return _buildFilterDropdown(
      label: 'Гранулярность',
      valueText: _timeBucketLabel(_timeBucket),
      onTap: _showTimeBucketPicker,
    );
  }

  Future<void> _showTimeBucketPicker() async {
    final options = <_MultiSelectOption<_TimeBucket>>[
      _MultiSelectOption(value: _TimeBucket.session, label: _timeBucketLabel(_TimeBucket.session)),
      _MultiSelectOption(value: _TimeBucket.microcycle, label: _timeBucketLabel(_TimeBucket.microcycle)),
      _MultiSelectOption(value: _TimeBucket.calendarWeek, label: _timeBucketLabel(_TimeBucket.calendarWeek)),
    ];

    final result = await showModalBottomSheet<_TimeBucket>(
      context: context,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(16)),
      ),
      builder: (context) => _SingleSelectSheet<_TimeBucket>(
        title: 'Выберите временную гранулярность',
        options: options,
        initialValue: _timeBucket,
      ),
    );

    if (result == null || result == _timeBucket) return;
    setState(() => _timeBucket = result);
    _applyFilters();
  }

  Future<void> _fetchAnalytics() async {
    // No-op: analytics are precomputed from plan structure.
  }

  Widget _buildAnalyticsChart() {
    if (_planAnalytics.isEmpty) {
      return const Center(child: Text('Нет данных для плана'));
    }
    final mx = _metricX;
    final my = _metricY;

    if (mx == my) {
      // Time series line chart
      final points = <FlSpot>[];
      final labels = <String>[];

      for (var i = 0; i < _planAnalytics.length; i++) {
        final point = _planAnalytics[i];
        final val = point.values[mx] ?? 0;
        points.add(FlSpot(i.toDouble(), val));
        labels.add(point.label);
      }
      if (points.isEmpty) {
        return const Center(child: Text('Нет данных для выбранных метрик'));
      }

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
                  if (idx < 0 || idx >= labels.length) {
                    return const SizedBox.shrink();
                  }
                  if (idx % showEvery != 0) {
                    return const SizedBox.shrink();
                  }
                  return SideTitleWidget(
                    meta: meta,
                    child: Text(labels[idx], style: const TextStyle(fontSize: 10)),
                  );
                },
              ),
            ),
            leftTitles: AxisTitles(
              sideTitles: SideTitles(
                showTitles: true,
                interval: yInterval,
                reservedSize: 44,
                getTitlesWidget: (value, meta) {
                  return SideTitleWidget(
                    meta: meta,
                    child: Text(
                      value.toStringAsFixed(0),
                      style: const TextStyle(fontSize: 10),
                    ),
                  );
                },
              ),
            ),
            topTitles: AxisTitles(sideTitles: SideTitles(showTitles: false)),
            rightTitles: AxisTitles(sideTitles: SideTitles(showTitles: false)),
          ),
          lineTouchData: LineTouchData(
            touchTooltipData: LineTouchTooltipData(
              getTooltipColor: (touchedSpot) => Colors.black.withOpacity(0.75),
              getTooltipItems: (touchedSpots) {
                return touchedSpots
                    .map(
                      (spot) => LineTooltipItem(
                        spot.y.toStringAsFixed(2),
                        const TextStyle(
                          color: Colors.white,
                          fontWeight: FontWeight.w600,
                        ),
                      ),
                    )
                    .toList();
              },
            ),
          ),
          lineBarsData: [
            LineChartBarData(
              spots: points,
              isCurved: true,
              color: Colors.blue,
              dotData: FlDotData(show: false),
            ),
          ],
        ),
      );
    }

    // Scatter: X vs Y correlation
    final scatters = <ScatterSpot>[];
    for (final point in _planAnalytics) {
      final vx = point.values[mx];
      final vy = point.values[my];
      if (vx != null && vy != null) {
        scatters.add(ScatterSpot(vx, vy));
      }
    }
    if (scatters.isEmpty) {
      return const Center(child: Text('Нет данных для выбранных метрик'));
    }
    return ScatterChart(
      ScatterChartData(
        scatterSpots: scatters,
        titlesData: FlTitlesData(
          bottomTitles: AxisTitles(
            sideTitles: SideTitles(
              showTitles: true,
              reservedSize: 28,
              getTitlesWidget: (value, meta) {
                return SideTitleWidget(
                  meta: meta,
                  child: Text(
                    value.toStringAsFixed(2),
                    style: const TextStyle(fontSize: 10),
                  ),
                );
              },
            ),
          ),
          leftTitles: AxisTitles(
            sideTitles: SideTitles(
              showTitles: true,
              reservedSize: 44,
              getTitlesWidget: (value, meta) {
                return SideTitleWidget(
                  meta: meta,
                  child: Text(
                    value.toStringAsFixed(2),
                    style: const TextStyle(fontSize: 10),
                  ),
                );
              },
            ),
          ),
          topTitles: AxisTitles(sideTitles: SideTitles(showTitles: false)),
          rightTitles: AxisTitles(sideTitles: SideTitles(showTitles: false)),
        ),
      ),
    );
  }

  Widget _buildPlanWorkoutsTable(List<PlanWorkout> planWorkouts) {
    if (planWorkouts.isEmpty) {
      return const Text('No plan workouts available');
    }

    return Column(
      children: planWorkouts.map((pw) => _buildWorkoutDayCard(pw)).toList(),
    );
  }

  (Set<int>, Set<String>) _collectPlanExerciseData(CalendarPlan plan) {
    final ids = <int>{};
    final names = <String>{};

    String? _normalizeName(String? name) {
      final value = name?.trim();
      if (value == null || value.isEmpty) return null;
      return value.toLowerCase();
    }

    void addExercise({int? id, String? name}) {
      if (id != null && id > 0) {
        ids.add(id);
      }
      final normalized = _normalizeName(name);
      if (normalized != null) {
        names.add(normalized);
      }
    }

    for (final mesocycle in plan.mesocycles) {
      for (final microcycle in mesocycle.microcycles) {
        for (final workout in microcycle.planWorkouts) {
          for (final exercise in workout.exercises) {
            addExercise(
              id: exercise.exerciseDefinitionId,
              name: exercise.exerciseName,
            );
          }
        }
      }
    }

    return (ids, names);
  }

  Widget _buildWorkoutDayCard(PlanWorkout workout) {
    return Card(
      elevation: 1,
      margin: const EdgeInsets.only(bottom: 8.0),
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(6)),
      child: Theme(
        data: Theme.of(context).copyWith(dividerColor: Colors.transparent),
        child: ExpansionTile(
          tilePadding: const EdgeInsets.symmetric(horizontal: 12.0, vertical: 4.0),
          childrenPadding: const EdgeInsets.only(left: 12.0, right: 12.0, bottom: 8.0),
          title: Row(
            children: [
              Icon(Icons.fitness_center, size: 16, color: Colors.grey[700]),
              const SizedBox(width: 8),
              Text(
                workout.dayLabel,
                style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 14),
              ),
              const SizedBox(width: 8),
              Text(
                '(${workout.exercises.length} ex)',
                style: TextStyle(color: Colors.grey[600], fontSize: 12),
              ),
            ],
          ),
          children: [
            Column(
              children: workout.exercises.asMap().entries.map((entry) {
                int idx = entry.key;
                var exercise = entry.value;
                return _buildExerciseCard(exercise, idx + 1);
              }).toList(),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildExerciseCard(PlanExercise exercise, int index) {
    return Container(
      margin: const EdgeInsets.only(bottom: 8.0),
      padding: const EdgeInsets.symmetric(horizontal: 12.0, vertical: 10.0),
      decoration: BoxDecoration(
        color: Colors.grey[50],
        borderRadius: BorderRadius.circular(6),
        border: Border.all(color: Colors.grey.shade300, width: 1),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Text(
                '$index.',
                style: const TextStyle(
                  fontWeight: FontWeight.bold,
                  fontSize: 14,
                ),
              ),
              const SizedBox(width: 8),
              Expanded(
                child: Text(
                  exercise.exerciseName,
                  style: const TextStyle(
                    fontWeight: FontWeight.w600,
                    fontSize: 14,
                  ),
                ),
              ),
            ],
          ),
          if (exercise.sets.isNotEmpty) ...[
            const SizedBox(height: 8),
            _buildSetsSection(exercise.sets),
          ],
        ],
      ),
    );
  }

  Widget _buildSetsSection(List<PlanSet> sets) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          '${sets.length} set${sets.length != 1 ? 's' : ''}',
          style: TextStyle(
            fontSize: 12,
            color: Colors.grey[600],
          ),
        ),
        const SizedBox(height: 6),
        ...sets.asMap().entries.map((entry) {
          int setIndex = entry.key;
          var set = entry.value;
          return _buildSetRow(set, setIndex + 1);
        }).toList(),
      ],
    );
  }

  Widget _buildSetRow(PlanSet set, int setNumber) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 4.0),
      child: Row(
        children: [
          SizedBox(
            width: 50,
            child: Text(
              'Set $setNumber',
              style: TextStyle(
                fontSize: 12,
                color: Colors.grey[700],
              ),
            ),
          ),
          Expanded(
            child: Row(
              children: [
                _buildCompactParameter('Int', set.intensity != null ? '${set.intensity}%' : '-'),
                const SizedBox(width: 12),
                _buildCompactParameter('Reps', set.volume != null ? '${set.volume}' : '-'),
                const SizedBox(width: 12),
                _buildCompactParameter('RPE', set.effort != null ? '${set.effort}' : '-'),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildCompactParameter(String label, String value) {
    return Expanded(
      child: Row(
        children: [
          Text(
            '$label:',
            style: TextStyle(
              fontSize: 12,
              color: Colors.grey[600],
            ),
          ),
          const SizedBox(width: 4),
          Text(
            value,
            style: const TextStyle(
              fontSize: 12,
              fontWeight: FontWeight.w600,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildInfoRow(String label, String value) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 4),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SizedBox(
            width: 90,
            child: Text(
              label,
              style: const TextStyle(fontWeight: FontWeight.w600, fontSize: 12),
            ),
          ),
          const SizedBox(width: 8),
          Expanded(
            child: Text(
              value,
              style: const TextStyle(fontSize: 12),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildCompactInfo(String label, String value) {
    return Text(
      '$label: $value',
      style: TextStyle(fontSize: 12, color: Colors.grey[700]),
    );
  }

  Widget _buildPlanInfo(BuildContext context) {
    return Card(
      elevation: 2,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
      child: Padding(
        padding: const EdgeInsets.all(12.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(Icons.calendar_today, size: 18, color: Theme.of(context).primaryColor),
                const SizedBox(width: 8),
                Expanded(
                  child: Text(widget.plan.name, style: const TextStyle(fontSize: 16, fontWeight: FontWeight.bold)),
                ),
              ],
            ),
            const SizedBox(height: 8),
            _buildInfoRow('Duration', '${widget.plan.durationWeeks} weeks'),
            _buildInfoRow('Active', widget.plan.isActive ? 'Yes' : 'No'),
            if (widget.plan.startDate != null)
              _buildInfoRow('Start Date', widget.plan.startDate!.toLocal().toString().split(' ')[0]),
            if (widget.plan.endDate != null)
              _buildInfoRow('End Date', widget.plan.endDate!.toLocal().toString().split(' ')[0]),
          ],
        ),
      ),
    );
  }

  Widget _buildMesocycleExpansionTile(Mesocycle mesocycle) {
    return Card(
      elevation: 1,
      margin: const EdgeInsets.only(bottom: 8.0),
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(6)),
      child: ExpansionTile(
        tilePadding: const EdgeInsets.symmetric(horizontal: 12.0, vertical: 4.0),
        childrenPadding: const EdgeInsets.only(left: 12.0, right: 12.0, bottom: 8.0),
        title: Row(
          children: [
            Text(
              'Meso ${mesocycle.orderIndex}',
              style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 14),
            ),
            const SizedBox(width: 8),
            Expanded(child: Text(mesocycle.name, style: const TextStyle(fontWeight: FontWeight.w600, fontSize: 14))),
            Text(
              '(${mesocycle.microcycles.length} micro)',
              style: TextStyle(color: Colors.grey[600], fontSize: 12),
            ),
          ],
        ),
        children: [
          Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              if (mesocycle.weeksCount != null ||
                  mesocycle.microcycleLengthDays != null ||
                  (mesocycle.normalizationValue != null && mesocycle.normalizationUnit != null))
                Padding(
                  padding: const EdgeInsets.only(bottom: 8.0),
                  child: Wrap(
                    spacing: 12,
                    children: [
                      if (mesocycle.weeksCount != null) _buildCompactInfo('Weeks', '${mesocycle.weeksCount}'),
                      if (mesocycle.microcycleLengthDays != null) _buildCompactInfo('Length', '${mesocycle.microcycleLengthDays}d'),
                      if (mesocycle.normalizationValue != null && mesocycle.normalizationUnit != null)
                        _buildCompactInfo('Norm', '${mesocycle.normalizationValue}${mesocycle.normalizationUnit}'),
                    ],
                  ),
                ),
              ...mesocycle.microcycles.map((microcycle) => _buildMicrocycleCard(microcycle)),
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildMicrocycleCard(Microcycle microcycle) {
    final name = microcycle.name.trim();
    final orderIndex = microcycle.orderIndex;
    final orderNumber = orderIndex >= 0 ? orderIndex + 1 : 1;
    final fallbackLabel = 'Micro $orderNumber';
    final primaryLabel = name.isNotEmpty ? name : fallbackLabel;
    final hasSecondaryLabel = name.isNotEmpty;

    final plannedDays = microcycle.planWorkouts.length;
    final dayCount = microcycle.daysCount ?? (plannedDays > 0 ? plannedDays : null);
    final subtitleText = dayCount != null ? '(${dayCount}d)' : null;

    return Card(
      elevation: 1,
      margin: const EdgeInsets.only(bottom: 6.0),
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(6)),
      color: Colors.grey[50],
      child: ExpansionTile(
        tilePadding: const EdgeInsets.symmetric(horizontal: 12.0, vertical: 2.0),
        childrenPadding: const EdgeInsets.only(left: 12.0, right: 12.0, bottom: 8.0),
        title: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              primaryLabel,
              style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 13),
            ),
            if (hasSecondaryLabel)
              Text(
                fallbackLabel,
                style: TextStyle(color: Colors.grey[600], fontSize: 11),
              ),
          ],
        ),
        subtitle: subtitleText != null
            ? Text(
                subtitleText,
                style: TextStyle(color: Colors.grey[600], fontSize: 11),
              )
            : null,
        children: [
          Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              _buildPlanWorkoutsTable(microcycle.planWorkouts),
            ],
          ),
        ],
      ),
    );
  }
}
