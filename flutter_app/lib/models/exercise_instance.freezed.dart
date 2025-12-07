// coverage:ignore-file




part of 'exercise_instance.dart';





T _$identity<T>(T value) => value;

final _privateConstructorUsedError = UnsupportedError(
    'It seems like you constructed your class using `MyClass._()`. This constructor is only meant to be used by freezed and you are not supposed to need it nor use it.\nPlease check the documentation here for more information: https://github.com/rrousselGit/freezed#adding-getters-and-methods-to-our-models');

ExerciseInstance _$ExerciseInstanceFromJson(Map<String, dynamic> json) {
  return _ExerciseInstance.fromJson(json);
}


mixin _$ExerciseInstance {
  int? get id => throw _privateConstructorUsedError;
  @JsonKey(name: 'exercise_list_id')
  int get exerciseListId => throw _privateConstructorUsedError;
  @JsonKey(name: 'exercise_definition')
  ExerciseDefinition? get exerciseDefinition =>
      throw _privateConstructorUsedError;
  @JsonKey(name: 'workout_id')
  int? get workoutId => throw _privateConstructorUsedError;
  @JsonKey(name: 'user_max_id')
  int? get userMaxId => throw _privateConstructorUsedError;
  List<ExerciseSetDto> get sets => throw _privateConstructorUsedError;
  String? get notes => throw _privateConstructorUsedError;
  @JsonKey(name: 'order')
  int? get order => throw _privateConstructorUsedError;
  @JsonKey(includeFromJson: false, includeToJson: false)
  int? get localId => throw _privateConstructorUsedError;


  Map<String, dynamic> toJson() => throw _privateConstructorUsedError;



  @JsonKey(includeFromJson: false, includeToJson: false)
  $ExerciseInstanceCopyWith<ExerciseInstance> get copyWith =>
      throw _privateConstructorUsedError;
}


abstract class $ExerciseInstanceCopyWith<$Res> {
  factory $ExerciseInstanceCopyWith(
          ExerciseInstance value, $Res Function(ExerciseInstance) then) =
      _$ExerciseInstanceCopyWithImpl<$Res, ExerciseInstance>;
  @useResult
  $Res call(
      {int? id,
      @JsonKey(name: 'exercise_list_id') int exerciseListId,
      @JsonKey(name: 'exercise_definition')
      ExerciseDefinition? exerciseDefinition,
      @JsonKey(name: 'workout_id') int? workoutId,
      @JsonKey(name: 'user_max_id') int? userMaxId,
      List<ExerciseSetDto> sets,
      String? notes,
      @JsonKey(name: 'order') int? order,
      @JsonKey(includeFromJson: false, includeToJson: false) int? localId});

  $ExerciseDefinitionCopyWith<$Res>? get exerciseDefinition;
}


class _$ExerciseInstanceCopyWithImpl<$Res, $Val extends ExerciseInstance>
    implements $ExerciseInstanceCopyWith<$Res> {
  _$ExerciseInstanceCopyWithImpl(this._value, this._then);

  // ignore: unused_field
  final $Val _value;
  // ignore: unused_field
  final $Res Function($Val) _then;



  @pragma('vm:prefer-inline')
  @override
  $Res call({
    Object? id = freezed,
    Object? exerciseListId = null,
    Object? exerciseDefinition = freezed,
    Object? workoutId = freezed,
    Object? userMaxId = freezed,
    Object? sets = null,
    Object? notes = freezed,
    Object? order = freezed,
    Object? localId = freezed,
  }) {
    return _then(_value.copyWith(
      id: freezed == id
          ? _value.id
          : id // ignore: cast_nullable_to_non_nullable
              as int?,
      exerciseListId: null == exerciseListId
          ? _value.exerciseListId
          : exerciseListId // ignore: cast_nullable_to_non_nullable
              as int,
      exerciseDefinition: freezed == exerciseDefinition
          ? _value.exerciseDefinition
          : exerciseDefinition // ignore: cast_nullable_to_non_nullable
              as ExerciseDefinition?,
      workoutId: freezed == workoutId
          ? _value.workoutId
          : workoutId // ignore: cast_nullable_to_non_nullable
              as int?,
      userMaxId: freezed == userMaxId
          ? _value.userMaxId
          : userMaxId // ignore: cast_nullable_to_non_nullable
              as int?,
      sets: null == sets
          ? _value.sets
          : sets // ignore: cast_nullable_to_non_nullable
              as List<ExerciseSetDto>,
      notes: freezed == notes
          ? _value.notes
          : notes // ignore: cast_nullable_to_non_nullable
              as String?,
      order: freezed == order
          ? _value.order
          : order // ignore: cast_nullable_to_non_nullable
              as int?,
      localId: freezed == localId
          ? _value.localId
          : localId // ignore: cast_nullable_to_non_nullable
              as int?,
    ) as $Val);
  }



  @override
  @pragma('vm:prefer-inline')
  $ExerciseDefinitionCopyWith<$Res>? get exerciseDefinition {
    if (_value.exerciseDefinition == null) {
      return null;
    }

    return $ExerciseDefinitionCopyWith<$Res>(_value.exerciseDefinition!,
        (value) {
      return _then(_value.copyWith(exerciseDefinition: value) as $Val);
    });
  }
}


