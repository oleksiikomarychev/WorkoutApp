// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'workout.dart';

// **************************************************************************
// JsonSerializableGenerator
// **************************************************************************

_$WorkoutImpl _$$WorkoutImplFromJson(Map<String, dynamic> json) =>
    _$WorkoutImpl(
      id: (json['id'] as num?)?.toInt(),
      name: json['name'] as String,
      notes: json['notes'] as String?,
      status: json['status'] as String?,
      startedAt: json['started_at'] == null
          ? null
          : DateTime.parse(json['started_at'] as String),
      durationSeconds: (json['duration_seconds'] as num?)?.toInt(),
      rpeSession: (json['rpe_session'] as num?)?.toDouble(),
      location: json['location'] as String?,
      readinessScore: (json['readiness_score'] as num?)?.toInt(),
      appliedPlanId: (json['applied_plan_id'] as num?)?.toInt(),
      planOrderIndex: (json['plan_order_index'] as num?)?.toInt(),
      scheduledFor: json['scheduled_for'] == null
          ? null
          : DateTime.parse(json['scheduled_for'] as String),
      completedAt: json['completed_at'] == null
          ? null
          : DateTime.parse(json['completed_at'] as String),
      exerciseInstances: (json['exercise_instances'] as List<dynamic>?)
              ?.map((e) => ExerciseInstance.fromJson(e as Map<String, dynamic>))
              .toList() ??
          const [],
    );

Map<String, dynamic> _$$WorkoutImplToJson(_$WorkoutImpl instance) =>
    <String, dynamic>{
      'id': instance.id,
      'name': instance.name,
      'notes': instance.notes,
      'status': instance.status,
      'started_at': instance.startedAt?.toIso8601String(),
      'duration_seconds': instance.durationSeconds,
      'rpe_session': instance.rpeSession,
      'location': instance.location,
      'readiness_score': instance.readinessScore,
      'applied_plan_id': instance.appliedPlanId,
      'plan_order_index': instance.planOrderIndex,
      'scheduled_for': instance.scheduledFor?.toIso8601String(),
      'completed_at': instance.completedAt?.toIso8601String(),
      'exercise_instances':
          instance.exerciseInstances.map((e) => e.toJson()).toList(),
    };
