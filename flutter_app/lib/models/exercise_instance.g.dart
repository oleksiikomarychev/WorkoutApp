// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'exercise_instance.dart';

// **************************************************************************
// JsonSerializableGenerator
// **************************************************************************

_$ExerciseInstanceImpl _$$ExerciseInstanceImplFromJson(
        Map<String, dynamic> json) =>
    _$ExerciseInstanceImpl(
      id: (json['id'] as num?)?.toInt(),
      exerciseListId: (json['exercise_list_id'] as num).toInt(),
      exerciseDefinition: json['exercise_definition'] == null
          ? null
          : ExerciseDefinition.fromJson(
              json['exercise_definition'] as Map<String, dynamic>),
      workoutId: (json['workout_id'] as num?)?.toInt(),
      userMaxId: (json['user_max_id'] as num?)?.toInt(),
      sets: (json['sets'] as List<dynamic>?)
              ?.map((e) => ExerciseSetDto.fromJson(e as Map<String, dynamic>))
              .toList() ??
          const [],
      notes: json['notes'] as String?,
      order: (json['order'] as num?)?.toInt(),
    );

Map<String, dynamic> _$$ExerciseInstanceImplToJson(
        _$ExerciseInstanceImpl instance) =>
    <String, dynamic>{
      'id': instance.id,
      'exercise_list_id': instance.exerciseListId,
      'exercise_definition': instance.exerciseDefinition?.toJson(),
      'workout_id': instance.workoutId,
      'user_max_id': instance.userMaxId,
      'sets': instance.sets.map((e) => e.toJson()).toList(),
      'notes': instance.notes,
      'order': instance.order,
    };
