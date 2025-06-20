import 'package:flutter/foundation.dart';
import 'exercise_instance.dart';
import 'exercise.dart';

class Workout {
  final int? id;
  final String name;
  final String? description;
  final int? progressionTemplateId;
  final List<ExerciseInstance> exerciseInstances;
  final DateTime? createdAt;
  final DateTime? updatedAt;

  Workout({
    this.id,
    required this.name,
    this.description,
    this.progressionTemplateId,
    List<ExerciseInstance>? exerciseInstances,
    this.createdAt,
    this.updatedAt,
  }) : exerciseInstances = exerciseInstances ?? [];

  factory Workout.fromJson(Map<String, dynamic>? json) {
    if (json == null) {
      return Workout(
        name: '',
        exerciseInstances: [],
      );
    }
    
    // Safely parse exercise instances
    List<ExerciseInstance> exerciseInstances = [];
    try {
      if (json['exercise_instances'] is List) {
        exerciseInstances = (json['exercise_instances'] as List)
            .where((e) => e != null)
            .map<ExerciseInstance>((e) => ExerciseInstance.fromJson(e))
            .toList();
      }
    } catch (e) {
      debugPrint('Error parsing exercise instances: $e');
      exerciseInstances = [];
    }
    
    return Workout(
      id: json['id'],
      name: json['name']?.toString() ?? '',
      description: json['description']?.toString(),
      progressionTemplateId: json['progression_template_id'] is int 
          ? json['progression_template_id'] 
          : (json['progression_template_id'] is String 
              ? int.tryParse(json['progression_template_id'])
              : null),
      exerciseInstances: exerciseInstances,
      createdAt: json['created_at'] != null 
          ? DateTime.tryParse(json['created_at'].toString()) 
          : null,
      updatedAt: json['updated_at'] != null
          ? DateTime.tryParse(json['updated_at'].toString())
          : null,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'name': name,
      'description': description,
      'progression_template_id': progressionTemplateId,
      'exercise_instances': exerciseInstances.map((e) => e.toJson()).toList(),
    };
  }

  Workout copyWith({
    int? id,
    String? name,
    String? description,
    int? progressionTemplateId,
    List<ExerciseInstance>? exerciseInstances,
    DateTime? createdAt,
    DateTime? updatedAt,
  }) {
    return Workout(
      id: id ?? this.id,
      name: name ?? this.name,
      description: description ?? this.description,
      progressionTemplateId: progressionTemplateId ?? this.progressionTemplateId,
      exerciseInstances: exerciseInstances ?? List<ExerciseInstance>.from(this.exerciseInstances),
      createdAt: createdAt ?? this.createdAt,
      updatedAt: updatedAt ?? this.updatedAt,
    );
  }
  
  // Helper method to get a list of unique exercise IDs in this workout
  Set<int> getExerciseIds() {
    return exerciseInstances
        .map((instance) => instance.exerciseId)
        .toSet();
  }
  
  // Helper method to get instances of a specific exercise
  List<ExerciseInstance> getInstancesForExercise(int exerciseId) {
    return exerciseInstances
        .where((instance) => instance.exerciseId == exerciseId)
        .toList();
  }
}
