import 'exercise_instance.dart';
import 'exercise_definition.dart';

class Exercise {
  final int? id;
  final String name;
  final ExerciseDefinition? exerciseDefinition;
  final List<ExerciseInstance> instances;

  Exercise({
    this.id,
    required this.name,
    this.exerciseDefinition,
    List<ExerciseInstance>? instances,
  }) : instances = instances ?? [];

  factory Exercise.fromJson(Map<String, dynamic> json) {
    return Exercise(
      id: json['id'],
      name: json['name'] ?? '',
      exerciseDefinition: json['exercise_definition'] != null 
          ? ExerciseDefinition.fromJson(json['exercise_definition'] is Map<String, dynamic> 
              ? json['exercise_definition'] 
              : {})
          : null,
      instances: json['instances'] != null
          ? (json['instances'] as List)
              .map((e) => ExerciseInstance.fromJson(e))
              .toList()
          : [],
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'name': name,
      if (exerciseDefinition != null) 'exercise_definition': exerciseDefinition!.toJson(),
      'instances': instances.map((e) => e.toJson()).toList(),
    };
  }

  Exercise copyWith({
    int? id,
    String? name,
    ExerciseDefinition? exerciseDefinition,
    List<ExerciseInstance>? instances,
  }) {
    return Exercise(
      id: id ?? this.id,
      name: name ?? this.name,
      exerciseDefinition: exerciseDefinition ?? this.exerciseDefinition,
      instances: instances ?? this.instances,
    );
  }
}
