class ProgressionTemplate {
  final int id;
  final String name;
  final String? description;
  final int user_max_id;
  final int intensity;
  final int effort;
  final int? volume;

  ProgressionTemplate({
    this.id = 0,
    required this.name,
    required this.user_max_id,
    required this.intensity,
    required this.effort,
    this.volume,
    this.description,
  });

  factory ProgressionTemplate.fromJson(Map<String, dynamic> json) {
    return ProgressionTemplate(
      id: json['id'] ?? 0,
      name: json['name'] ?? '',
      user_max_id: json['user_max_id'],
      intensity: json['intensity'],
      effort: json['effort'],
      volume: json['volume'] != null ? json['volume'] as int : null,
      description: json['description'],
    );
  }

  Map<String, dynamic> toJson() => {
    'id': id,
    'name': name,
    'description': description,
    'user_max_id': user_max_id,
    'intensity': intensity,
    'effort': effort,
    'volume': volume,
  }..removeWhere((key, value) => value == null || (key == 'id' && value == 0));
}

class ProgressionTemplateCreate {
  final String name;
  final int user_max_id;
  final int intensity;
  final int effort;
  final int volume;

  ProgressionTemplateCreate({
    required this.name,
    required this.user_max_id,
    required this.intensity,
    required this.effort,
    required this.volume,
  });

  Map<String, dynamic> toJson() => {
    'name': name,
    'user_max_id': user_max_id,
    'intensity': intensity,
    'effort': effort,
    'volume': volume,
  };
}
