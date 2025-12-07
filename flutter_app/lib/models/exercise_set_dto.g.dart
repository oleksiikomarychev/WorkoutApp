

part of 'exercise_set_dto.dart';





_$ExerciseSetDtoImpl _$$ExerciseSetDtoImplFromJson(Map<String, dynamic> json) =>
    _$ExerciseSetDtoImpl(
      id: (json['id'] as num?)?.toInt(),
      reps: (json['reps'] as num?)?.toInt() ?? 0,
      weight: (json['weight'] as num?)?.toDouble() ?? 0.0,
      rpe: (json['rpe'] as num?)?.toDouble(),
      order: (json['order'] as num?)?.toInt(),
      exerciseInstanceId: (json['exercise_instance'] as num?)?.toInt(),
      volume: _volumeFromJson(json['volume']),
    );

Map<String, dynamic> _$$ExerciseSetDtoImplToJson(
        _$ExerciseSetDtoImpl instance) =>
    <String, dynamic>{
      'id': instance.id,
      'reps': instance.reps,
      'weight': instance.weight,
      'rpe': instance.rpe,
      'order': instance.order,
      'exercise_instance': instance.exerciseInstanceId,
    };
