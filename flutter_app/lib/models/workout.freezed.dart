// coverage:ignore-file




part of 'workout.dart';





T _$identity<T>(T value) => value;

final _privateConstructorUsedError = UnsupportedError(
    'It seems like you constructed your class using `MyClass._()`. This constructor is only meant to be used by freezed and you are not supposed to need it nor use it.\nPlease check the documentation here for more information: https://github.com/rrousselGit/freezed#adding-getters-and-methods-to-our-models');

Workout _$WorkoutFromJson(Map<String, dynamic> json) {
  return _Workout.fromJson(json);
}


mixin _$Workout {
  int? get id => throw _privateConstructorUsedError;
  String get name => throw _privateConstructorUsedError;
  String? get notes => throw _privateConstructorUsedError;
  @JsonKey(name: 'status')
  String? get status => throw _privateConstructorUsedError;
  @JsonKey(name: 'started_at')
  DateTime? get startedAt => throw _privateConstructorUsedError;
  @JsonKey(name: 'duration_seconds')
  int? get durationSeconds => throw _privateConstructorUsedError;
  @JsonKey(name: 'rpe_session')
  double? get rpeSession => throw _privateConstructorUsedError;
  String? get location => throw _privateConstructorUsedError;
  @JsonKey(name: 'readiness_score')
  int? get readinessScore =>
      throw _privateConstructorUsedError;
  @JsonKey(name: 'applied_plan_id')
  int? get appliedPlanId => throw _privateConstructorUsedError;
  @JsonKey(name: 'plan_order_index')
  int? get planOrderIndex =>
      throw _privateConstructorUsedError;
  @JsonKey(name: 'scheduled_for')
  DateTime? get scheduledFor => throw _privateConstructorUsedError;
  @JsonKey(name: 'completed_at')
  DateTime? get completedAt => throw _privateConstructorUsedError;
  @JsonKey(name: 'exercise_instances')
  List<ExerciseInstance> get exerciseInstances =>
      throw _privateConstructorUsedError;
  @JsonKey(includeFromJson: false, includeToJson: false)
  int? get localId => throw _privateConstructorUsedError;
  @JsonKey(name: 'next_workout_id')
  int? get nextWorkoutId =>
      throw _privateConstructorUsedError;
  @JsonKey(name: 'workout_type')
  WorkoutType get workoutType => throw _privateConstructorUsedError;


  Map<String, dynamic> toJson() => throw _privateConstructorUsedError;



  @JsonKey(includeFromJson: false, includeToJson: false)
  $WorkoutCopyWith<Workout> get copyWith => throw _privateConstructorUsedError;
}


abstract class $WorkoutCopyWith<$Res> {
  factory $WorkoutCopyWith(Workout value, $Res Function(Workout) then) =
      _$WorkoutCopyWithImpl<$Res, Workout>;
  @useResult
  $Res call(
      {int? id,
      String name,
      String? notes,
      @JsonKey(name: 'status') String? status,
      @JsonKey(name: 'started_at') DateTime? startedAt,
      @JsonKey(name: 'duration_seconds') int? durationSeconds,
      @JsonKey(name: 'rpe_session') double? rpeSession,
      String? location,
      @JsonKey(name: 'readiness_score') int? readinessScore,
      @JsonKey(name: 'applied_plan_id') int? appliedPlanId,
      @JsonKey(name: 'plan_order_index') int? planOrderIndex,
      @JsonKey(name: 'scheduled_for') DateTime? scheduledFor,
      @JsonKey(name: 'completed_at') DateTime? completedAt,
      @JsonKey(name: 'exercise_instances')
      List<ExerciseInstance> exerciseInstances,
      @JsonKey(includeFromJson: false, includeToJson: false) int? localId,
      @JsonKey(name: 'next_workout_id') int? nextWorkoutId,
      @JsonKey(name: 'workout_type') WorkoutType workoutType});
}


