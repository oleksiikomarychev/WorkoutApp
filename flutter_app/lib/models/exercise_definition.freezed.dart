// coverage:ignore-file
// GENERATED CODE - DO NOT MODIFY BY HAND
// ignore_for_file: type=lint
// ignore_for_file: unused_element, deprecated_member_use, deprecated_member_use_from_same_package, use_function_type_syntax_for_parameters, unnecessary_const, avoid_init_to_null, invalid_override_different_default_values_named, prefer_expression_function_bodies, annotate_overrides, invalid_annotation_target, unnecessary_question_mark

part of 'exercise_definition.dart';

// **************************************************************************
// FreezedGenerator
// **************************************************************************

T _$identity<T>(T value) => value;

final _privateConstructorUsedError = UnsupportedError(
    'It seems like you constructed your class using `MyClass._()`. This constructor is only meant to be used by freezed and you are not supposed to need it nor use it.\nPlease check the documentation here for more information: https://github.com/rrousselGit/freezed#adding-getters-and-methods-to-our-models');

ExerciseDefinition _$ExerciseDefinitionFromJson(Map<String, dynamic> json) {
  return _ExerciseDefinition.fromJson(json);
}

/// @nodoc
mixin _$ExerciseDefinition {
  int? get id => throw _privateConstructorUsedError;
  String get name => throw _privateConstructorUsedError;
  @JsonKey(name: 'muscle_group')
  String? get muscleGroup => throw _privateConstructorUsedError;
  String? get equipment => throw _privateConstructorUsedError;
  @JsonKey(name: 'target_muscles')
  List<String>? get targetMuscles => throw _privateConstructorUsedError;
  @JsonKey(name: 'synergist_muscles')
  List<String>? get synergistMuscles => throw _privateConstructorUsedError;
  @JsonKey(name: 'movement_type')
  String? get movementType => throw _privateConstructorUsedError;
  @JsonKey(name: 'region')
  String? get region => throw _privateConstructorUsedError;

  /// Serializes this ExerciseDefinition to a JSON map.
  Map<String, dynamic> toJson() => throw _privateConstructorUsedError;

  /// Create a copy of ExerciseDefinition
  /// with the given fields replaced by the non-null parameter values.
  @JsonKey(includeFromJson: false, includeToJson: false)
  $ExerciseDefinitionCopyWith<ExerciseDefinition> get copyWith =>
      throw _privateConstructorUsedError;
}

/// @nodoc
abstract class $ExerciseDefinitionCopyWith<$Res> {
  factory $ExerciseDefinitionCopyWith(
          ExerciseDefinition value, $Res Function(ExerciseDefinition) then) =
      _$ExerciseDefinitionCopyWithImpl<$Res, ExerciseDefinition>;
  @useResult
  $Res call(
      {int? id,
      String name,
      @JsonKey(name: 'muscle_group') String? muscleGroup,
      String? equipment,
      @JsonKey(name: 'target_muscles') List<String>? targetMuscles,
      @JsonKey(name: 'synergist_muscles') List<String>? synergistMuscles,
      @JsonKey(name: 'movement_type') String? movementType,
      @JsonKey(name: 'region') String? region});
}

/// @nodoc
class _$ExerciseDefinitionCopyWithImpl<$Res, $Val extends ExerciseDefinition>
    implements $ExerciseDefinitionCopyWith<$Res> {
  _$ExerciseDefinitionCopyWithImpl(this._value, this._then);

  // ignore: unused_field
  final $Val _value;
  // ignore: unused_field
  final $Res Function($Val) _then;

  /// Create a copy of ExerciseDefinition
  /// with the given fields replaced by the non-null parameter values.
  @pragma('vm:prefer-inline')
  @override
  $Res call({
    Object? id = freezed,
    Object? name = null,
    Object? muscleGroup = freezed,
    Object? equipment = freezed,
    Object? targetMuscles = freezed,
    Object? synergistMuscles = freezed,
    Object? movementType = freezed,
    Object? region = freezed,
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
      muscleGroup: freezed == muscleGroup
          ? _value.muscleGroup
          : muscleGroup // ignore: cast_nullable_to_non_nullable
              as String?,
      equipment: freezed == equipment
          ? _value.equipment
          : equipment // ignore: cast_nullable_to_non_nullable
              as String?,
      targetMuscles: freezed == targetMuscles
          ? _value.targetMuscles
          : targetMuscles // ignore: cast_nullable_to_non_nullable
              as List<String>?,
      synergistMuscles: freezed == synergistMuscles
          ? _value.synergistMuscles
          : synergistMuscles // ignore: cast_nullable_to_non_nullable
              as List<String>?,
      movementType: freezed == movementType
          ? _value.movementType
          : movementType // ignore: cast_nullable_to_non_nullable
              as String?,
      region: freezed == region
          ? _value.region
          : region // ignore: cast_nullable_to_non_nullable
              as String?,
    ) as $Val);
  }
}

