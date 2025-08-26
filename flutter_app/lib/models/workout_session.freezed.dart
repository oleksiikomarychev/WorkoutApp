// coverage:ignore-file
// GENERATED CODE - DO NOT MODIFY BY HAND
// ignore_for_file: type=lint
// ignore_for_file: unused_element, deprecated_member_use, deprecated_member_use_from_same_package, use_function_type_syntax_for_parameters, unnecessary_const, avoid_init_to_null, invalid_override_different_default_values_named, prefer_expression_function_bodies, annotate_overrides, invalid_annotation_target, unnecessary_question_mark

part of 'workout_session.dart';

// **************************************************************************
// FreezedGenerator
// **************************************************************************

T _$identity<T>(T value) => value;

final _privateConstructorUsedError = UnsupportedError(
    'It seems like you constructed your class using `MyClass._()`. This constructor is only meant to be used by freezed and you are not supposed to need it nor use it.\nPlease check the documentation here for more information: https://github.com/rrousselGit/freezed#adding-getters-and-methods-to-our-models');

WorkoutSession _$WorkoutSessionFromJson(Map<String, dynamic> json) {
  return _WorkoutSession.fromJson(json);
}

/// @nodoc
mixin _$WorkoutSession {
  int? get id => throw _privateConstructorUsedError;
  @JsonKey(name: 'workout_id')
  int get workoutId => throw _privateConstructorUsedError;
  @JsonKey(name: 'started_at')
  DateTime get startedAt => throw _privateConstructorUsedError;
  @JsonKey(name: 'ended_at')
  DateTime? get endedAt => throw _privateConstructorUsedError;
  String get status => throw _privateConstructorUsedError;
  @JsonKey(name: 'duration_seconds')
  int? get durationSeconds => throw _privateConstructorUsedError;
  Map<String, dynamic> get progress =>
      throw _privateConstructorUsedError; // Optional session metrics
  @JsonKey(name: 'device_source')
  String? get deviceSource => throw _privateConstructorUsedError;
  @JsonKey(name: 'hr_avg')
  int? get hrAvg => throw _privateConstructorUsedError;
  @JsonKey(name: 'hr_max')
  int? get hrMax => throw _privateConstructorUsedError;
  @JsonKey(name: 'hydration_liters')
  double? get hydrationLiters => throw _privateConstructorUsedError;
  String? get mood => throw _privateConstructorUsedError;
  @JsonKey(name: 'injury_flags')
  Map<String, dynamic>? get injuryFlags => throw _privateConstructorUsedError;

  /// Serializes this WorkoutSession to a JSON map.
  Map<String, dynamic> toJson() => throw _privateConstructorUsedError;

  /// Create a copy of WorkoutSession
  /// with the given fields replaced by the non-null parameter values.
  @JsonKey(includeFromJson: false, includeToJson: false)
  $WorkoutSessionCopyWith<WorkoutSession> get copyWith =>
      throw _privateConstructorUsedError;
}

/// @nodoc
abstract class $WorkoutSessionCopyWith<$Res> {
  factory $WorkoutSessionCopyWith(
          WorkoutSession value, $Res Function(WorkoutSession) then) =
      _$WorkoutSessionCopyWithImpl<$Res, WorkoutSession>;
  @useResult
  $Res call(
      {int? id,
      @JsonKey(name: 'workout_id') int workoutId,
      @JsonKey(name: 'started_at') DateTime startedAt,
      @JsonKey(name: 'ended_at') DateTime? endedAt,
      String status,
      @JsonKey(name: 'duration_seconds') int? durationSeconds,
      Map<String, dynamic> progress,
      @JsonKey(name: 'device_source') String? deviceSource,
      @JsonKey(name: 'hr_avg') int? hrAvg,
      @JsonKey(name: 'hr_max') int? hrMax,
      @JsonKey(name: 'hydration_liters') double? hydrationLiters,
      String? mood,
      @JsonKey(name: 'injury_flags') Map<String, dynamic>? injuryFlags});
}