class _$WorkoutCopyWithImpl<$Res, $Val extends Workout>
    implements $WorkoutCopyWith<$Res> {
  _$WorkoutCopyWithImpl(this._value, this._then);

  // ignore: unused_field
  final $Val _value;
  // ignore: unused_field
  final $Res Function($Val) _then;



  @pragma('vm:prefer-inline')
  @override
  $Res call({
    Object? id = freezed,
    Object? name = null,
    Object? notes = freezed,
    Object? status = freezed,
    Object? startedAt = freezed,
    Object? durationSeconds = freezed,
    Object? rpeSession = freezed,
    Object? location = freezed,
    Object? readinessScore = freezed,
    Object? appliedPlanId = freezed,
    Object? planOrderIndex = freezed,
    Object? scheduledFor = freezed,
    Object? completedAt = freezed,
    Object? exerciseInstances = null,
    Object? localId = freezed,
    Object? nextWorkoutId = freezed,
    Object? workoutType = null,
  }) {
    return _then(_value.copyWith(
      id: freezed == id
          ? _value.id
          : id // ignore: cast_nullable_to_non_nullable
              as int?,
      name: null == name
          ? _value.name
          : name // ignore: cast_nullable_to_non_nullable
              as String,
      notes: freezed == notes
          ? _value.notes
          : notes // ignore: cast_nullable_to_non_nullable
              as String?,
      status: freezed == status
          ? _value.status
          : status // ignore: cast_nullable_to_non_nullable
              as String?,
      startedAt: freezed == startedAt
          ? _value.startedAt
          : startedAt // ignore: cast_nullable_to_non_nullable
              as DateTime?,
      durationSeconds: freezed == durationSeconds
          ? _value.durationSeconds
          : durationSeconds // ignore: cast_nullable_to_non_nullable
              as int?,
      rpeSession: freezed == rpeSession
          ? _value.rpeSession
          : rpeSession // ignore: cast_nullable_to_non_nullable
              as double?,
      location: freezed == location
          ? _value.location
          : location // ignore: cast_nullable_to_non_nullable
              as String?,
      readinessScore: freezed == readinessScore
          ? _value.readinessScore
          : readinessScore // ignore: cast_nullable_to_non_nullable
              as int?,
      appliedPlanId: freezed == appliedPlanId
          ? _value.appliedPlanId
          : appliedPlanId // ignore: cast_nullable_to_non_nullable
              as int?,
      planOrderIndex: freezed == planOrderIndex
          ? _value.planOrderIndex
          : planOrderIndex // ignore: cast_nullable_to_non_nullable
              as int?,
      scheduledFor: freezed == scheduledFor
          ? _value.scheduledFor
          : scheduledFor // ignore: cast_nullable_to_non_nullable
              as DateTime?,
      completedAt: freezed == completedAt
          ? _value.completedAt
          : completedAt // ignore: cast_nullable_to_non_nullable
              as DateTime?,
      exerciseInstances: null == exerciseInstances
          ? _value.exerciseInstances
          : exerciseInstances // ignore: cast_nullable_to_non_nullable
              as List<ExerciseInstance>,
      localId: freezed == localId
          ? _value.localId
          : localId // ignore: cast_nullable_to_non_nullable
              as int?,
      nextWorkoutId: freezed == nextWorkoutId
          ? _value.nextWorkoutId
          : nextWorkoutId // ignore: cast_nullable_to_non_nullable
              as int?,
      workoutType: null == workoutType
          ? _value.workoutType
          : workoutType // ignore: cast_nullable_to_non_nullable
              as WorkoutType,
    ) as $Val);
  }
}


abstract class _$$WorkoutImplCopyWith<$Res> implements $WorkoutCopyWith<$Res> {
  factory _$$WorkoutImplCopyWith(
          _$WorkoutImpl value, $Res Function(_$WorkoutImpl) then) =
      __$$WorkoutImplCopyWithImpl<$Res>;
  @override
  @useResult
  $Res call(
      {int? id,
      String name,
      String? notes,
      @JsonKey(name: 'status') String? status,
      @JsonKey(name: 'started_at') DateTime? startedAt,
      @JsonKey(name: 'duration_seconds') int? durationSeconds,
      @JsonKey(name: 'rpe_session') double? rpeSession,
      String? location,
      @JsonKey(name: 'readiness_score') int? readinessScore,
      @JsonKey(name: 'applied_plan_id') int? appliedPlanId,
      @JsonKey(name: 'plan_order_index') int? planOrderIndex,
      @JsonKey(name: 'scheduled_for') DateTime? scheduledFor,
      @JsonKey(name: 'completed_at') DateTime? completedAt,
      @JsonKey(name: 'exercise_instances')
      List<ExerciseInstance> exerciseInstances,
      @JsonKey(includeFromJson: false, includeToJson: false) int? localId,
      @JsonKey(name: 'next_workout_id') int? nextWorkoutId,
      @JsonKey(name: 'workout_type') WorkoutType workoutType});
}


