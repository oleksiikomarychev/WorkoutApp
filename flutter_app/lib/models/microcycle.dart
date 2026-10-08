import 'plan_schedule.dart';

class Microcycle {
  final int id;
  final int mesocycleId;
  final String name;
  final String? notes;
  final int orderIndex;

  final Map<String, List<ExerciseScheduleItemDto>> schedule;

  final List<PlanWorkout> planWorkouts;
  final int? daysCount;
  final double? normalizationValue;
  final String? normalizationUnit;
  final List<NormalizationRule> normalizationRules;

  const Microcycle({
    required this.id,
    required this.mesocycleId,
    required this.name,
    this.notes,
    required this.orderIndex,
    required this.schedule,
    this.planWorkouts = const [],
    this.daysCount,
    this.normalizationValue,
    this.normalizationUnit,
    this.normalizationRules = const [],
  });

  factory Microcycle.fromJson(Map<String, dynamic> json) {
    final raw = Map<String, dynamic>.from(json['schedule'] ?? {});
    final sched = <String, List<ExerciseScheduleItemDto>>{};
    raw.forEach((key, value) {
      final List<ExerciseScheduleItemDto> list = (value as List<dynamic>? ?? [])
          .map<ExerciseScheduleItemDto>((e) => e != null
              ? ExerciseScheduleItemDto.fromJson(e as Map<String, dynamic>)
              : ExerciseScheduleItemDto(id: 0, exerciseId: 0, sets: [], name: '', exercises: []))
          .toList();
      sched[key] = list;
    });

    return Microcycle(
      id: (json['id'] as int?) ?? 0,
      mesocycleId: (json['mesocycle_id'] as int?) ?? 0,
      name: json['name'] ?? '',
      notes: json['notes'],
      orderIndex: (json['order_index'] as int?) ?? 0,
      schedule: sched,
      planWorkouts: (json['plan_workouts'] as List<dynamic>? ?? [])
          .map((e) => PlanWorkout.fromJson(e as Map<String, dynamic>))
          .toList(),
      daysCount: json['days_count'] as int?,
      normalizationValue: (json['normalization_value'] as num?)?.toDouble(),
      normalizationUnit: json['normalization_unit'] as String?,
      normalizationRules: (json['normalization_rules'] as List<dynamic>? ?? [])
          .map((e) => NormalizationRule.fromJson(e as Map<String, dynamic>))
          .toList(),
    );
  }

  Map<String, dynamic> toJson() => {
        'id': id,
        'mesocycle_id': mesocycleId,
        'name': name,
        'notes': notes,
        'order_index': orderIndex,
        'schedule': schedule.map((k, v) => MapEntry(k, v.map((e) => e.toJson()).toList())),
        'plan_workouts': planWorkouts.map((e) => e.toJson()).toList(),
        if (daysCount != null) 'days_count': daysCount,
        if (normalizationValue != null) 'normalization_value': normalizationValue,
        if (normalizationUnit != null) 'normalization_unit': normalizationUnit,
        if (normalizationRules.isNotEmpty)
          'normalization_rules': normalizationRules.map((e) => e.toJson()).toList(),
      };
}

class NormalizationRule {
  final List<int> exerciseIds;
  final List<String> muscleGroups;
  final List<String> targetMuscles;
  final double value;
  final String unit;

  const NormalizationRule({
    this.exerciseIds = const [],
    this.muscleGroups = const [],
    this.targetMuscles = const [],
    required this.value,
    required this.unit,
  });

  factory NormalizationRule.fromJson(Map<String, dynamic> json) => NormalizationRule(
        exerciseIds: (json['exercise_ids'] as List<dynamic>? ?? []).map((e) => (e as num).toInt()).toList(),
        muscleGroups:
            (json['muscle_groups'] as List<dynamic>? ?? []).map((e) => (e as String?)?.trim() ?? '').where((v) => v.isNotEmpty).toList(),
        targetMuscles:
            (json['target_muscles'] as List<dynamic>? ?? []).map((e) => (e as String?)?.trim() ?? '').where((v) => v.isNotEmpty).toList(),
        value: (json['value'] as num).toDouble(),
        unit: json['unit'] as String? ?? '',
      );

  Map<String, dynamic> toJson() => {
        'exercise_ids': exerciseIds,
        'muscle_groups': muscleGroups,
        'target_muscles': targetMuscles,
        'value': value,
        'unit': unit,
      };
}

class PlanWorkout {
  final int id;
  final int microcycleId;
  final String dayLabel;
  final int orderIndex;
  final List<PlanExercise> exercises;
  final Map<String, dynamic>? nutritionPlan;

