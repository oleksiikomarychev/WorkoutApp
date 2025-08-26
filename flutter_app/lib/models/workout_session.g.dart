// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'workout_session.dart';

// **************************************************************************
// JsonSerializableGenerator
// **************************************************************************

_$WorkoutSessionImpl _$$WorkoutSessionImplFromJson(Map<String, dynamic> json) =>
    _$WorkoutSessionImpl(
      id: (json['id'] as num?)?.toInt(),
      workoutId: (json['workout_id'] as num).toInt(),
      startedAt: DateTime.parse(json['started_at'] as String),
      endedAt: json['ended_at'] == null
          ? null
          : DateTime.parse(json['ended_at'] as String),
      status: json['status'] as String? ?? 'active',
      durationSeconds: (json['duration_seconds'] as num?)?.toInt(),
      progress: json['progress'] as Map<String, dynamic>? ??
          const <String, dynamic>{},
      deviceSource: json['device_source'] as String?,
      hrAvg: (json['hr_avg'] as num?)?.toInt(),
      hrMax: (json['hr_max'] as num?)?.toInt(),
      hydrationLiters: (json['hydration_liters'] as num?)?.toDouble(),
      mood: json['mood'] as String?,
      injuryFlags: json['injury_flags'] as Map<String, dynamic>?,
    );

Map<String, dynamic> _$$WorkoutSessionImplToJson(
        _$WorkoutSessionImpl instance) =>
    <String, dynamic>{
      'id': instance.id,
      'workout_id': instance.workoutId,
      'started_at': instance.startedAt.toIso8601String(),
      'ended_at': instance.endedAt?.toIso8601String(),
      'status': instance.status,
      'duration_seconds': instance.durationSeconds,
      'progress': instance.progress,
      'device_source': instance.deviceSource,
      'hr_avg': instance.hrAvg,
      'hr_max': instance.hrMax,
      'hydration_liters': instance.hydrationLiters,
      'mood': instance.mood,
      'injury_flags': instance.injuryFlags,
    };