class __$$WorkoutImplCopyWithImpl<$Res>
    extends _$WorkoutCopyWithImpl<$Res, _$WorkoutImpl>
    implements _$$WorkoutImplCopyWith<$Res> {
  __$$WorkoutImplCopyWithImpl(
      _$WorkoutImpl _value, $Res Function(_$WorkoutImpl) _then)
      : super(_value, _then);



  @pragma('vm:prefer-inline')
  @override
  $Res call({
    Object? id = freezed,
    Object? name = null,
    Object? notes = freezed,
    Object? status = freezed,
    Object? startedAt = freezed,
    Object? durationSeconds = freezed,
    Object? rpeSession = freezed,
    Object? location = freezed,
    Object? readinessScore = freezed,
    Object? appliedPlanId = freezed,
    Object? planOrderIndex = freezed,
    Object? scheduledFor = freezed,
    Object? completedAt = freezed,
    Object? exerciseInstances = null,
    Object? localId = freezed,
    Object? nextWorkoutId = freezed,
    Object? workoutType = null,
  }) {
    return _then(_$WorkoutImpl(
      id: freezed == id
          ? _value.id
          : id // ignore: cast_nullable_to_non_nullable
              as int?,
      name: null == name
          ? _value.name
          : name // ignore: cast_nullable_to_non_nullable
              as String,
      notes: freezed == notes
          ? _value.notes
          : notes // ignore: cast_nullable_to_non_nullable
              as String?,
      status: freezed == status
          ? _value.status
          : status // ignore: cast_nullable_to_non_nullable
              as String?,
      startedAt: freezed == startedAt
          ? _value.startedAt
          : startedAt // ignore: cast_nullable_to_non_nullable
              as DateTime?,
      durationSeconds: freezed == durationSeconds
          ? _value.durationSeconds
          : durationSeconds // ignore: cast_nullable_to_non_nullable
              as int?,
      rpeSession: freezed == rpeSession
          ? _value.rpeSession
          : rpeSession // ignore: cast_nullable_to_non_nullable
              as double?,
      location: freezed == location
          ? _value.location
          : location // ignore: cast_nullable_to_non_nullable
              as String?,
      readinessScore: freezed == readinessScore
          ? _value.readinessScore
          : readinessScore // ignore: cast_nullable_to_non_nullable
              as int?,
      appliedPlanId: freezed == appliedPlanId
          ? _value.appliedPlanId
          : appliedPlanId // ignore: cast_nullable_to_non_nullable
              as int?,
      planOrderIndex: freezed == planOrderIndex
          ? _value.planOrderIndex
          : planOrderIndex // ignore: cast_nullable_to_non_nullable
              as int?,
      scheduledFor: freezed == scheduledFor
          ? _value.scheduledFor
          : scheduledFor // ignore: cast_nullable_to_non_nullable
              as DateTime?,
      completedAt: freezed == completedAt
          ? _value.completedAt
          : completedAt // ignore: cast_nullable_to_non_nullable
              as DateTime?,
      exerciseInstances: null == exerciseInstances
          ? _value._exerciseInstances
          : exerciseInstances // ignore: cast_nullable_to_non_nullable
              as List<ExerciseInstance>,
      localId: freezed == localId
          ? _value.localId
          : localId // ignore: cast_nullable_to_non_nullable
              as int?,
      nextWorkoutId: freezed == nextWorkoutId
          ? _value.nextWorkoutId
          : nextWorkoutId // ignore: cast_nullable_to_non_nullable
              as int?,
      workoutType: null == workoutType
          ? _value.workoutType
          : workoutType // ignore: cast_nullable_to_non_nullable
              as WorkoutType,
    ));
  }
}



@JsonSerializable(explicitToJson: true)
class _$WorkoutImpl extends _Workout with DiagnosticableTreeMixin {
  const _$WorkoutImpl(
      {this.id,
      required this.name,
      this.notes,
      @JsonKey(name: 'status') this.status,
      @JsonKey(name: 'started_at') this.startedAt,
      @JsonKey(name: 'duration_seconds') this.durationSeconds,
      @JsonKey(name: 'rpe_session') this.rpeSession,
      this.location,
      @JsonKey(name: 'readiness_score') this.readinessScore,
      @JsonKey(name: 'applied_plan_id') this.appliedPlanId,
      @JsonKey(name: 'plan_order_index') this.planOrderIndex,
      @JsonKey(name: 'scheduled_for') this.scheduledFor,
      @JsonKey(name: 'completed_at') this.completedAt,
      @JsonKey(name: 'exercise_instances')
      final List<ExerciseInstance> exerciseInstances = const [],
      @JsonKey(includeFromJson: false, includeToJson: false) this.localId,
      @JsonKey(name: 'next_workout_id') this.nextWorkoutId,
      @JsonKey(name: 'workout_type') this.workoutType = WorkoutType.manual})
      : _exerciseInstances = exerciseInstances,
        super._();

