// coverage:ignore-file
// GENERATED CODE - DO NOT MODIFY BY HAND
// ignore_for_file: type=lint
// ignore_for_file: unused_element, deprecated_member_use, deprecated_member_use_from_same_package, use_function_type_syntax_for_parameters, unnecessary_const, avoid_init_to_null, invalid_override_different_default_values_named, prefer_expression_function_bodies, annotate_overrides, invalid_annotation_target, unnecessary_question_mark

part of 'exercise_set_dto.dart';

// **************************************************************************
// FreezedGenerator
// **************************************************************************

T _$identity<T>(T value) => value;

final _privateConstructorUsedError = UnsupportedError(
  'It seems like you constructed your class using `MyClass._()`. This constructor is only meant to be used by freezed and you are not supposed to need it nor use it.\nPlease check the documentation here for more information: https://github.com/rrousselGit/freezed#adding-getters-and-methods-to-our-models',
);

ExerciseSetDto _$ExerciseSetDtoFromJson(Map<String, dynamic> json) {
  return _ExerciseSetDto.fromJson(json);
}

/// @nodoc
mixin _$ExerciseSetDto {
  int? get id => throw _privateConstructorUsedError;
  @JsonKey(name: 'set_type')
  String? get setType => throw _privateConstructorUsedError;
  List<ExerciseSetDto> get subsets => throw _privateConstructorUsedError;
  @JsonKey(name: 'volume')
  int get reps => throw _privateConstructorUsedError;
  @JsonKey(name: 'working_weight')
  double get weight => throw _privateConstructorUsedError;
  double? get rpe => throw _privateConstructorUsedError;
  int? get order => throw _privateConstructorUsedError;
  @JsonKey(name: 'exercise_instance')
  int? get exerciseInstanceId => throw _privateConstructorUsedError;
  int get intensity => throw _privateConstructorUsedError;
  double get effort => throw _privateConstructorUsedError;
  @JsonKey(
    includeFromJson: true,
    includeToJson: false,
    fromJson: _volumeFromJson,
  )
  int? get volume => throw _privateConstructorUsedError;
  @JsonKey(includeFromJson: false, includeToJson: false)
  int? get localId => throw _privateConstructorUsedError;

  /// Serializes this ExerciseSetDto to a JSON map.
  Map<String, dynamic> toJson() => throw _privateConstructorUsedError;

  /// Create a copy of ExerciseSetDto
  /// with the given fields replaced by the non-null parameter values.
  @JsonKey(includeFromJson: false, includeToJson: false)
  $ExerciseSetDtoCopyWith<ExerciseSetDto> get copyWith =>
      throw _privateConstructorUsedError;
}

/// @nodoc
abstract class $ExerciseSetDtoCopyWith<$Res> {
  factory $ExerciseSetDtoCopyWith(
    ExerciseSetDto value,
    $Res Function(ExerciseSetDto) then,
  ) = _$ExerciseSetDtoCopyWithImpl<$Res, ExerciseSetDto>;
  @useResult
  $Res call({
    int? id,
    @JsonKey(name: 'set_type') String? setType,
    List<ExerciseSetDto> subsets,
    @JsonKey(name: 'volume') int reps,
    @JsonKey(name: 'working_weight') double weight,
    double? rpe,
    int? order,
    @JsonKey(name: 'exercise_instance') int? exerciseInstanceId,
    int intensity,
    double effort,
    @JsonKey(
      includeFromJson: true,
      includeToJson: false,
      fromJson: _volumeFromJson,
    )
    int? volume,
    @JsonKey(includeFromJson: false, includeToJson: false) int? localId,
  });
}

