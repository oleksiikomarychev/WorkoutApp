import 'package:flutter/foundation.dart';
import 'package:freezed_annotation/freezed_annotation.dart';

part 'workout_session.freezed.dart';
part 'workout_session.g.dart';

@freezed
class WorkoutSession with _$WorkoutSession {
  const WorkoutSession._();

  @JsonSerializable(explicitToJson: true)
  const factory WorkoutSession({
    int? id,
    @JsonKey(name: 'workout_id') required int workoutId,
    @JsonKey(name: 'started_at') required DateTime startedAt,
    @JsonKey(name: 'finished_at') DateTime? finishedAt,
    @Default('active') String status,
    @JsonKey(name: 'duration_seconds') int? durationSeconds,
    @Default(<String, dynamic>{}) Map<String, dynamic> progress,
    // Optional session metrics
    @JsonKey(name: 'device_source') String? deviceSource,
    @JsonKey(name: 'hr_avg') int? hrAvg,
    @JsonKey(name: 'hr_max') int? hrMax,
    @JsonKey(name: 'hydration_liters') double? hydrationLiters,
    String? mood,
    @JsonKey(name: 'injury_flags') Map<String, dynamic>? injuryFlags,
  }) = _WorkoutSession;

  factory WorkoutSession.fromJson(Map<String, dynamic> json) =>
      _$WorkoutSessionFromJson(json);

  // Convenience
  bool get isActive => status.toLowerCase() == 'active' && finishedAt == null;
}
