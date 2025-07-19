import 'package:flutter/foundation.dart';
import 'exercise_instance.dart';


class Workout {
  final int? id;
  final String name;
  final int? progressionTemplateId;
  final List<ExerciseInstance> exerciseInstances;

  Workout({
    this.id,
    required this.name,
    this.progressionTemplateId,
    List<ExerciseInstance>? exerciseInstances,
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
            .where((e) => e is Map<String, dynamic>)
            .map<ExerciseInstance>((e) {
              final instanceMap = e as Map<String, dynamic>;
              // Create a new map with corrected types to ensure doubles are used
              final correctedMap = Map<String, dynamic>.from(instanceMap);
              correctedMap['weight'] = (instanceMap['weight'] as num?)?.toInt();
              correctedMap['volume'] = (instanceMap['volume'] as num?)?.toInt();
              correctedMap['intensity'] = (instanceMap['intensity'] as num?)?.toInt();
              correctedMap['effort'] = (instanceMap['effort'] as num?)?.toInt();

              return ExerciseInstance.fromJson(correctedMap);
            })
            .toList();
      }
    } catch (e) {
      debugPrint('Error parsing exercise instances: $e');
      exerciseInstances = [];
    }
    
    return Workout(
      id: json['id'],
      name: json['name']?.toString() ?? '',
      progressionTemplateId: json['progression_template_id'] is int 
          ? json['progression_template_id'] 
          : (json['progression_template_id'] is String 
              ? int.tryParse(json['progression_template_id'])
              : null),
      exerciseInstances: exerciseInstances,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'name': name,

      'progression_template_id': progressionTemplateId,
      'exercise_instances': exerciseInstances.map((e) => e.toJson()).toList(),
    };
  }

  Workout copyWith({
    int? id,
    String? name,
    int? progressionTemplateId,
    List<ExerciseInstance>? exerciseInstances,
  }) {
    return Workout(
      id: id ?? this.id,
      name: name ?? this.name,
      progressionTemplateId: progressionTemplateId ?? this.progressionTemplateId,
      exerciseInstances: exerciseInstances ?? this.exerciseInstances,
    );
  }
  
  // Helper method to get a list of unique exercise definition IDs in this workout
  Set<int> getExerciseIds() {
    return exerciseInstances
        .map((instance) => instance.exerciseListId)
        .toSet();
  }
  
  // Helper method to get instances of a specific exercise
  List<ExerciseInstance> getInstancesForExercise(int exerciseListId) {
    return exerciseInstances
        .where((instance) => instance.exerciseListId == exerciseListId)
        .toList();
  }
}
