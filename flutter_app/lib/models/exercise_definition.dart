import 'package:freezed_annotation/freezed_annotation.dart';

part 'exercise_definition.freezed.dart';
part 'exercise_definition.g.dart';

@freezed
class ExerciseDefinition with _$ExerciseDefinition {
  const factory ExerciseDefinition({
    int? id,
    required String name,
    @JsonKey(name: 'muscle_group') String? muscleGroup,
    String? equipment,
    @JsonKey(name: 'target_muscles') List<String>? targetMuscles,
    @JsonKey(name: 'synergist_muscles') List<String>? synergistMuscles,
    @JsonKey(name: 'movement_type') String? movementType,
    @JsonKey(name: 'region') String? region,
  }) = _ExerciseDefinition;

  factory ExerciseDefinition.fromJson(Map<String, dynamic> json) =>
      _$ExerciseDefinitionFromJson(json);
}
