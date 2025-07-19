import 'exercise_instance.dart';

class Exercise {
  final int? id;
  final String name;
  final int? exerciseDefinitionId;
  final List<ExerciseInstance> instances;

  Exercise({
    this.id,
    required this.name,
    this.exerciseDefinitionId,
    List<ExerciseInstance>? instances,
  }) : instances = instances ?? [];

  factory Exercise.fromJson(Map<String, dynamic> json) {
    return Exercise(
      id: json['id'],
      name: json['name'] ?? '',
      exerciseDefinitionId: json['exercise_definition_id'],
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
      if (exerciseDefinitionId != null) 'exercise_definition_id': exerciseDefinitionId,
      'instances': instances.map((e) => e.toJson()).toList(),
    };
  }

  Exercise copyWith({
    int? id,
    String? name,
    int? exerciseDefinitionId,
    List<ExerciseInstance>? instances,
  }) {
    return Exercise(
      id: id ?? this.id,
      name: name ?? this.name,
      exerciseDefinitionId: exerciseDefinitionId ?? this.exerciseDefinitionId,
      instances: instances ?? this.instances,
    );
  }
}
