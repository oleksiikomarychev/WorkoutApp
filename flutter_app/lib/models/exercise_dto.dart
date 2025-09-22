class ExerciseDto {
  final int id;
  final String name;
  final String? description;
  final String? videoUrl;
  final String? imageUrl;

  ExerciseDto({
    required this.id,
    required this.name,
    this.description,
    this.videoUrl,
    this.imageUrl,
  });

  factory ExerciseDto.fromJson(Map<String, dynamic> json) {
    return ExerciseDto(
      id: json['id'] as int? ?? 0,
      name: json['name'] as String? ?? '',
      description: json['description'] as String?,
      videoUrl: json['video_url'] as String?,
      imageUrl: json['image_url'] as String?,
    );
  }

  Map<String, dynamic> toJson() => {
        'id': id,
        'name': name,
        'description': description,
        'video_url': videoUrl,
        'image_url': imageUrl,
      };
}
