import 'package:freezed_annotation/freezed_annotation.dart';
import 'package:flutter/foundation.dart';

part 'exercise_set_dto.freezed.dart';
part 'exercise_set_dto.g.dart';

// Helper function to handle null volume from JSON
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
    // Accept legacy 'volume' from UI but do not serialize it to API
    @JsonKey(includeFromJson: true, includeToJson: false, fromJson: _volumeFromJson) int? volume,
    // Local-only identifier used by UI
    @JsonKey(includeFromJson: false, includeToJson: false) int? localId,
  }) = _ExerciseSetDto;

  factory ExerciseSetDto.fromJson(Map<String, dynamic> json) => 
      _$ExerciseSetDtoFromJson(json);
      
  // Get the computed volume (either the provided volume or calculated from reps * weight)
  int get computedVolume {
    if (volume != null) return volume!;
    return (reps * weight).round();
  }

  // Backward compatibility and helpers
  
  // Convert to form data for API submission
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
