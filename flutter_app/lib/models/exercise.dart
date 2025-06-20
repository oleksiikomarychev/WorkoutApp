import 'exercise_instance.dart';

class Exercise {
  final int? id;
  final String name;
  final String? description;
  final int? exerciseDefinitionId;
  final DateTime? createdAt;
  final DateTime? updatedAt;
  final List<ExerciseInstance> instances;

  Exercise({
    this.id,
    required this.name,
    this.description,
    this.exerciseDefinitionId,
    this.createdAt,
    this.updatedAt,
    List<ExerciseInstance>? instances,
  }) : instances = instances ?? [];

  factory Exercise.fromJson(Map<String, dynamic> json) {
    return Exercise(
      id: json['id'],
      name: json['name'] ?? '',
      description: json['description'],
      exerciseDefinitionId: json['exercise_definition_id'],
      createdAt: json['created_at'] != null 
          ? DateTime.parse(json['created_at'])
          : null,
      updatedAt: json['updated_at'] != null
          ? DateTime.parse(json['updated_at'])
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
      if (description != null) 'description': description,
      if (exerciseDefinitionId != null) 'exercise_definition_id': exerciseDefinitionId,
      'instances': instances.map((e) => e.toJson()).toList(),
    };
  }

  Exercise copyWith({
    int? id,
    String? name,
    String? description,
    int? exerciseDefinitionId,
    List<ExerciseInstance>? instances,
    DateTime? createdAt,
    DateTime? updatedAt,
  }) {
    return Exercise(
      id: id ?? this.id,
      name: name ?? this.name,
      description: description ?? this.description,
      exerciseDefinitionId: exerciseDefinitionId ?? this.exerciseDefinitionId,
      instances: instances ?? this.instances,
      createdAt: createdAt ?? this.createdAt,
      updatedAt: updatedAt ?? this.updatedAt,
    );
  }
}