/// @nodoc
abstract class _$$ExerciseDefinitionImplCopyWith<$Res>
    implements $ExerciseDefinitionCopyWith<$Res> {
  factory _$$ExerciseDefinitionImplCopyWith(_$ExerciseDefinitionImpl value,
          $Res Function(_$ExerciseDefinitionImpl) then) =
      __$$ExerciseDefinitionImplCopyWithImpl<$Res>;
  @override
  @useResult
  $Res call(
      {int? id,
      String name,
      @JsonKey(name: 'muscle_group') String? muscleGroup,
      String? equipment,
      @JsonKey(name: 'target_muscles') List<String>? targetMuscles,
      @JsonKey(name: 'synergist_muscles') List<String>? synergistMuscles,
      @JsonKey(name: 'movement_type') String? movementType,
      @JsonKey(name: 'region') String? region});
}

/// @nodoc
class __$$ExerciseDefinitionImplCopyWithImpl<$Res>
    extends _$ExerciseDefinitionCopyWithImpl<$Res, _$ExerciseDefinitionImpl>
    implements _$$ExerciseDefinitionImplCopyWith<$Res> {
  __$$ExerciseDefinitionImplCopyWithImpl(_$ExerciseDefinitionImpl _value,
      $Res Function(_$ExerciseDefinitionImpl) _then)
      : super(_value, _then);

  /// Create a copy of ExerciseDefinition
  /// with the given fields replaced by the non-null parameter values.
  @pragma('vm:prefer-inline')
  @override
  $Res call({
    Object? id = freezed,
    Object? name = null,
    Object? muscleGroup = freezed,
    Object? equipment = freezed,
    Object? targetMuscles = freezed,
    Object? synergistMuscles = freezed,
    Object? movementType = freezed,
    Object? region = freezed,
  }) {
    return _then(_$ExerciseDefinitionImpl(
      id: freezed == id
          ? _value.id
          : id // ignore: cast_nullable_to_non_nullable
              as int?,
      name: null == name
          ? _value.name
          : name // ignore: cast_nullable_to_non_nullable
              as String,
      muscleGroup: freezed == muscleGroup
          ? _value.muscleGroup
          : muscleGroup // ignore: cast_nullable_to_non_nullable
              as String?,
      equipment: freezed == equipment
          ? _value.equipment
          : equipment // ignore: cast_nullable_to_non_nullable
              as String?,
      targetMuscles: freezed == targetMuscles
          ? _value._targetMuscles
          : targetMuscles // ignore: cast_nullable_to_non_nullable
              as List<String>?,
      synergistMuscles: freezed == synergistMuscles
          ? _value._synergistMuscles
          : synergistMuscles // ignore: cast_nullable_to_non_nullable
              as List<String>?,
      movementType: freezed == movementType
          ? _value.movementType
          : movementType // ignore: cast_nullable_to_non_nullable
              as String?,
      region: freezed == region
          ? _value.region
          : region // ignore: cast_nullable_to_non_nullable
              as String?,
    ));
  }
}

/// @nodoc
@JsonSerializable()
class _$ExerciseDefinitionImpl implements _ExerciseDefinition {
  const _$ExerciseDefinitionImpl(
      {this.id,
      required this.name,
      @JsonKey(name: 'muscle_group') this.muscleGroup,
      this.equipment,
      @JsonKey(name: 'target_muscles') final List<String>? targetMuscles,
      @JsonKey(name: 'synergist_muscles') final List<String>? synergistMuscles,
      @JsonKey(name: 'movement_type') this.movementType,
      @JsonKey(name: 'region') this.region})
      : _targetMuscles = targetMuscles,
        _synergistMuscles = synergistMuscles;

  factory _$ExerciseDefinitionImpl.fromJson(Map<String, dynamic> json) =>
      _$$ExerciseDefinitionImplFromJson(json);

