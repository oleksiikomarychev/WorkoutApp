class ParamsSets {
  final int? intensity;
  final int? effort;
  final int? volume;

  const ParamsSets({this.intensity, this.effort, this.volume});

  // Coerce incoming dynamic JSON to int?
  static int? _toInt(dynamic v) {
    if (v == null) return null;
    if (v is num) return v.toInt();
    if (v is String) return int.tryParse(v);
    if (v is bool) return v ? 1 : 0;
    return null;
  }

  factory ParamsSets.fromJson(Map<String, dynamic> json) => ParamsSets(
        intensity: _toInt(json['intensity']),
        effort: _toInt(json['effort']),
        volume: _toInt(json['volume']),
      );

  Map<String, dynamic> toJson() => {
        'intensity': intensity,
        'effort': effort,
        'volume': volume,
      };
}

class ExerciseScheduleItemDto {
  final int exerciseId;
  final List<ParamsSets> sets;

  const ExerciseScheduleItemDto({required this.exerciseId, required this.sets});

  factory ExerciseScheduleItemDto.fromJson(Map<String, dynamic> json) => ExerciseScheduleItemDto(
        exerciseId: json['exercise_id'] as int,
        sets: (json['sets'] as List<dynamic>? ?? [])
            .map((e) => ParamsSets.fromJson(e as Map<String, dynamic>))
            .toList(),
      );

  Map<String, dynamic> toJson() => {
        'exercise_id': exerciseId,
        'sets': sets.map((e) => e.toJson()).toList(),
      };
}
