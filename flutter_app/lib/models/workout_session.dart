import 'package:flutter/foundation.dart';
import 'package:freezed_annotation/freezed_annotation.dart';

part 'workout_session.freezed.dart';
part 'workout_session.g.dart';

DateTime _parseDateTimeAssumeUtc(String value) {
  final s = value.trim();
  final hasTz = RegExp(r'(Z|[+-]\d{2}:\d{2})$').hasMatch(s);
  final parsed = DateTime.parse(hasTz ? s : '${s}Z');
  return parsed.toLocal();
}

DateTime? _parseDateTimeAssumeUtcNullable(String? value) {
  if (value == null) return null;
  return _parseDateTimeAssumeUtc(value);
}

String _dateTimeToIsoUtc(DateTime value) {
  return value.toUtc().toIso8601String();
}

String? _dateTimeToIsoUtcNullable(DateTime? value) {
  if (value == null) return null;
  return _dateTimeToIsoUtc(value);
}

@freezed
class WorkoutSession with _$WorkoutSession {
  const WorkoutSession._();

  @JsonSerializable(explicitToJson: true)
  const factory WorkoutSession({
    int? id,
    @JsonKey(name: 'workout_id') required int workoutId,
    @JsonKey(
      name: 'started_at',
      fromJson: _parseDateTimeAssumeUtc,
      toJson: _dateTimeToIsoUtc,
    )
    required DateTime startedAt,
    @JsonKey(
      name: 'finished_at',
      fromJson: _parseDateTimeAssumeUtcNullable,
      toJson: _dateTimeToIsoUtcNullable,
    )
    DateTime? finishedAt,
    @Default('active') String status,
    @JsonKey(name: 'duration_seconds') int? durationSeconds,
    @Default(<String, dynamic>{}) Map<String, dynamic> progress,

    @JsonKey(name: 'device_source') String? deviceSource,
    @JsonKey(name: 'hr_avg') int? hrAvg,
    @JsonKey(name: 'hr_max') int? hrMax,
    @JsonKey(name: 'hydration_liters') double? hydrationLiters,
    String? mood,
    @JsonKey(name: 'injury_flags') Map<String, dynamic>? injuryFlags,
  }) = _WorkoutSession;

  factory WorkoutSession.fromJson(Map<String, dynamic> json) =>
      _$WorkoutSessionFromJson(json);


  bool get isActive => status.toLowerCase() == 'active' && finishedAt == null;
}