abstract class _$$ExerciseInstanceImplCopyWith<$Res>
    implements $ExerciseInstanceCopyWith<$Res> {
  factory _$$ExerciseInstanceImplCopyWith(_$ExerciseInstanceImpl value,
          $Res Function(_$ExerciseInstanceImpl) then) =
      __$$ExerciseInstanceImplCopyWithImpl<$Res>;
  @override
  @useResult
  $Res call(
      {int? id,
      @JsonKey(name: 'exercise_list_id') int exerciseListId,
      @JsonKey(name: 'exercise_definition')
      ExerciseDefinition? exerciseDefinition,
      @JsonKey(name: 'workout_id') int? workoutId,
      @JsonKey(name: 'user_max_id') int? userMaxId,
      List<ExerciseSetDto> sets,
      String? notes,
      @JsonKey(name: 'order') int? order,
      @JsonKey(includeFromJson: false, includeToJson: false) int? localId});

  @override
  $ExerciseDefinitionCopyWith<$Res>? get exerciseDefinition;
}


class __$$ExerciseInstanceImplCopyWithImpl<$Res>
    extends _$ExerciseInstanceCopyWithImpl<$Res, _$ExerciseInstanceImpl>
    implements _$$ExerciseInstanceImplCopyWith<$Res> {
  __$$ExerciseInstanceImplCopyWithImpl(_$ExerciseInstanceImpl _value,
      $Res Function(_$ExerciseInstanceImpl) _then)
      : super(_value, _then);



  @pragma('vm:prefer-inline')
  @override
  $Res call({
    Object? id = freezed,
    Object? exerciseListId = null,
    Object? exerciseDefinition = freezed,
    Object? workoutId = freezed,
    Object? userMaxId = freezed,
    Object? sets = null,
    Object? notes = freezed,
    Object? order = freezed,
    Object? localId = freezed,
  }) {
    return _then(_$ExerciseInstanceImpl(
      id: freezed == id
          ? _value.id
          : id // ignore: cast_nullable_to_non_nullable
              as int?,
      exerciseListId: null == exerciseListId
          ? _value.exerciseListId
          : exerciseListId // ignore: cast_nullable_to_non_nullable
              as int,
      exerciseDefinition: freezed == exerciseDefinition
          ? _value.exerciseDefinition
          : exerciseDefinition // ignore: cast_nullable_to_non_nullable
              as ExerciseDefinition?,
      workoutId: freezed == workoutId
          ? _value.workoutId
          : workoutId // ignore: cast_nullable_to_non_nullable
              as int?,
      userMaxId: freezed == userMaxId
          ? _value.userMaxId
          : userMaxId // ignore: cast_nullable_to_non_nullable
              as int?,
      sets: null == sets
          ? _value._sets
          : sets // ignore: cast_nullable_to_non_nullable
              as List<ExerciseSetDto>,
      notes: freezed == notes
          ? _value.notes
          : notes // ignore: cast_nullable_to_non_nullable
              as String?,
      order: freezed == order
          ? _value.order
          : order // ignore: cast_nullable_to_non_nullable
              as int?,
      localId: freezed == localId
          ? _value.localId
          : localId // ignore: cast_nullable_to_non_nullable
              as int?,
    ));
  }
}



