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
    @JsonKey(name: 'set_type') String? setType,
    @Default(<ExerciseSetDto>[]) List<ExerciseSetDto> subsets,
    @JsonKey(name: 'volume') @Default(0) int reps,
    @JsonKey(name: 'working_weight') @Default(0.0) double weight,
    double? rpe,
    int? order,
    @JsonKey(name: 'exercise_instance') int? exerciseInstanceId,
    @Default(0) int intensity,
    @Default(0) double effort,

    @JsonKey(includeFromJson: true, includeToJson: false, fromJson: _volumeFromJson) int? volume,

    @JsonKey(includeFromJson: false, includeToJson: false) int? localId,
  }) = _ExerciseSetDto;

  factory ExerciseSetDto.fromJson(Map<String, dynamic> json) =>
      _$ExerciseSetDtoFromJson(json);


  int get computedVolume {
    if (subsets.isNotEmpty) {
      return subsets.fold(0, (sum, s) => sum + s.computedVolume);
    }
    if (volume != null) return volume!;
    return (reps * weight).round();
  }

  // Add getter for backward compatibility  
  double? get rpeValue => rpe ?? effort.toDouble();




  Map<String, dynamic> toFormData() {
    return {
      if (id != null) 'id': id,
      if (setType != null) 'set_type': setType,
      if (subsets.isNotEmpty) 'subsets': subsets.map((s) => s.toFormData()).toList(),
      'reps': reps,
      'weight': weight,
      'rpe': effort, // Backend expects 'rpe' field
      if (order != null) 'order': order,
      if (exerciseInstanceId != null) 'exercise_instance': exerciseInstanceId,
    };
  }
}
