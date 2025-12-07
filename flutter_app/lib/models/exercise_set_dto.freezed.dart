// coverage:ignore-file




part of 'exercise_set_dto.dart';





T _$identity<T>(T value) => value;

final _privateConstructorUsedError = UnsupportedError(
    'It seems like you constructed your class using `MyClass._()`. This constructor is only meant to be used by freezed and you are not supposed to need it nor use it.\nPlease check the documentation here for more information: https://github.com/rrousselGit/freezed#adding-getters-and-methods-to-our-models');

ExerciseSetDto _$ExerciseSetDtoFromJson(Map<String, dynamic> json) {
  return _ExerciseSetDto.fromJson(json);
}


mixin _$ExerciseSetDto {
  int? get id => throw _privateConstructorUsedError;
  int get reps => throw _privateConstructorUsedError;
  double get weight => throw _privateConstructorUsedError;
  double? get rpe => throw _privateConstructorUsedError;
  int? get order => throw _privateConstructorUsedError;
  @JsonKey(name: 'exercise_instance')
  int? get exerciseInstanceId =>
      throw _privateConstructorUsedError;
  @JsonKey(
      includeFromJson: true, includeToJson: false, fromJson: _volumeFromJson)
  int? get volume =>
      throw _privateConstructorUsedError;
  @JsonKey(includeFromJson: false, includeToJson: false)
  int? get localId => throw _privateConstructorUsedError;


  Map<String, dynamic> toJson() => throw _privateConstructorUsedError;



  @JsonKey(includeFromJson: false, includeToJson: false)
  $ExerciseSetDtoCopyWith<ExerciseSetDto> get copyWith =>
      throw _privateConstructorUsedError;
}


abstract class $ExerciseSetDtoCopyWith<$Res> {
  factory $ExerciseSetDtoCopyWith(
          ExerciseSetDto value, $Res Function(ExerciseSetDto) then) =
      _$ExerciseSetDtoCopyWithImpl<$Res, ExerciseSetDto>;
  @useResult
  $Res call(
      {int? id,
      int reps,
      double weight,
      double? rpe,
      int? order,
      @JsonKey(name: 'exercise_instance') int? exerciseInstanceId,
      @JsonKey(
          includeFromJson: true,
          includeToJson: false,
          fromJson: _volumeFromJson)
      int? volume,
      @JsonKey(includeFromJson: false, includeToJson: false) int? localId});
}


class _$ExerciseSetDtoCopyWithImpl<$Res, $Val extends ExerciseSetDto>
    implements $ExerciseSetDtoCopyWith<$Res> {
  _$ExerciseSetDtoCopyWithImpl(this._value, this._then);

  // ignore: unused_field
  final $Val _value;
  // ignore: unused_field
  final $Res Function($Val) _then;



  @pragma('vm:prefer-inline')
  @override
  $Res call({
    Object? id = freezed,
    Object? reps = null,
    Object? weight = null,
    Object? rpe = freezed,
    Object? order = freezed,
    Object? exerciseInstanceId = freezed,
    Object? volume = freezed,
    Object? localId = freezed,
  }) {
    return _then(_value.copyWith(
      id: freezed == id
          ? _value.id
          : id // ignore: cast_nullable_to_non_nullable
              as int?,
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
      volume: freezed == volume
          ? _value.volume
          : volume // ignore: cast_nullable_to_non_nullable
              as int?,
      localId: freezed == localId
          ? _value.localId
          : localId // ignore: cast_nullable_to_non_nullable
              as int?,
    ) as $Val);
  }
}


abstract class _$$ExerciseSetDtoImplCopyWith<$Res>
    implements $ExerciseSetDtoCopyWith<$Res> {
  factory _$$ExerciseSetDtoImplCopyWith(_$ExerciseSetDtoImpl value,
          $Res Function(_$ExerciseSetDtoImpl) then) =
      __$$ExerciseSetDtoImplCopyWithImpl<$Res>;
  @override
  @useResult
  $Res call(
      {int? id,
      int reps,
      double weight,
      double? rpe,
      int? order,
      @JsonKey(name: 'exercise_instance') int? exerciseInstanceId,
      @JsonKey(
          includeFromJson: true,
          includeToJson: false,
          fromJson: _volumeFromJson)
      int? volume,
      @JsonKey(includeFromJson: false, includeToJson: false) int? localId});
}


class __$$ExerciseSetDtoImplCopyWithImpl<$Res>
    extends _$ExerciseSetDtoCopyWithImpl<$Res, _$ExerciseSetDtoImpl>
    implements _$$ExerciseSetDtoImplCopyWith<$Res> {
  __$$ExerciseSetDtoImplCopyWithImpl(
      _$ExerciseSetDtoImpl _value, $Res Function(_$ExerciseSetDtoImpl) _then)
      : super(_value, _then);



  @pragma('vm:prefer-inline')
  @override
  $Res call({
    Object? id = freezed,
    Object? reps = null,
    Object? weight = null,
    Object? rpe = freezed,
    Object? order = freezed,
    Object? exerciseInstanceId = freezed,
    Object? volume = freezed,
    Object? localId = freezed,
  }) {
    return _then(_$ExerciseSetDtoImpl(
      id: freezed == id
          ? _value.id
          : id // ignore: cast_nullable_to_non_nullable
              as int?,
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
      volume: freezed == volume
          ? _value.volume
          : volume // ignore: cast_nullable_to_non_nullable
              as int?,
      localId: freezed == localId
          ? _value.localId
          : localId // ignore: cast_nullable_to_non_nullable
              as int?,
    ));
  }
}