/// @nodoc
class _$ExerciseSetDtoCopyWithImpl<$Res, $Val extends ExerciseSetDto>
    implements $ExerciseSetDtoCopyWith<$Res> {
  _$ExerciseSetDtoCopyWithImpl(this._value, this._then);

  // ignore: unused_field
  final $Val _value;
  // ignore: unused_field
  final $Res Function($Val) _then;

  /// Create a copy of ExerciseSetDto
  /// with the given fields replaced by the non-null parameter values.
  @pragma('vm:prefer-inline')
  @override
  $Res call({
    Object? id = freezed,
    Object? setType = freezed,
    Object? subsets = null,
    Object? reps = null,
    Object? weight = null,
    Object? rpe = freezed,
    Object? order = freezed,
    Object? exerciseInstanceId = freezed,
    Object? intensity = null,
    Object? effort = null,
    Object? volume = freezed,
    Object? localId = freezed,
  }) {
    return _then(
      _value.copyWith(
            id: freezed == id
                ? _value.id
                : id // ignore: cast_nullable_to_non_nullable
                      as int?,
            setType: freezed == setType
                ? _value.setType
                : setType // ignore: cast_nullable_to_non_nullable
                      as String?,
            subsets: null == subsets
                ? _value.subsets
                : subsets // ignore: cast_nullable_to_non_nullable
                      as List<ExerciseSetDto>,
            reps: null == reps
                ? _value.reps
                : reps // ignore: cast_nullable_to_non_nullable
                      as int,
            weight: null == weight
                ? _value.weight
                : weight // ignore: cast_nullable_to_non_nullable
                      as double,
            rpe: freezed == rpe
                ? _value.rpe
                : rpe // ignore: cast_nullable_to_non_nullable
                      as double?,
            order: freezed == order
                ? _value.order
                : order // ignore: cast_nullable_to_non_nullable
                      as int?,
            exerciseInstanceId: freezed == exerciseInstanceId
                ? _value.exerciseInstanceId
                : exerciseInstanceId // ignore: cast_nullable_to_non_nullable
                      as int?,
            intensity: null == intensity
                ? _value.intensity
                : intensity // ignore: cast_nullable_to_non_nullable
                      as int,
            effort: null == effort
                ? _value.effort
                : effort // ignore: cast_nullable_to_non_nullable
                      as double,
            volume: freezed == volume
                ? _value.volume
                : volume // ignore: cast_nullable_to_non_nullable
                      as int?,
            localId: freezed == localId
                ? _value.localId
                : localId // ignore: cast_nullable_to_non_nullable
                      as int?,
          )
          as $Val,
    );
  }
}

/// @nodoc
abstract class _$$ExerciseSetDtoImplCopyWith<$Res>
    implements $ExerciseSetDtoCopyWith<$Res> {
  factory _$$ExerciseSetDtoImplCopyWith(
    _$ExerciseSetDtoImpl value,
    $Res Function(_$ExerciseSetDtoImpl) then,
  ) = __$$ExerciseSetDtoImplCopyWithImpl<$Res>;
  @override
  @useResult
  $Res call({
    int? id,
    @JsonKey(name: 'set_type') String? setType,
    List<ExerciseSetDto> subsets,
    @JsonKey(name: 'volume') int reps,
    @JsonKey(name: 'working_weight') double weight,
    double? rpe,
    int? order,
    @JsonKey(name: 'exercise_instance') int? exerciseInstanceId,
    int intensity,
    double effort,
    @JsonKey(
      includeFromJson: true,
      includeToJson: false,
      fromJson: _volumeFromJson,
    )
    int? volume,
    @JsonKey(includeFromJson: false, includeToJson: false) int? localId,
  });
}

/// @nodoc
class __$$ExerciseSetDtoImplCopyWithImpl<$Res>
    extends _$ExerciseSetDtoCopyWithImpl<$Res, _$ExerciseSetDtoImpl>
    implements _$$ExerciseSetDtoImplCopyWith<$Res> {
  __$$ExerciseSetDtoImplCopyWithImpl(
    _$ExerciseSetDtoImpl _value,
    $Res Function(_$ExerciseSetDtoImpl) _then,
  ) : super(_value, _then);

  /// Create a copy of ExerciseSetDto
  /// with the given fields replaced by the non-null parameter values.
  @pragma('vm:prefer-inline')
  @override
  $Res call({
    Object? id = freezed,
    Object? setType = freezed,
    Object? subsets = null,
    Object? reps = null,
    Object? weight = null,
    Object? rpe = freezed,
    Object? order = freezed,
    Object? exerciseInstanceId = freezed,
    Object? intensity = null,
    Object? effort = null,
    Object? volume = freezed,
    Object? localId = freezed,
  }) {
    return _then(
      _$ExerciseSetDtoImpl(
        id: freezed == id
            ? _value.id
            : id // ignore: cast_nullable_to_non_nullable
                  as int?,
        setType: freezed == setType
            ? _value.setType
            : setType // ignore: cast_nullable_to_non_nullable
                  as String?,
        subsets: null == subsets
            ? _value._subsets
            : subsets // ignore: cast_nullable_to_non_nullable
                  as List<ExerciseSetDto>,
        reps: null == reps
            ? _value.reps
            : reps // ignore: cast_nullable_to_non_nullable
                  as int,
        weight: null == weight
            ? _value.weight
            : weight // ignore: cast_nullable_to_non_nullable
                  as double,
        rpe: freezed == rpe
            ? _value.rpe
            : rpe // ignore: cast_nullable_to_non_nullable
                  as double?,
        order: freezed == order
            ? _value.order
            : order // ignore: cast_nullable_to_non_nullable
                  as int?,
        exerciseInstanceId: freezed == exerciseInstanceId
            ? _value.exerciseInstanceId
            : exerciseInstanceId // ignore: cast_nullable_to_non_nullable
                  as int?,
        intensity: null == intensity
            ? _value.intensity
            : intensity // ignore: cast_nullable_to_non_nullable
                  as int,
        effort: null == effort
            ? _value.effort
            : effort // ignore: cast_nullable_to_non_nullable
                  as double,
        volume: freezed == volume
            ? _value.volume
            : volume // ignore: cast_nullable_to_non_nullable
                  as int?,
        localId: freezed == localId
            ? _value.localId
            : localId // ignore: cast_nullable_to_non_nullable
                  as int?,
      ),
    );
  }
}