/// @nodoc
class _$WorkoutSessionCopyWithImpl<$Res, $Val extends WorkoutSession>
    implements $WorkoutSessionCopyWith<$Res> {
  _$WorkoutSessionCopyWithImpl(this._value, this._then);

  // ignore: unused_field
  final $Val _value;
  // ignore: unused_field
  final $Res Function($Val) _then;

  /// Create a copy of WorkoutSession
  /// with the given fields replaced by the non-null parameter values.
  @pragma('vm:prefer-inline')
  @override
  $Res call({
    Object? id = freezed,
    Object? workoutId = null,
    Object? startedAt = null,
    Object? endedAt = freezed,
    Object? status = null,
    Object? durationSeconds = freezed,
    Object? progress = null,
    Object? deviceSource = freezed,
    Object? hrAvg = freezed,
    Object? hrMax = freezed,
    Object? hydrationLiters = freezed,
    Object? mood = freezed,
    Object? injuryFlags = freezed,
  }) {
    return _then(_value.copyWith(
      id: freezed == id
          ? _value.id
          : id // ignore: cast_nullable_to_non_nullable
              as int?,
      workoutId: null == workoutId
          ? _value.workoutId
          : workoutId // ignore: cast_nullable_to_non_nullable
              as int,
      startedAt: null == startedAt
          ? _value.startedAt
          : startedAt // ignore: cast_nullable_to_non_nullable
              as DateTime,
      endedAt: freezed == endedAt
          ? _value.endedAt
          : endedAt // ignore: cast_nullable_to_non_nullable
              as DateTime?,
      status: null == status
          ? _value.status
          : status // ignore: cast_nullable_to_non_nullable
              as String,
      durationSeconds: freezed == durationSeconds
          ? _value.durationSeconds
          : durationSeconds // ignore: cast_nullable_to_non_nullable
              as int?,
      progress: null == progress
          ? _value.progress
          : progress // ignore: cast_nullable_to_non_nullable
              as Map<String, dynamic>,
      deviceSource: freezed == deviceSource
          ? _value.deviceSource
          : deviceSource // ignore: cast_nullable_to_non_nullable
              as String?,
      hrAvg: freezed == hrAvg
          ? _value.hrAvg
          : hrAvg // ignore: cast_nullable_to_non_nullable
              as int?,
      hrMax: freezed == hrMax
          ? _value.hrMax
          : hrMax // ignore: cast_nullable_to_non_nullable
              as int?,
      hydrationLiters: freezed == hydrationLiters
          ? _value.hydrationLiters
          : hydrationLiters // ignore: cast_nullable_to_non_nullable
              as double?,
      mood: freezed == mood
          ? _value.mood
          : mood // ignore: cast_nullable_to_non_nullable
              as String?,
      injuryFlags: freezed == injuryFlags
          ? _value.injuryFlags
          : injuryFlags // ignore: cast_nullable_to_non_nullable
              as Map<String, dynamic>?,
    ) as $Val);
  }
}

/// @nodoc
abstract class _$$WorkoutSessionImplCopyWith<$Res>
    implements $WorkoutSessionCopyWith<$Res> {
  factory _$$WorkoutSessionImplCopyWith(_$WorkoutSessionImpl value,
          $Res Function(_$WorkoutSessionImpl) then) =
      __$$WorkoutSessionImplCopyWithImpl<$Res>;
  @override
  @useResult
  $Res call(
      {int? id,
      @JsonKey(name: 'workout_id') int workoutId,
      @JsonKey(name: 'started_at') DateTime startedAt,
      @JsonKey(name: 'ended_at') DateTime? endedAt,
      String status,
      @JsonKey(name: 'duration_seconds') int? durationSeconds,
      Map<String, dynamic> progress,
      @JsonKey(name: 'device_source') String? deviceSource,
      @JsonKey(name: 'hr_avg') int? hrAvg,
      @JsonKey(name: 'hr_max') int? hrMax,
      @JsonKey(name: 'hydration_liters') double? hydrationLiters,
      String? mood,
      @JsonKey(name: 'injury_flags') Map<String, dynamic>? injuryFlags});
}

