class Workout {
  final int? id;
  final String name;
  final String? description;
  final int? progressionTemplateId;
  final List<dynamic>? exercises;
  
  Workout({
    this.id,
    required this.name,
    this.description,
    this.progressionTemplateId,
    this.exercises,
  });
  factory Workout.fromJson(Map<String, dynamic> json) {
    return Workout(
      id: json['id'],
      name: json['name'],
      description: json['description'],
      progressionTemplateId: json['progression_template_id'],
      exercises: json['exercises'],
    );
  }
  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'name': name,
      'description': description,
      'progression_template_id': progressionTemplateId,
      'exercises': exercises,
    };
  }
}
