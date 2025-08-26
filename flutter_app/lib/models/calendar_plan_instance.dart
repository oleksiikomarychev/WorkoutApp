class ParamsSetInstance {
  final int id;
  final int? intensity;
  final int? effort;
  final int? volume;

  ParamsSetInstance({required this.id, this.intensity, this.effort, this.volume});

  factory ParamsSetInstance.fromJson(Map<String, dynamic> json) => ParamsSetInstance(
        id: json['id'] as int,
        intensity: json['intensity'],
        effort: json['effort'],
        volume: json['volume'],
      );

  Map<String, dynamic> toJson() => {
        'id': id,
        'intensity': intensity,
        'effort': effort,
        'volume': volume,
      };
}

class ExerciseScheduleItemInstance {
  final int id;
  final int exerciseId;
  final List<ParamsSetInstance> sets;

  ExerciseScheduleItemInstance({required this.id, required this.exerciseId, required this.sets});

  factory ExerciseScheduleItemInstance.fromJson(Map<String, dynamic> json) => ExerciseScheduleItemInstance(
        id: json['id'] as int,
        exerciseId: json['exercise_id'] as int,
        sets: (json['sets'] as List<dynamic>? ?? [])
            .map((e) => ParamsSetInstance.fromJson(e as Map<String, dynamic>))
            .toList(),
      );

  Map<String, dynamic> toJson() => {
        'id': id,
        'exercise_id': exerciseId,
        'sets': sets.map((e) => e.toJson()).toList(),
      };
}

class CalendarPlanInstance {
  final int id;
  final int? sourcePlanId;
  final String name;
  final Map<String, List<ExerciseScheduleItemInstance>> schedule;
  final int durationWeeks;

  CalendarPlanInstance({
    required this.id,
    required this.sourcePlanId,
    required this.name,
    required this.schedule,
    required this.durationWeeks,
  });

  factory CalendarPlanInstance.fromJson(Map<String, dynamic> json) {
    final raw = Map<String, dynamic>.from(json['schedule'] ?? {});
    final sched = <String, List<ExerciseScheduleItemInstance>>{};
    raw.forEach((key, value) {
      final list = (value as List<dynamic>? ?? [])
          .map((e) => ExerciseScheduleItemInstance.fromJson(e as Map<String, dynamic>))
          .toList();
      sched[key] = list;
    });
    return CalendarPlanInstance(
      id: json['id'] as int,
      sourcePlanId: json['source_plan_id'],
      name: json['name'] ?? '',
      schedule: sched,
      durationWeeks: json['duration_weeks'] ?? 0,
    );
  }

  Map<String, dynamic> toJson() => {
        'id': id,
        'source_plan_id': sourcePlanId,
        'name': name,
        'schedule': schedule.map((k, v) => MapEntry(k, v.map((e) => e.toJson()).toList())),
        'duration_weeks': durationWeeks,
      };
}