@JsonSerializable(explicitToJson: true)
class _$ExerciseSetDtoImpl extends _ExerciseSetDto
    with DiagnosticableTreeMixin {
  const _$ExerciseSetDtoImpl(
      {this.id,
      this.reps = 0,
      this.weight = 0.0,
      this.rpe,
      this.order,
      @JsonKey(name: 'exercise_instance') this.exerciseInstanceId,
      @JsonKey(
          includeFromJson: true,
          includeToJson: false,
          fromJson: _volumeFromJson)
      this.volume,
      @JsonKey(includeFromJson: false, includeToJson: false) this.localId})
      : super._();

  factory _$ExerciseSetDtoImpl.fromJson(Map<String, dynamic> json) =>
      _$$ExerciseSetDtoImplFromJson(json);

  @override
  final int? id;
  @override
  @JsonKey()
  final int reps;
  @override
  @JsonKey()
  final double weight;
  @override
  final double? rpe;
  @override
  final int? order;
  @override
  @JsonKey(name: 'exercise_instance')
  final int? exerciseInstanceId;

  @override
  @JsonKey(
      includeFromJson: true, includeToJson: false, fromJson: _volumeFromJson)
  final int? volume;

  @override
  @JsonKey(includeFromJson: false, includeToJson: false)
  final int? localId;

  @override
  String toString({DiagnosticLevel minLevel = DiagnosticLevel.info}) {
    return 'ExerciseSetDto(id: $id, reps: $reps, weight: $weight, rpe: $rpe, order: $order, exerciseInstanceId: $exerciseInstanceId, volume: $volume, localId: $localId)';
  }

  @override
  void debugFillProperties(DiagnosticPropertiesBuilder properties) {
    super.debugFillProperties(properties);
    properties
      ..add(DiagnosticsProperty('type', 'ExerciseSetDto'))
      ..add(DiagnosticsProperty('id', id))
      ..add(DiagnosticsProperty('reps', reps))
      ..add(DiagnosticsProperty('weight', weight))
      ..add(DiagnosticsProperty('rpe', rpe))
      ..add(DiagnosticsProperty('order', order))
      ..add(DiagnosticsProperty('exerciseInstanceId', exerciseInstanceId))
      ..add(DiagnosticsProperty('volume', volume))
      ..add(DiagnosticsProperty('localId', localId));
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) ||
        (other.runtimeType == runtimeType &&
            other is _$ExerciseSetDtoImpl &&
            (identical(other.id, id) || other.id == id) &&
            (identical(other.reps, reps) || other.reps == reps) &&
            (identical(other.weight, weight) || other.weight == weight) &&
            (identical(other.rpe, rpe) || other.rpe == rpe) &&
            (identical(other.order, order) || other.order == order) &&
            (identical(other.exerciseInstanceId, exerciseInstanceId) ||
                other.exerciseInstanceId == exerciseInstanceId) &&
            (identical(other.volume, volume) || other.volume == volume) &&
            (identical(other.localId, localId) || other.localId == localId));
  }

  @JsonKey(includeFromJson: false, includeToJson: false)
  @override
  int get hashCode => Object.hash(runtimeType, id, reps, weight, rpe, order,
      exerciseInstanceId, volume, localId);



  @JsonKey(includeFromJson: false, includeToJson: false)
  @override
  @pragma('vm:prefer-inline')
  _$$ExerciseSetDtoImplCopyWith<_$ExerciseSetDtoImpl> get copyWith =>
      __$$ExerciseSetDtoImplCopyWithImpl<_$ExerciseSetDtoImpl>(
          this, _$identity);

  @override
  Map<String, dynamic> toJson() {
    return _$$ExerciseSetDtoImplToJson(
      this,
    );
  }
}

abstract class _ExerciseSetDto extends ExerciseSetDto {
  const factory _ExerciseSetDto(
      {final int? id,
      final int reps,
      final double weight,
      final double? rpe,
      final int? order,
      @JsonKey(name: 'exercise_instance') final int? exerciseInstanceId,
      @JsonKey(
          includeFromJson: true,
          includeToJson: false,
          fromJson: _volumeFromJson)
      final int? volume,
      @JsonKey(includeFromJson: false, includeToJson: false)
      final int? localId}) = _$ExerciseSetDtoImpl;
  const _ExerciseSetDto._() : super._();

  factory _ExerciseSetDto.fromJson(Map<String, dynamic> json) =
      _$ExerciseSetDtoImpl.fromJson;

  @override
  int? get id;
  @override
  int get reps;
  @override
  double get weight;
  @override
  double? get rpe;
  @override
  int? get order;
  @override
  @JsonKey(name: 'exercise_instance')
  int?
      get exerciseInstanceId;
  @override
  @JsonKey(
      includeFromJson: true, includeToJson: false, fromJson: _volumeFromJson)
  int? get volume;
  @override
  @JsonKey(includeFromJson: false, includeToJson: false)
  int? get localId;



  @override
  @JsonKey(includeFromJson: false, includeToJson: false)
  _$$ExerciseSetDtoImplCopyWith<_$ExerciseSetDtoImpl> get copyWith =>
      throw _privateConstructorUsedError;
}
