class UserMax {
  final int? id;
  final int exerciseId;
  final int maxWeight;
  final int repMax;
  final DateTime? createdAt;
  final DateTime? updatedAt;
  final Map<String, dynamic>? exerciseDetails;

  UserMax({
    this.id,
    required this.exerciseId,
    required this.maxWeight,
    required this.repMax,
    this.createdAt,
    this.updatedAt,
    this.exerciseDetails,
  });

  factory UserMax.fromJson(Map<String, dynamic> json) {
    return UserMax(
      id: json['id'],
      exerciseId: json['exercise_id'] ?? 0,
      maxWeight: json['max_weight'] is int ? json['max_weight'] : 0,
      repMax: json['rep_max'] ?? 0,
      createdAt: json['created_at'] != null 
          ? DateTime.parse(json['created_at'])
          : null,
      updatedAt: json['updated_at'] != null
          ? DateTime.parse(json['updated_at'])
          : null,
      exerciseDetails: json['exercise_details'] is Map 
          ? Map<String, dynamic>.from(json['exercise_details'])
          : null,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'exercise_id': exerciseId,
      'max_weight': maxWeight,
      'rep_max': repMax,
      if (exerciseDetails != null) 'exercise_details': exerciseDetails,
    };
  }

  UserMax copyWith({
    int? id,
    int? exerciseId,
    int? maxWeight,
    int? repMax,
    DateTime? createdAt,
    DateTime? updatedAt,
    Map<String, dynamic>? exerciseDetails,
  }) {
    return UserMax(
      id: id ?? this.id,
      exerciseId: exerciseId ?? this.exerciseId,
      maxWeight: maxWeight ?? this.maxWeight,
      repMax: repMax ?? this.repMax,
      createdAt: createdAt ?? this.createdAt,
      updatedAt: updatedAt ?? this.updatedAt,
      exerciseDetails: exerciseDetails ?? this.exerciseDetails,
    );
  }
}
