class ProgressionTemplate {
  final int? id;
  final String name;
  final int userMaxId;
  final int sets;
  final int intensity;
  final double effort;
  final int? volume;
  final double? calculatedWeight;
  final String? notes;
  final DateTime? createdAt;
  final DateTime? updatedAt;

  ProgressionTemplate({
    this.id,
    required this.name,
    required this.userMaxId,
    required this.sets,
    required this.intensity,
    required this.effort,
    this.volume,
    this.calculatedWeight,
    this.notes,
    this.createdAt,
    this.updatedAt,
  });

  factory ProgressionTemplate.fromJson(Map<String, dynamic> json) {
    return ProgressionTemplate(
      id: json['id'],
      name: json['name'],
      userMaxId: json['user_max_id'],
      sets: json['sets'] ?? 0,
      intensity: json['intensity'] is int ? json['intensity'] : 70, // Default to 70% intensity
      effort: json['effort'] is num ? (json['effort'] as num).toDouble() : 8.0, // Default to RPE 8
      volume: json['volume'],
      calculatedWeight: json['calculated_weight'] is num ? (json['calculated_weight'] as num).toDouble() : null,
      notes: json['notes'],
      createdAt: json['created_at'] != null ? DateTime.parse(json['created_at']) : null,
      updatedAt: json['updated_at'] != null ? DateTime.parse(json['updated_at']) : null,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'name': name,
      'user_max_id': userMaxId,
      'sets': sets,
      'intensity': intensity,
      'effort': effort,
      if (volume != null) 'volume': volume,
      if (notes != null) 'notes': notes,
    };
  }

  ProgressionTemplate copyWith({
    int? id,
    String? name,
    int? userMaxId,
    int? sets,
    int? intensity,
    double? effort,
    int? volume,
    double? calculatedWeight,
    String? notes,
    DateTime? createdAt,
    DateTime? updatedAt,
  }) {
    return ProgressionTemplate(
      id: id ?? this.id,
      name: name ?? this.name,
      userMaxId: userMaxId ?? this.userMaxId,
      sets: sets ?? this.sets,
      intensity: intensity ?? this.intensity,
      effort: effort ?? this.effort,
      volume: volume ?? this.volume,
      calculatedWeight: calculatedWeight ?? this.calculatedWeight,
      notes: notes ?? this.notes,
      createdAt: createdAt ?? this.createdAt,
      updatedAt: updatedAt ?? this.updatedAt,
    );
  }
}
