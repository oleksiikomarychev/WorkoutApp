class ExerciseList {
  final int? id;
  final String name;
  final String? description;
  final String? muscleGroup;
  final String? equipment;
  final String? videoUrl;
  final DateTime? createdAt;
  final DateTime? updatedAt;

  ExerciseList({
    this.id,
    required this.name,
    this.description,
    this.muscleGroup,
    this.equipment,
    this.videoUrl,
    this.createdAt,
    this.updatedAt,
  });

  factory ExerciseList.fromJson(Map<String, dynamic> json) {
    return ExerciseList(
      id: json['id'],
      name: json['name'] ?? '',
      description: json['description'],
      muscleGroup: json['muscle_group'],
      equipment: json['equipment'],
      videoUrl: json['video_url'],
      createdAt: json['created_at'] != null 
          ? DateTime.parse(json['created_at'])
          : null,
      updatedAt: json['updated_at'] != null
          ? DateTime.parse(json['updated_at'])
          : null,
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

  ExerciseList copyWith({
    int? id,
    String? name,
    String? description,
    String? muscleGroup,
    String? equipment,
    String? videoUrl,
    DateTime? createdAt,
    DateTime? updatedAt,
  }) {
    return ExerciseList(
      id: id ?? this.id,
      name: name ?? this.name,
      description: description ?? this.description,
      muscleGroup: muscleGroup ?? this.muscleGroup,
      equipment: equipment ?? this.equipment,
      videoUrl: videoUrl ?? this.videoUrl,
      createdAt: createdAt ?? this.createdAt,
      updatedAt: updatedAt ?? this.updatedAt,
    );
  }
}
