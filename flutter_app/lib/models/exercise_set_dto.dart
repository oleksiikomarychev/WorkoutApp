import 'package:freezed_annotation/freezed_annotation.dart';
import 'package:flutter/foundation.dart';

part 'exercise_set_dto.freezed.dart';
part 'exercise_set_dto.g.dart';


int? _volumeFromJson(dynamic json) {
  if (json == null) return null;
  if (json is num) return json.toInt();
  if (json is String) return int.tryParse(json);
  return null;
}

@freezed
class ExerciseSetDto with _$ExerciseSetDto {
  const ExerciseSetDto._();

  @JsonSerializable(explicitToJson: true)
  const factory ExerciseSetDto({
    int? id,
    @Default(0) int reps,
    @Default(0.0) double weight,
    double? rpe,
    int? order,
    @JsonKey(name: 'exercise_instance') int? exerciseInstanceId,

    @JsonKey(includeFromJson: true, includeToJson: false, fromJson: _volumeFromJson) int? volume,

    @JsonKey(includeFromJson: false, includeToJson: false) int? localId,
  }) = _ExerciseSetDto;

  factory ExerciseSetDto.fromJson(Map<String, dynamic> json) =>
      _$ExerciseSetDtoFromJson(json);


  int get computedVolume {
    if (volume != null) return volume!;
    return (reps * weight).round();
  }




  Map<String, dynamic> toFormData() {
    return {
      if (id != null) 'id': id,
      'reps': reps,
      'weight': weight,
      if (rpe != null) 'rpe': rpe,
      if (order != null) 'order': order,
      if (exerciseInstanceId != null) 'exercise_instance': exerciseInstanceId,
    };
  }
}
