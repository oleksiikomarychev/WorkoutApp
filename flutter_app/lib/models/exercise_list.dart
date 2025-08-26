// This file has been moved to exercise_definition.dart
// Please update your imports to use:
// import 'package:workout_app/models/exercise_definition.dart';
// The ExerciseList class has been renamed to ExerciseDefinition.

class ExerciseDefinition {
  final int? id;
  final String name;
  final String? muscleGroup;
  final String? equipment;

  ExerciseDefinition({
    this.id,
    required this.name,
    this.muscleGroup,
    this.equipment,
  });

  factory ExerciseDefinition.fromJson(Map<String, dynamic> json) {
    return ExerciseDefinition(
      id: json['id'],
      name: json['name'] ?? json['Name'] ?? '',
      muscleGroup: json['muscleGroup'] ?? json['muscle_group'],
      equipment: json['equipment'] ?? json['Equipment'],
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'name': name,
      'muscleGroup': muscleGroup,
      'equipment': equipment,
    };
  }

  ExerciseDefinition copyWith({
    int? id,
    String? name,
    String? muscleGroup,
    String? equipment,
  }) {
    return ExerciseDefinition(
      id: id ?? this.id,
      name: name ?? this.name,
      muscleGroup: muscleGroup ?? this.muscleGroup,
      equipment: equipment ?? this.equipment,
    );
  }
}