/// @nodoc

@JsonSerializable(explicitToJson: true)
class _$ExerciseSetDtoImpl extends _ExerciseSetDto
    with DiagnosticableTreeMixin {
  const _$ExerciseSetDtoImpl({
    this.id,
    @JsonKey(name: 'set_type') this.setType,
    final List<ExerciseSetDto> subsets = const <ExerciseSetDto>[],
    @JsonKey(name: 'volume') this.reps = 0,
    @JsonKey(name: 'working_weight') this.weight = 0.0,
    this.rpe,
    this.order,
    @JsonKey(name: 'exercise_instance') this.exerciseInstanceId,
    this.intensity = 0,
    this.effort = 0,
    @JsonKey(
      includeFromJson: true,
      includeToJson: false,
      fromJson: _volumeFromJson,
    )
    this.volume,
    @JsonKey(includeFromJson: false, includeToJson: false) this.localId,
  }) : _subsets = subsets,
       super._();

  factory _$ExerciseSetDtoImpl.fromJson(Map<String, dynamic> json) =>
      _$$ExerciseSetDtoImplFromJson(json);

  @override
  final int? id;
  @override
  @JsonKey(name: 'set_type')
  final String? setType;
  final List<ExerciseSetDto> _subsets;
  @override
  @JsonKey()
  List<ExerciseSetDto> get subsets {
    if (_subsets is EqualUnmodifiableListView) return _subsets;
    // ignore: implicit_dynamic_type
    return EqualUnmodifiableListView(_subsets);
  }

  @override
  @JsonKey(name: 'volume')
  final int reps;
  @override
  @JsonKey(name: 'working_weight')
  final double weight;
  @override
  final double? rpe;
  @override
  final int? order;
  @override
  @JsonKey(name: 'exercise_instance')
  final int? exerciseInstanceId;
  @override
  @JsonKey()
  final int intensity;
  @override
  @JsonKey()
  final double effort;
  @override
  @JsonKey(
    includeFromJson: true,
    includeToJson: false,
    fromJson: _volumeFromJson,
  )
  final int? volume;
  @override
  @JsonKey(includeFromJson: false, includeToJson: false)
  final int? localId;

  @override
  String toString({DiagnosticLevel minLevel = DiagnosticLevel.info}) {
    return 'ExerciseSetDto(id: $id, setType: $setType, subsets: $subsets, reps: $reps, weight: $weight, rpe: $rpe, order: $order, exerciseInstanceId: $exerciseInstanceId, intensity: $intensity, effort: $effort, volume: $volume, localId: $localId)';
  }

  @override
  void debugFillProperties(DiagnosticPropertiesBuilder properties) {
    super.debugFillProperties(properties);
    properties
      ..add(DiagnosticsProperty('type', 'ExerciseSetDto'))
      ..add(DiagnosticsProperty('id', id))
      ..add(DiagnosticsProperty('setType', setType))
      ..add(DiagnosticsProperty('subsets', subsets))
      ..add(DiagnosticsProperty('reps', reps))
      ..add(DiagnosticsProperty('weight', weight))
      ..add(DiagnosticsProperty('rpe', rpe))
      ..add(DiagnosticsProperty('order', order))
      ..add(DiagnosticsProperty('exerciseInstanceId', exerciseInstanceId))
      ..add(DiagnosticsProperty('intensity', intensity))
      ..add(DiagnosticsProperty('effort', effort))
      ..add(DiagnosticsProperty('volume', volume))
      ..add(DiagnosticsProperty('localId', localId));
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) ||
        (other.runtimeType == runtimeType &&
            other is _$ExerciseSetDtoImpl &&
            (identical(other.id, id) || other.id == id) &&
            (identical(other.setType, setType) || other.setType == setType) &&
            const DeepCollectionEquality().equals(other._subsets, _subsets) &&
            (identical(other.reps, reps) || other.reps == reps) &&
            (identical(other.weight, weight) || other.weight == weight) &&
            (identical(other.rpe, rpe) || other.rpe == rpe) &&
            (identical(other.order, order) || other.order == order) &&
            (identical(other.exerciseInstanceId, exerciseInstanceId) ||
                other.exerciseInstanceId == exerciseInstanceId) &&
            (identical(other.intensity, intensity) ||
                other.intensity == intensity) &&
            (identical(other.effort, effort) || other.effort == effort) &&
            (identical(other.volume, volume) || other.volume == volume) &&
            (identical(other.localId, localId) || other.localId == localId));
  }

  @JsonKey(includeFromJson: false, includeToJson: false)
  @override
  int get hashCode => Object.hash(
    runtimeType,
    id,
    setType,
    const DeepCollectionEquality().hash(_subsets),
    reps,
    weight,
    rpe,
    order,
    exerciseInstanceId,
    intensity,
    effort,
    volume,
    localId,
  );

  /// Create a copy of ExerciseSetDto
  /// with the given fields replaced by the non-null parameter values.
  @JsonKey(includeFromJson: false, includeToJson: false)
  @override
  @pragma('vm:prefer-inline')
  _$$ExerciseSetDtoImplCopyWith<_$ExerciseSetDtoImpl> get copyWith =>
      __$$ExerciseSetDtoImplCopyWithImpl<_$ExerciseSetDtoImpl>(
        this,
        _$identity,
      );

  @override
  Map<String, dynamic> toJson() {
    return _$$ExerciseSetDtoImplToJson(this);
  }
}