/// @nodoc
class __$$WorkoutSessionImplCopyWithImpl<$Res>
    extends _$WorkoutSessionCopyWithImpl<$Res, _$WorkoutSessionImpl>
    implements _$$WorkoutSessionImplCopyWith<$Res> {
  __$$WorkoutSessionImplCopyWithImpl(
      _$WorkoutSessionImpl _value, $Res Function(_$WorkoutSessionImpl) _then)
      : super(_value, _then);

  /// Create a copy of WorkoutSession
  /// with the given fields replaced by the non-null parameter values.
  @pragma('vm:prefer-inline')
  @override
  $Res call({
    Object? id = freezed,
    Object? workoutId = null,
    Object? startedAt = null,
    Object? endedAt = freezed,
    Object? status = null,
    Object? durationSeconds = freezed,
    Object? progress = null,
    Object? deviceSource = freezed,
    Object? hrAvg = freezed,
    Object? hrMax = freezed,
    Object? hydrationLiters = freezed,
    Object? mood = freezed,
    Object? injuryFlags = freezed,
  }) {
    return _then(_$WorkoutSessionImpl(
      id: freezed == id
          ? _value.id
          : id // ignore: cast_nullable_to_non_nullable
              as int?,
      workoutId: null == workoutId
          ? _value.workoutId
          : workoutId // ignore: cast_nullable_to_non_nullable
              as int,
      startedAt: null == startedAt
          ? _value.startedAt
          : startedAt // ignore: cast_nullable_to_non_nullable
              as DateTime,
      endedAt: freezed == endedAt
          ? _value.endedAt
          : endedAt // ignore: cast_nullable_to_non_nullable
              as DateTime?,
      status: null == status
          ? _value.status
          : status // ignore: cast_nullable_to_non_nullable
              as String,
      durationSeconds: freezed == durationSeconds
          ? _value.durationSeconds
          : durationSeconds // ignore: cast_nullable_to_non_nullable
              as int?,
      progress: null == progress
          ? _value._progress
          : progress // ignore: cast_nullable_to_non_nullable
              as Map<String, dynamic>,
      deviceSource: freezed == deviceSource
          ? _value.deviceSource
          : deviceSource // ignore: cast_nullable_to_non_nullable
              as String?,
      hrAvg: freezed == hrAvg
          ? _value.hrAvg
          : hrAvg // ignore: cast_nullable_to_non_nullable
              as int?,
      hrMax: freezed == hrMax
          ? _value.hrMax
          : hrMax // ignore: cast_nullable_to_non_nullable
              as int?,
      hydrationLiters: freezed == hydrationLiters
          ? _value.hydrationLiters
          : hydrationLiters // ignore: cast_nullable_to_non_nullable
              as double?,
      mood: freezed == mood
          ? _value.mood
          : mood // ignore: cast_nullable_to_non_nullable
              as String?,
      injuryFlags: freezed == injuryFlags
          ? _value._injuryFlags
          : injuryFlags // ignore: cast_nullable_to_non_nullable
              as Map<String, dynamic>?,
    ));
  }
}

/// @nodoc