  @override
  final int? id;
  @override
  final String name;
  @override
  @JsonKey(name: 'muscle_group')
  final String? muscleGroup;
  @override
  final String? equipment;
  final List<String>? _targetMuscles;
  @override
  @JsonKey(name: 'target_muscles')
  List<String>? get targetMuscles {
    final value = _targetMuscles;
    if (value == null) return null;
    if (_targetMuscles is EqualUnmodifiableListView) return _targetMuscles;
    // ignore: implicit_dynamic_type
    return EqualUnmodifiableListView(value);
  }

  final List<String>? _synergistMuscles;
  @override
  @JsonKey(name: 'synergist_muscles')
  List<String>? get synergistMuscles {
    final value = _synergistMuscles;
    if (value == null) return null;
    if (_synergistMuscles is EqualUnmodifiableListView)
      return _synergistMuscles;
    // ignore: implicit_dynamic_type
    return EqualUnmodifiableListView(value);
  }

  @override
  @JsonKey(name: 'movement_type')
  final String? movementType;
  @override
  @JsonKey(name: 'region')
  final String? region;

  @override
  String toString() {
    return 'ExerciseDefinition(id: $id, name: $name, muscleGroup: $muscleGroup, equipment: $equipment, targetMuscles: $targetMuscles, synergistMuscles: $synergistMuscles, movementType: $movementType, region: $region)';
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) ||
        (other.runtimeType == runtimeType &&
            other is _$ExerciseDefinitionImpl &&
            (identical(other.id, id) || other.id == id) &&
            (identical(other.name, name) || other.name == name) &&
            (identical(other.muscleGroup, muscleGroup) ||
                other.muscleGroup == muscleGroup) &&
            (identical(other.equipment, equipment) ||
                other.equipment == equipment) &&
            const DeepCollectionEquality()
                .equals(other._targetMuscles, _targetMuscles) &&
            const DeepCollectionEquality()
                .equals(other._synergistMuscles, _synergistMuscles) &&
            (identical(other.movementType, movementType) ||
                other.movementType == movementType) &&
            (identical(other.region, region) || other.region == region));
  }

  @JsonKey(includeFromJson: false, includeToJson: false)
  @override
  int get hashCode => Object.hash(
      runtimeType,
      id,
      name,
      muscleGroup,
      equipment,
      const DeepCollectionEquality().hash(_targetMuscles),
      const DeepCollectionEquality().hash(_synergistMuscles),
      movementType,
      region);

  /// Create a copy of ExerciseDefinition
  /// with the given fields replaced by the non-null parameter values.
  @JsonKey(includeFromJson: false, includeToJson: false)
  @override
  @pragma('vm:prefer-inline')
  _$$ExerciseDefinitionImplCopyWith<_$ExerciseDefinitionImpl> get copyWith =>
      __$$ExerciseDefinitionImplCopyWithImpl<_$ExerciseDefinitionImpl>(
          this, _$identity);

  @override
  Map<String, dynamic> toJson() {
    return _$$ExerciseDefinitionImplToJson(
      this,
    );
  }
}

abstract class _ExerciseDefinition implements ExerciseDefinition {
  const factory _ExerciseDefinition(
      {final int? id,
      required final String name,
      @JsonKey(name: 'muscle_group') final String? muscleGroup,
      final String? equipment,
      @JsonKey(name: 'target_muscles') final List<String>? targetMuscles,
      @JsonKey(name: 'synergist_muscles') final List<String>? synergistMuscles,
      @JsonKey(name: 'movement_type') final String? movementType,
      @JsonKey(name: 'region')
      final String? region}) = _$ExerciseDefinitionImpl;

  factory _ExerciseDefinition.fromJson(Map<String, dynamic> json) =
      _$ExerciseDefinitionImpl.fromJson;

  @override
  int? get id;
  @override
  String get name;
  @override
  @JsonKey(name: 'muscle_group')
  String? get muscleGroup;
  @override
  String? get equipment;
  @override
  @JsonKey(name: 'target_muscles')
  List<String>? get targetMuscles;
  @override
  @JsonKey(name: 'synergist_muscles')
  List<String>? get synergistMuscles;
  @override
  @JsonKey(name: 'movement_type')
  String? get movementType;
  @override
  @JsonKey(name: 'region')
  String? get region;

  /// Create a copy of ExerciseDefinition
  /// with the given fields replaced by the non-null parameter values.
  @override
  @JsonKey(includeFromJson: false, includeToJson: false)
  _$$ExerciseDefinitionImplCopyWith<_$ExerciseDefinitionImpl> get copyWith =>
      throw _privateConstructorUsedError;
}
