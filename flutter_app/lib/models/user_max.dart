class UserMax {
  final int? id;
  final int exerciseId;
  final double maxWeight;
  final int repMax;
  UserMax({
    this.id,
    required this.exerciseId,
    required this.maxWeight,
    required this.repMax,
  });
  factory UserMax.fromJson(Map<String, dynamic> json) {
    return UserMax(
      id: json['id'],
      exerciseId: json['exercise_id'],
      maxWeight: json['max_weight']?.toDouble(),
      repMax: json['rep_max'],
    );
  }
  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'exercise_id': exerciseId,
      'max_weight': maxWeight,
      'rep_max': repMax,
    };
  }
}