@JsonSerializable(explicitToJson: true)
class _$WorkoutSessionImpl extends _WorkoutSession
    with DiagnosticableTreeMixin {
  const _$WorkoutSessionImpl(
      {this.id,
      @JsonKey(name: 'workout_id') required this.workoutId,
      @JsonKey(name: 'started_at') required this.startedAt,
      @JsonKey(name: 'ended_at') this.endedAt,
      this.status = 'active',
      @JsonKey(name: 'duration_seconds') this.durationSeconds,
      final Map<String, dynamic> progress = const <String, dynamic>{},
      @JsonKey(name: 'device_source') this.deviceSource,
      @JsonKey(name: 'hr_avg') this.hrAvg,
      @JsonKey(name: 'hr_max') this.hrMax,
      @JsonKey(name: 'hydration_liters') this.hydrationLiters,
      this.mood,
      @JsonKey(name: 'injury_flags') final Map<String, dynamic>? injuryFlags})
      : _progress = progress,
        _injuryFlags = injuryFlags,
        super._();

  factory _$WorkoutSessionImpl.fromJson(Map<String, dynamic> json) =>
      _$$WorkoutSessionImplFromJson(json);

  @override
  final int? id;
  @override
  @JsonKey(name: 'workout_id')
  final int workoutId;
  @override
  @JsonKey(name: 'started_at')
  final DateTime startedAt;
  @override
  @JsonKey(name: 'ended_at')
  final DateTime? endedAt;
  @override
  @JsonKey()
  final String status;
  @override
  @JsonKey(name: 'duration_seconds')
  final int? durationSeconds;
  final Map<String, dynamic> _progress;
  @override
  @JsonKey()
  Map<String, dynamic> get progress {
    if (_progress is EqualUnmodifiableMapView) return _progress;
    // ignore: implicit_dynamic_type
    return EqualUnmodifiableMapView(_progress);
  }

// Optional session metrics
  @override
  @JsonKey(name: 'device_source')
  final String? deviceSource;
  @override
  @JsonKey(name: 'hr_avg')
  final int? hrAvg;
  @override
  @JsonKey(name: 'hr_max')
  final int? hrMax;
  @override
  @JsonKey(name: 'hydration_liters')
  final double? hydrationLiters;
  @override
  final String? mood;
  final Map<String, dynamic>? _injuryFlags;
  @override
  @JsonKey(name: 'injury_flags')
  Map<String, dynamic>? get injuryFlags {
    final value = _injuryFlags;
    if (value == null) return null;
    if (_injuryFlags is EqualUnmodifiableMapView) return _injuryFlags;
    // ignore: implicit_dynamic_type
    return EqualUnmodifiableMapView(value);
  }

  @override
  String toString({DiagnosticLevel minLevel = DiagnosticLevel.info}) {
    return 'WorkoutSession(id: $id, workoutId: $workoutId, startedAt: $startedAt, endedAt: $endedAt, status: $status, durationSeconds: $durationSeconds, progress: $progress, deviceSource: $deviceSource, hrAvg: $hrAvg, hrMax: $hrMax, hydrationLiters: $hydrationLiters, mood: $mood, injuryFlags: $injuryFlags)';
  }

  @override
  void debugFillProperties(DiagnosticPropertiesBuilder properties) {
    super.debugFillProperties(properties);
    properties
      ..add(DiagnosticsProperty('type', 'WorkoutSession'))
      ..add(DiagnosticsProperty('id', id))
      ..add(DiagnosticsProperty('workoutId', workoutId))
      ..add(DiagnosticsProperty('startedAt', startedAt))
      ..add(DiagnosticsProperty('endedAt', endedAt))
      ..add(DiagnosticsProperty('status', status))
      ..add(DiagnosticsProperty('durationSeconds', durationSeconds))
      ..add(DiagnosticsProperty('progress', progress))
      ..add(DiagnosticsProperty('deviceSource', deviceSource))
      ..add(DiagnosticsProperty('hrAvg', hrAvg))
      ..add(DiagnosticsProperty('hrMax', hrMax))
      ..add(DiagnosticsProperty('hydrationLiters', hydrationLiters))
      ..add(DiagnosticsProperty('mood', mood))
      ..add(DiagnosticsProperty('injuryFlags', injuryFlags));
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) ||
        (other.runtimeType == runtimeType &&
            other is _$WorkoutSessionImpl &&
            (identical(other.id, id) || other.id == id) &&
            (identical(other.workoutId, workoutId) ||
                other.workoutId == workoutId) &&
            (identical(other.startedAt, startedAt) ||
                other.startedAt == startedAt) &&
            (identical(other.endedAt, endedAt) || other.endedAt == endedAt) &&
            (identical(other.status, status) || other.status == status) &&
            (identical(other.durationSeconds, durationSeconds) ||
                other.durationSeconds == durationSeconds) &&
            const DeepCollectionEquality().equals(other._progress, _progress) &&
            (identical(other.deviceSource, deviceSource) ||
                other.deviceSource == deviceSource) &&
            (identical(other.hrAvg, hrAvg) || other.hrAvg == hrAvg) &&
            (identical(other.hrMax, hrMax) || other.hrMax == hrMax) &&
            (identical(other.hydrationLiters, hydrationLiters) ||
                other.hydrationLiters == hydrationLiters) &&
            (identical(other.mood, mood) || other.mood == mood) &&
            const DeepCollectionEquality()
                .equals(other._injuryFlags, _injuryFlags));
  }

  @JsonKey(includeFromJson: false, includeToJson: false)
  @override
  int get hashCode => Object.hash(
      runtimeType,
      id,
      workoutId,
      startedAt,
      endedAt,
      status,
      durationSeconds,
      const DeepCollectionEquality().hash(_progress),
      deviceSource,
      hrAvg,
      hrMax,
      hydrationLiters,
      mood,
      const DeepCollectionEquality().hash(_injuryFlags));

  /// Create a copy of WorkoutSession
  /// with the given fields replaced by the non-null parameter values.
  @JsonKey(includeFromJson: false, includeToJson: false)
  @override
  @pragma('vm:prefer-inline')
  _$$WorkoutSessionImplCopyWith<_$WorkoutSessionImpl> get copyWith =>
      __$$WorkoutSessionImplCopyWithImpl<_$WorkoutSessionImpl>(
          this, _$identity);

  @override
  Map<String, dynamic> toJson() {
    return _$$WorkoutSessionImplToJson(
      this,
    );
  }
}

