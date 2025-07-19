class ExerciseList {
  final int? id;
  final String name;
  final String? muscleGroup;
  final String? equipment;

  ExerciseList({
    this.id,
    required this.name,
    this.muscleGroup,
    this.equipment,
  });

  factory ExerciseList.fromJson(Map<String, dynamic> json) {
    return ExerciseList(
      id: json['id'],
      name: json['name'] ?? '',
      muscleGroup: json['muscle_group'],
      equipment: json['equipment'],
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'name': name,
      'muscle_group': muscleGroup,
      'equipment': equipment,
    };
  }

  ExerciseList copyWith({
    int? id,
    String? name,
    String? muscleGroup,
    String? equipment,
  }) {
    return ExerciseList(
      id: id ?? this.id,
      name: name ?? this.name,
      muscleGroup: muscleGroup ?? this.muscleGroup,
      equipment: equipment ?? this.equipment,
    );
  }
}
