import 'package:flutter/foundation.dart';
import 'package:workout_app/models/progression_template.dart';
import 'package:workout_app/models/exercise_list.dart';

@immutable
class ExerciseInstance {
  final int? id;
  final int exerciseListId;
  final int workoutId;
  final int? progressionTemplateId;
  final int? volume;
  final int? intensity;
  final int? effort;
  final int? weight;
  final ExerciseList? exerciseDefinition;
  final ProgressionTemplate? progressionTemplate;

  const ExerciseInstance({
    this.id,
    required this.exerciseListId,
    required this.workoutId,
    this.progressionTemplateId,
    this.volume,
    this.intensity,
    this.effort,
    this.weight,
    this.exerciseDefinition,
    this.progressionTemplate,
  });

  ExerciseInstance copyWith({
    int? id,
    int? exerciseListId,
    int? workoutId,
    int? progressionTemplateId,
    int? volume,
    int? intensity,
    int? effort,
    int? weight,
    ExerciseList? exerciseDefinition,
    ProgressionTemplate? progressionTemplate,
  }) {
    return ExerciseInstance(
      id: id ?? this.id,
      exerciseListId: exerciseListId ?? this.exerciseListId,
      workoutId: workoutId ?? this.workoutId,
      progressionTemplateId: progressionTemplateId ?? this.progressionTemplateId,
      volume: volume ?? this.volume,
      intensity: intensity ?? this.intensity,
      effort: effort ?? this.effort,
      weight: weight ?? this.weight,
      exerciseDefinition: exerciseDefinition ?? this.exerciseDefinition,
      progressionTemplate: progressionTemplate ?? this.progressionTemplate,
    );
  }

  factory ExerciseInstance.fromJson(Map<String, dynamic>? json) {
    if (json == null) {
      throw const FormatException('ExerciseInstance JSON cannot be null');
    }

    try {
      final exerciseListId = _parseInt(json['exercise_id']);
      final workoutId = _parseInt(json['workout_id']);

      if (exerciseListId == null || workoutId == null) {
        throw const FormatException('exercise_id and workout_id are required');
      }

      final progressionTemplateId = _parseInt(json['progression_template_id']);
      final volume = (json['volume'] as num?)?.toInt();
      final intensity = (json['intensity'] as num?)?.toInt();
      final effort = (json['effort'] as num?)?.toInt();
      final weight = (json['weight'] as num?)?.toInt();

      final exerciseDefJson = json['exercise_definition'];
      final ExerciseList? exerciseDefinition = exerciseDefJson != null
          ? ExerciseList.fromJson(exerciseDefJson is Map<String, dynamic> ? exerciseDefJson : {})
          : null;

      final progressionJson = json['progression_template'];
      final ProgressionTemplate? progressionTemplate = progressionJson != null
          ? ProgressionTemplate.fromJson(progressionJson is Map<String, dynamic> ? progressionJson : {})
          : null;

      return ExerciseInstance(
        id: _parseInt(json['id']),
        exerciseListId: exerciseListId,
        workoutId: workoutId,
        progressionTemplateId: progressionTemplateId,
        volume: volume,
        intensity: intensity,
        effort: effort,
        weight: weight,
        exerciseDefinition: exerciseDefinition,
        progressionTemplate: progressionTemplate,
      );
    } catch (e, stackTrace) {
      debugPrint('Error parsing ExerciseInstance: $e\n$stackTrace');
      rethrow;
    }
  }

  static int? _parseInt(dynamic value) {
    if (value == null) return null;
    if (value is int) return value;
    if (value is num) return value.toInt();
    if (value is String) return int.tryParse(value);
    return null;
  }

  Map<String, dynamic> toJson() {
    return {
      if (id != null) 'id': id,
      'exercise_id': exerciseListId,
      'workout_id': workoutId,
      if (progressionTemplateId != null) 'progression_template_id': progressionTemplateId,
      if (volume != null) 'volume': volume,
      if (intensity != null) 'intensity': intensity,
      if (effort != null) 'effort': effort,
      if (weight != null) 'weight': weight,
      if (exerciseDefinition != null) 'exercise_definition': exerciseDefinition!.toJson(),
      if (progressionTemplate != null) 'progression_template': progressionTemplate!.toJson(),
    };
  }
}