abstract class _WorkoutSession extends WorkoutSession {
  const factory _WorkoutSession(
      {final int? id,
      @JsonKey(name: 'workout_id') required final int workoutId,
      @JsonKey(name: 'started_at') required final DateTime startedAt,
      @JsonKey(name: 'ended_at') final DateTime? endedAt,
      final String status,
      @JsonKey(name: 'duration_seconds') final int? durationSeconds,
      final Map<String, dynamic> progress,
      @JsonKey(name: 'device_source') final String? deviceSource,
      @JsonKey(name: 'hr_avg') final int? hrAvg,
      @JsonKey(name: 'hr_max') final int? hrMax,
      @JsonKey(name: 'hydration_liters') final double? hydrationLiters,
      final String? mood,
      @JsonKey(name: 'injury_flags')
      final Map<String, dynamic>? injuryFlags}) = _$WorkoutSessionImpl;
  const _WorkoutSession._() : super._();

  factory _WorkoutSession.fromJson(Map<String, dynamic> json) =
      _$WorkoutSessionImpl.fromJson;

  @override
  int? get id;
  @override
  @JsonKey(name: 'workout_id')
  int get workoutId;
  @override
  @JsonKey(name: 'started_at')
  DateTime get startedAt;
  @override
  @JsonKey(name: 'ended_at')
  DateTime? get endedAt;
  @override
  String get status;
  @override
  @JsonKey(name: 'duration_seconds')
  int? get durationSeconds;
  @override
  Map<String, dynamic> get progress; // Optional session metrics
  @override
  @JsonKey(name: 'device_source')
  String? get deviceSource;
  @override
  @JsonKey(name: 'hr_avg')
  int? get hrAvg;
  @override
  @JsonKey(name: 'hr_max')
  int? get hrMax;
  @override
  @JsonKey(name: 'hydration_liters')
  double? get hydrationLiters;
  @override
  String? get mood;
  @override
  @JsonKey(name: 'injury_flags')
  Map<String, dynamic>? get injuryFlags;

  /// Create a copy of WorkoutSession
  /// with the given fields replaced by the non-null parameter values.
  @override
  @JsonKey(includeFromJson: false, includeToJson: false)
  _$$WorkoutSessionImplCopyWith<_$WorkoutSessionImpl> get copyWith =>
      throw _privateConstructorUsedError;
}
