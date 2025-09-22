// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'exercise_definition.dart';

// **************************************************************************
// JsonSerializableGenerator
// **************************************************************************

_$ExerciseDefinitionImpl _$$ExerciseDefinitionImplFromJson(
        Map<String, dynamic> json) =>
    _$ExerciseDefinitionImpl(
      id: (json['id'] as num?)?.toInt(),
      name: json['name'] as String,
      muscleGroup: json['muscle_group'] as String?,
      equipment: json['equipment'] as String?,
      targetMuscles: (json['target_muscles'] as List<dynamic>?)
          ?.map((e) => e as String)
          .toList(),
      synergistMuscles: (json['synergist_muscles'] as List<dynamic>?)
          ?.map((e) => e as String)
          .toList(),
      movementType: json['movement_type'] as String?,
      region: json['region'] as String?,
      oneRepMax: (json['oneRepMax'] as num?)?.toDouble(),
    );

Map<String, dynamic> _$$ExerciseDefinitionImplToJson(
        _$ExerciseDefinitionImpl instance) =>
    <String, dynamic>{
      'id': instance.id,
      'name': instance.name,
      'muscle_group': instance.muscleGroup,
      'equipment': instance.equipment,
      'target_muscles': instance.targetMuscles,
      'synergist_muscles': instance.synergistMuscles,
      'movement_type': instance.movementType,
      'region': instance.region,
      'oneRepMax': instance.oneRepMax,
    };
