class Exercise {
  final int? id;
  final String name;
  final int sets;
  final int reps;
  final double? weight;
  final int workoutId;
  Exercise({
    this.id,
    required this.name,
    required this.sets,
    required this.reps,
    this.weight,
    required this.workoutId,
  });
  factory Exercise.fromJson(Map<String, dynamic> json) {
    return Exercise(
      id: json['id'],
      name: json['name'],
      sets: json['sets'],
      reps: json['reps'],
      weight: json['weight']?.toDouble(),
      workoutId: json['workout_id'],
    );
  }
  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'name': name,
      'sets': sets,
      'reps': reps,
      'weight': weight,
      'workout_id': workoutId,
    };
  }
}
