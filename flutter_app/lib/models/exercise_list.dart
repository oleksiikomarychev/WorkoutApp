class ExerciseList {
  final int? id;
  final String name;
  final String? description;
  final String? muscleGroup;
  final String? equipment;
  final String? videoUrl;
  ExerciseList({
    this.id,
    required this.name,
    this.description,
    this.muscleGroup,
    this.equipment,
    this.videoUrl,
  });
  factory ExerciseList.fromJson(Map<String, dynamic> json) {
    return ExerciseList(
      id: json['id'],
      name: json['name'],
      description: json['description'],
      muscleGroup: json['muscle_group'],
      equipment: json['equipment'],
      videoUrl: json['video_url'],
    );
  }
  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'name': name,
      'description': description,
      'muscle_group': muscleGroup,
      'equipment': equipment,
      'video_url': videoUrl,
    };
  }
}
