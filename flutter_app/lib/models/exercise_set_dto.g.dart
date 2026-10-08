// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'exercise_set_dto.dart';

// **************************************************************************
// JsonSerializableGenerator
// **************************************************************************

_$ExerciseSetDtoImpl _$$ExerciseSetDtoImplFromJson(Map<String, dynamic> json) =>
    _$ExerciseSetDtoImpl(
      id: (json['id'] as num?)?.toInt(),
      setType: json['set_type'] as String?,
      subsets:
          (json['subsets'] as List<dynamic>?)
              ?.map((e) => ExerciseSetDto.fromJson(e as Map<String, dynamic>))
              .toList() ??
          const <ExerciseSetDto>[],
      reps: (json['volume'] as num?)?.toInt() ?? 0,
      weight: (json['working_weight'] as num?)?.toDouble() ?? 0.0,
      rpe: (json['rpe'] as num?)?.toDouble(),
      order: (json['order'] as num?)?.toInt(),
      exerciseInstanceId: (json['exercise_instance'] as num?)?.toInt(),
      intensity: (json['intensity'] as num?)?.toInt() ?? 0,
      effort: (json['effort'] as num?)?.toDouble() ?? 0,
      volume: _volumeFromJson(json['volume']),
    );

Map<String, dynamic> _$$ExerciseSetDtoImplToJson(
  _$ExerciseSetDtoImpl instance,
) => <String, dynamic>{
  'id': instance.id,
  'set_type': instance.setType,
  'subsets': instance.subsets.map((e) => e.toJson()).toList(),
  'volume': instance.reps,
  'working_weight': instance.weight,
  'rpe': instance.rpe,
  'order': instance.order,
  'exercise_instance': instance.exerciseInstanceId,
  'intensity': instance.intensity,
  'effort': instance.effort,
};