  factory _$WorkoutImpl.fromJson(Map<String, dynamic> json) =>
      _$$WorkoutImplFromJson(json);

  @override
  final int? id;
  @override
  final String name;
  @override
  final String? notes;
  @override
  @JsonKey(name: 'status')
  final String? status;
  @override
  @JsonKey(name: 'started_at')
  final DateTime? startedAt;
  @override
  @JsonKey(name: 'duration_seconds')
  final int? durationSeconds;
  @override
  @JsonKey(name: 'rpe_session')
  final double? rpeSession;
  @override
  final String? location;
  @override
  @JsonKey(name: 'readiness_score')
  final int? readinessScore;

  @override
  @JsonKey(name: 'applied_plan_id')
  final int? appliedPlanId;
  @override
  @JsonKey(name: 'plan_order_index')
  final int? planOrderIndex;

  @override
  @JsonKey(name: 'scheduled_for')
  final DateTime? scheduledFor;
  @override
  @JsonKey(name: 'completed_at')
  final DateTime? completedAt;
  final List<ExerciseInstance> _exerciseInstances;
  @override
  @JsonKey(name: 'exercise_instances')
  List<ExerciseInstance> get exerciseInstances {
    if (_exerciseInstances is EqualUnmodifiableListView)
      return _exerciseInstances;
    // ignore: implicit_dynamic_type
    return EqualUnmodifiableListView(_exerciseInstances);
  }

  @override
  @JsonKey(includeFromJson: false, includeToJson: false)
  final int? localId;
  @override
  @JsonKey(name: 'next_workout_id')
  final int? nextWorkoutId;

  @override
  @JsonKey(name: 'workout_type')
  final WorkoutType workoutType;

  @override
  String toString({DiagnosticLevel minLevel = DiagnosticLevel.info}) {
    return 'Workout(id: $id, name: $name, notes: $notes, status: $status, startedAt: $startedAt, durationSeconds: $durationSeconds, rpeSession: $rpeSession, location: $location, readinessScore: $readinessScore, appliedPlanId: $appliedPlanId, planOrderIndex: $planOrderIndex, scheduledFor: $scheduledFor, completedAt: $completedAt, exerciseInstances: $exerciseInstances, localId: $localId, nextWorkoutId: $nextWorkoutId, workoutType: $workoutType)';
  }

  @override
  void debugFillProperties(DiagnosticPropertiesBuilder properties) {
    super.debugFillProperties(properties);
    properties
      ..add(DiagnosticsProperty('type', 'Workout'))
      ..add(DiagnosticsProperty('id', id))
      ..add(DiagnosticsProperty('name', name))
      ..add(DiagnosticsProperty('notes', notes))
      ..add(DiagnosticsProperty('status', status))
      ..add(DiagnosticsProperty('startedAt', startedAt))
      ..add(DiagnosticsProperty('durationSeconds', durationSeconds))
      ..add(DiagnosticsProperty('rpeSession', rpeSession))
      ..add(DiagnosticsProperty('location', location))
      ..add(DiagnosticsProperty('readinessScore', readinessScore))
      ..add(DiagnosticsProperty('appliedPlanId', appliedPlanId))
      ..add(DiagnosticsProperty('planOrderIndex', planOrderIndex))
      ..add(DiagnosticsProperty('scheduledFor', scheduledFor))
      ..add(DiagnosticsProperty('completedAt', completedAt))
      ..add(DiagnosticsProperty('exerciseInstances', exerciseInstances))
      ..add(DiagnosticsProperty('localId', localId))
      ..add(DiagnosticsProperty('nextWorkoutId', nextWorkoutId))
      ..add(DiagnosticsProperty('workoutType', workoutType));
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) ||
        (other.runtimeType == runtimeType &&
            other is _$WorkoutImpl &&
            (identical(other.id, id) || other.id == id) &&
            (identical(other.name, name) || other.name == name) &&
            (identical(other.notes, notes) || other.notes == notes) &&
            (identical(other.status, status) || other.status == status) &&
            (identical(other.startedAt, startedAt) ||
                other.startedAt == startedAt) &&
            (identical(other.durationSeconds, durationSeconds) ||
                other.durationSeconds == durationSeconds) &&
            (identical(other.rpeSession, rpeSession) ||
                other.rpeSession == rpeSession) &&
            (identical(other.location, location) ||
                other.location == location) &&
            (identical(other.readinessScore, readinessScore) ||
                other.readinessScore == readinessScore) &&
            (identical(other.appliedPlanId, appliedPlanId) ||
                other.appliedPlanId == appliedPlanId) &&
            (identical(other.planOrderIndex, planOrderIndex) ||
                other.planOrderIndex == planOrderIndex) &&
            (identical(other.scheduledFor, scheduledFor) ||
                other.scheduledFor == scheduledFor) &&
            (identical(other.completedAt, completedAt) ||
                other.completedAt == completedAt) &&
            const DeepCollectionEquality()
                .equals(other._exerciseInstances, _exerciseInstances) &&
            (identical(other.localId, localId) || other.localId == localId) &&
            (identical(other.nextWorkoutId, nextWorkoutId) ||
                other.nextWorkoutId == nextWorkoutId) &&
            (identical(other.workoutType, workoutType) ||
                other.workoutType == workoutType));
  }

  @JsonKey(includeFromJson: false, includeToJson: false)
  @override
  int get hashCode => Object.hash(
      runtimeType,
      id,
      name,
      notes,
      status,
      startedAt,
      durationSeconds,
      rpeSession,
      location,
      readinessScore,
      appliedPlanId,
      planOrderIndex,
      scheduledFor,
      completedAt,
      const DeepCollectionEquality().hash(_exerciseInstances),
      localId,
      nextWorkoutId,
      workoutType);



  @JsonKey(includeFromJson: false, includeToJson: false)
  @override
  @pragma('vm:prefer-inline')
  _$$WorkoutImplCopyWith<_$WorkoutImpl> get copyWith =>
      __$$WorkoutImplCopyWithImpl<_$WorkoutImpl>(this, _$identity);

  @override
  Map<String, dynamic> toJson() {
    return _$$WorkoutImplToJson(
      this,
    );
  }
}