  const PlanWorkout({
    required this.id,
    required this.microcycleId,
    required this.dayLabel,
    required this.orderIndex,
    this.exercises = const [],
    this.nutritionPlan,
  });

  factory PlanWorkout.fromJson(Map<String, dynamic> json) => PlanWorkout(
        id: (json['id'] as int?) ?? 0,
        microcycleId: (json['microcycle_id'] as int?) ?? 0,
        dayLabel: json['day_label'] as String? ?? '',
        orderIndex: (json['order_index'] as int?) ?? 0,
        exercises: (json['exercises'] as List<dynamic>? ?? [])
            .map((e) => PlanExercise.fromJson(e as Map<String, dynamic>))
            .toList(),
        nutritionPlan: json['nutrition_plan'] as Map<String, dynamic>?,
      );

  Map<String, dynamic> toJson() => {
        'id': id,
        'microcycle_id': microcycleId,
        'day_label': dayLabel,
        'order_index': orderIndex,
        'exercises': exercises.map((e) => e.toJson()).toList(),
        'nutrition_plan': nutritionPlan,
      };
}

class PlanExercise {
  final int id;
  final int exerciseDefinitionId;
  final String exerciseName;
  final int orderIndex;
  final int? planWorkoutId;
  final int? restSeconds;
  final String? notes;
  final List<PlanSet> sets;

  const PlanExercise({
    required this.id,
    required this.exerciseDefinitionId,
    required this.exerciseName,
    required this.orderIndex,
    this.planWorkoutId,
    this.restSeconds,
    this.notes,
    this.sets = const [],
  });

  factory PlanExercise.fromJson(Map<String, dynamic> json) => PlanExercise(
        id: (json['id'] as int?) ?? 0,
        exerciseDefinitionId: (json['exercise_definition_id'] as int?) ?? 0,
        exerciseName: json['exercise_name'] as String? ?? '',
        orderIndex: (json['order_index'] as int?) ?? 0,
        planWorkoutId: json['plan_workout_id'] as int?,
        restSeconds: json['rest_seconds'] as int?,
        notes: json['notes'] as String?,
        sets: (json['sets'] as List<dynamic>? ?? [])
            .map((e) => PlanSet.fromJson(e as Map<String, dynamic>))
            .toList(),
      );

  Map<String, dynamic> toJson() => {
        'id': id,
        'exercise_definition_id': exerciseDefinitionId,
        'exercise_name': exerciseName,
        'order_index': orderIndex,
        'plan_workout_id': planWorkoutId,
        'rest_seconds': restSeconds,
        'notes': notes,
        'sets': sets.map((e) => e.toJson()).toList(),
      };
}

class PlanSet {
  final int id;
  final int? orderIndex;
  final int? intensity;
  final int? effort;
  final int? volume;
  final int? planExerciseId;

  const PlanSet({
    required this.id,
    this.orderIndex,
    this.intensity,
    this.effort,
    this.volume,
    this.planExerciseId,
  });

  factory PlanSet.fromJson(Map<String, dynamic> json) => PlanSet(
        id: (json['id'] as int?) ?? 0,
        orderIndex: json['order_index'] as int?,
        intensity: json['intensity'] as int?,
        effort: json['effort'] as int?,
        volume: json['volume'] as int?,
        planExerciseId: json['plan_exercise_id'] as int?,
      );

  Map<String, dynamic> toJson() => {
        'id': id,
        'order_index': orderIndex,
        'intensity': intensity,
        'effort': effort,
        'volume': volume,
        'plan_exercise_id': planExerciseId,
      };
}

class MicrocycleUpdateDto {
  final String? name;
  final String? notes;
  final int? orderIndex;
  final Map<String, List<ExerciseScheduleItemDto>>? schedule;
  final int? daysCount;
  final double? normalizationValue;
  final String? normalizationUnit;

  const MicrocycleUpdateDto({
    this.name,
    this.notes,
    this.orderIndex,
    this.schedule,
    this.daysCount,
    this.normalizationValue,
    this.normalizationUnit,
  });

  Map<String, dynamic> toJson() => {
        if (name != null) 'name': name,
        if (notes != null) 'notes': notes,
        if (orderIndex != null) 'order_index': orderIndex,
        if (schedule != null) 'schedule': schedule?.map((k, v) => MapEntry(k, v.map((e) => e.toJson()).toList())),
        if (daysCount != null) 'days_count': daysCount,
        if (normalizationValue != null) 'normalization_value': normalizationValue,
        if (normalizationUnit != null) 'normalization_unit': normalizationUnit,
      };
}