abstract class _ExerciseSetDto extends ExerciseSetDto {
  const factory _ExerciseSetDto({
    final int? id,
    @JsonKey(name: 'set_type') final String? setType,
    final List<ExerciseSetDto> subsets,
    @JsonKey(name: 'volume') final int reps,
    @JsonKey(name: 'working_weight') final double weight,
    final double? rpe,
    final int? order,
    @JsonKey(name: 'exercise_instance') final int? exerciseInstanceId,
    final int intensity,
    final double effort,
    @JsonKey(
      includeFromJson: true,
      includeToJson: false,
      fromJson: _volumeFromJson,
    )
    final int? volume,
    @JsonKey(includeFromJson: false, includeToJson: false) final int? localId,
  }) = _$ExerciseSetDtoImpl;
  const _ExerciseSetDto._() : super._();

  factory _ExerciseSetDto.fromJson(Map<String, dynamic> json) =
      _$ExerciseSetDtoImpl.fromJson;

  @override
  int? get id;
  @override
  @JsonKey(name: 'set_type')
  String? get setType;
  @override
  List<ExerciseSetDto> get subsets;
  @override
  @JsonKey(name: 'volume')
  int get reps;
  @override
  @JsonKey(name: 'working_weight')
  double get weight;
  @override
  double? get rpe;
  @override
  int? get order;
  @override
  @JsonKey(name: 'exercise_instance')
  int? get exerciseInstanceId;
  @override
  int get intensity;
  @override
  double get effort;
  @override
  @JsonKey(
    includeFromJson: true,
    includeToJson: false,
    fromJson: _volumeFromJson,
  )
  int? get volume;
  @override
  @JsonKey(includeFromJson: false, includeToJson: false)
  int? get localId;

  /// Create a copy of ExerciseSetDto
  /// with the given fields replaced by the non-null parameter values.
  @override
  @JsonKey(includeFromJson: false, includeToJson: false)
  _$$ExerciseSetDtoImplCopyWith<_$ExerciseSetDtoImpl> get copyWith =>
      throw _privateConstructorUsedError;
}