@JsonSerializable(explicitToJson: true)
class _$ExerciseInstanceImpl extends _ExerciseInstance
    with DiagnosticableTreeMixin {
  const _$ExerciseInstanceImpl(
      {this.id,
      @JsonKey(name: 'exercise_list_id') required this.exerciseListId,
      @JsonKey(name: 'exercise_definition') this.exerciseDefinition,
      @JsonKey(name: 'workout_id') this.workoutId,
      @JsonKey(name: 'user_max_id') this.userMaxId,
      final List<ExerciseSetDto> sets = const [],
      this.notes,
      @JsonKey(name: 'order') this.order,
      @JsonKey(includeFromJson: false, includeToJson: false) this.localId})
      : _sets = sets,
        super._();

  factory _$ExerciseInstanceImpl.fromJson(Map<String, dynamic> json) =>
      _$$ExerciseInstanceImplFromJson(json);

  @override
  final int? id;
  @override
  @JsonKey(name: 'exercise_list_id')
  final int exerciseListId;
  @override
  @JsonKey(name: 'exercise_definition')
  final ExerciseDefinition? exerciseDefinition;
  @override
  @JsonKey(name: 'workout_id')
  final int? workoutId;
  @override
  @JsonKey(name: 'user_max_id')
  final int? userMaxId;
  final List<ExerciseSetDto> _sets;
  @override
  @JsonKey()
  List<ExerciseSetDto> get sets {
    if (_sets is EqualUnmodifiableListView) return _sets;
    // ignore: implicit_dynamic_type
    return EqualUnmodifiableListView(_sets);
  }

  @override
  final String? notes;
  @override
  @JsonKey(name: 'order')
  final int? order;
  @override
  @JsonKey(includeFromJson: false, includeToJson: false)
  final int? localId;

  @override
  String toString({DiagnosticLevel minLevel = DiagnosticLevel.info}) {
    return 'ExerciseInstance(id: $id, exerciseListId: $exerciseListId, exerciseDefinition: $exerciseDefinition, workoutId: $workoutId, userMaxId: $userMaxId, sets: $sets, notes: $notes, order: $order, localId: $localId)';
  }

  @override
  void debugFillProperties(DiagnosticPropertiesBuilder properties) {
    super.debugFillProperties(properties);
    properties
      ..add(DiagnosticsProperty('type', 'ExerciseInstance'))
      ..add(DiagnosticsProperty('id', id))
      ..add(DiagnosticsProperty('exerciseListId', exerciseListId))
      ..add(DiagnosticsProperty('exerciseDefinition', exerciseDefinition))
      ..add(DiagnosticsProperty('workoutId', workoutId))
      ..add(DiagnosticsProperty('userMaxId', userMaxId))
      ..add(DiagnosticsProperty('sets', sets))
      ..add(DiagnosticsProperty('notes', notes))
      ..add(DiagnosticsProperty('order', order))
      ..add(DiagnosticsProperty('localId', localId));
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) ||
        (other.runtimeType == runtimeType &&
            other is _$ExerciseInstanceImpl &&
            (identical(other.id, id) || other.id == id) &&
            (identical(other.exerciseListId, exerciseListId) ||
                other.exerciseListId == exerciseListId) &&
            (identical(other.exerciseDefinition, exerciseDefinition) ||
                other.exerciseDefinition == exerciseDefinition) &&
            (identical(other.workoutId, workoutId) ||
                other.workoutId == workoutId) &&
            (identical(other.userMaxId, userMaxId) ||
                other.userMaxId == userMaxId) &&
            const DeepCollectionEquality().equals(other._sets, _sets) &&
            (identical(other.notes, notes) || other.notes == notes) &&
            (identical(other.order, order) || other.order == order) &&
            (identical(other.localId, localId) || other.localId == localId));
  }

  @JsonKey(includeFromJson: false, includeToJson: false)
  @override
  int get hashCode => Object.hash(
      runtimeType,
      id,
      exerciseListId,
      exerciseDefinition,
      workoutId,
      userMaxId,
      const DeepCollectionEquality().hash(_sets),
      notes,
      order,
      localId);



  @JsonKey(includeFromJson: false, includeToJson: false)
  @override
  @pragma('vm:prefer-inline')
  _$$ExerciseInstanceImplCopyWith<_$ExerciseInstanceImpl> get copyWith =>
      __$$ExerciseInstanceImplCopyWithImpl<_$ExerciseInstanceImpl>(
          this, _$identity);

  @override
  Map<String, dynamic> toJson() {
    return _$$ExerciseInstanceImplToJson(
      this,
    );
  }
}

abstract class _ExerciseInstance extends ExerciseInstance {
  const factory _ExerciseInstance(
      {final int? id,
      @JsonKey(name: 'exercise_list_id') required final int exerciseListId,
      @JsonKey(name: 'exercise_definition')
      final ExerciseDefinition? exerciseDefinition,
      @JsonKey(name: 'workout_id') final int? workoutId,
      @JsonKey(name: 'user_max_id') final int? userMaxId,
      final List<ExerciseSetDto> sets,
      final String? notes,
      @JsonKey(name: 'order') final int? order,
      @JsonKey(includeFromJson: false, includeToJson: false)
      final int? localId}) = _$ExerciseInstanceImpl;
  const _ExerciseInstance._() : super._();

  factory _ExerciseInstance.fromJson(Map<String, dynamic> json) =
      _$ExerciseInstanceImpl.fromJson;

  @override
  int? get id;
  @override
  @JsonKey(name: 'exercise_list_id')
  int get exerciseListId;
  @override
  @JsonKey(name: 'exercise_definition')
  ExerciseDefinition? get exerciseDefinition;
  @override
  @JsonKey(name: 'workout_id')
  int? get workoutId;
  @override
  @JsonKey(name: 'user_max_id')
  int? get userMaxId;
  @override
  List<ExerciseSetDto> get sets;
  @override
  String? get notes;
  @override
  @JsonKey(name: 'order')
  int? get order;
  @override
  @JsonKey(includeFromJson: false, includeToJson: false)
  int? get localId;



  @override
  @JsonKey(includeFromJson: false, includeToJson: false)
  _$$ExerciseInstanceImplCopyWith<_$ExerciseInstanceImpl> get copyWith =>
      throw _privateConstructorUsedError;
}
