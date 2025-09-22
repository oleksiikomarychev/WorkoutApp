import 'exercise_dto.dart';

class ParamsSets {
  double? intensity;
  double? effort;
  double? volume;

  ParamsSets({
    this.intensity,
    this.effort,
    this.volume,
  });

  factory ParamsSets.fromJson(Map<String, dynamic> json) => ParamsSets(
    intensity: json['intensity'] != null ? (json['intensity'] as num).toDouble() : null,
    effort: json['effort'] != null ? (json['effort'] as num).toDouble() : null,
    volume: json['volume'] != null ? (json['volume'] as num).toDouble() : null,
  );

  Map<String, dynamic> toJson() => {
    'intensity': intensity,
    'effort': effort,
    'volume': volume,
  };
}

class ExerciseScheduleItemDto {
  final int id;
  final int exerciseId;
  final List<ParamsSets> sets;
  final String name;
  final List<ExerciseDto> exercises;

  ExerciseScheduleItemDto({
    required this.id,
    required this.exerciseId,
    required this.sets,
    required this.name,
    required this.exercises,
  });

  factory ExerciseScheduleItemDto.fromJson(Map<String, dynamic> json) {
    return ExerciseScheduleItemDto(
      id: json['id'] as int? ?? 0,
      exerciseId: json['exercise_id'] as int? ?? 0,
      sets: (json['sets'] as List<dynamic>? ?? [])
          .map((e) => e != null ? ParamsSets.fromJson(e as Map<String, dynamic>) : ParamsSets())
          .toList(),
      name: json['name'] as String? ?? '',
      exercises: (json['exercises'] as List<dynamic>? ?? [])
          .map((e) => ExerciseDto.fromJson(e as Map<String, dynamic>))
          .toList(),
    );
  }

  Map<String, dynamic> toJson() => {
        'id': id,
        'exercise_id': exerciseId,
        'sets': sets.map((set) => set.toJson()).toList(),
        'name': name,
        'exercises': exercises.map((e) => e.toJson()).toList(),
      };
}

class MicrocycleCreate {
  final Map<String, List<ParamsSets>> schedule;

  MicrocycleCreate({required this.schedule});

  factory MicrocycleCreate.fromJson(Map<String, dynamic> json) => MicrocycleCreate(
    schedule: Map<String, List<ParamsSets>>.from(json['schedule']?.map((k, v) => MapEntry(k, (v as List).map((e) => ParamsSets.fromJson(e as Map<String, dynamic>)).toList().cast<ParamsSets>())) ?? {}),
  );

  Map<String, dynamic> toJson() => {
    'schedule': schedule.map((k, v) => MapEntry(k, v.map((e) => e.toJson()).toList())).cast<String, List>(),
  };
}