abstract class _Workout extends Workout {
  const factory _Workout(
      {final int? id,
      required final String name,
      final String? notes,
      @JsonKey(name: 'status') final String? status,
      @JsonKey(name: 'started_at') final DateTime? startedAt,
      @JsonKey(name: 'duration_seconds') final int? durationSeconds,
      @JsonKey(name: 'rpe_session') final double? rpeSession,
      final String? location,
      @JsonKey(name: 'readiness_score') final int? readinessScore,
      @JsonKey(name: 'applied_plan_id') final int? appliedPlanId,
      @JsonKey(name: 'plan_order_index') final int? planOrderIndex,
      @JsonKey(name: 'scheduled_for') final DateTime? scheduledFor,
      @JsonKey(name: 'completed_at') final DateTime? completedAt,
      @JsonKey(name: 'exercise_instances')
      final List<ExerciseInstance> exerciseInstances,
      @JsonKey(includeFromJson: false, includeToJson: false) final int? localId,
      @JsonKey(name: 'next_workout_id') final int? nextWorkoutId,
      @JsonKey(name: 'workout_type')
      final WorkoutType workoutType}) = _$WorkoutImpl;
  const _Workout._() : super._();

  factory _Workout.fromJson(Map<String, dynamic> json) = _$WorkoutImpl.fromJson;

  @override
  int? get id;
  @override
  String get name;
  @override
  String? get notes;
  @override
  @JsonKey(name: 'status')
  String? get status;
  @override
  @JsonKey(name: 'started_at')
  DateTime? get startedAt;
  @override
  @JsonKey(name: 'duration_seconds')
  int? get durationSeconds;
  @override
  @JsonKey(name: 'rpe_session')
  double? get rpeSession;
  @override
  String? get location;
  @override
  @JsonKey(name: 'readiness_score')
  int?
      get readinessScore;
  @override
  @JsonKey(name: 'applied_plan_id')
  int? get appliedPlanId;
  @override
  @JsonKey(name: 'plan_order_index')
  int? get planOrderIndex;
  @override
  @JsonKey(name: 'scheduled_for')
  DateTime? get scheduledFor;
  @override
  @JsonKey(name: 'completed_at')
  DateTime? get completedAt;
  @override
  @JsonKey(name: 'exercise_instances')
  List<ExerciseInstance> get exerciseInstances;
  @override
  @JsonKey(includeFromJson: false, includeToJson: false)
  int? get localId;
  @override
  @JsonKey(name: 'next_workout_id')
  int? get nextWorkoutId;
  @override
  @JsonKey(name: 'workout_type')
  WorkoutType get workoutType;



  @override
  @JsonKey(includeFromJson: false, includeToJson: false)
  _$$WorkoutImplCopyWith<_$WorkoutImpl> get copyWith =>
      throw _privateConstructorUsedError;
}
