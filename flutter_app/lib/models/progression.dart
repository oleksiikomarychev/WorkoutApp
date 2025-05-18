class Progression {
  final int? id;
  final int userMaxId;
  final int sets;
  final double intensity;
  final double effort;
  final int volume;
  final dynamic reps; 
  final dynamic calculatedWeight; 
  final String? userMaxDisplay;
  Progression({
    this.id,
    required this.userMaxId,
    required this.sets,
    required this.intensity,
    required this.effort,
    required this.volume,
    this.reps,
    this.calculatedWeight,
    this.userMaxDisplay,
  });
  factory Progression.fromJson(Map<String, dynamic> json) {
    return Progression(
      id: json['id'],
      userMaxId: json['user_max_id'],
      sets: json['sets'],
      intensity: json['intensity']?.toDouble(),
      effort: json['effort']?.toDouble(),
      volume: json['volume'],
      reps: json['reps'],
      calculatedWeight: json['calculated_weight'],
      userMaxDisplay: json['user_max_display'],
    );
  }
  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'user_max_id': userMaxId,
      'sets': sets,
      'intensity': intensity,
      'effort': effort,
      'volume': volume,
    };
  }
}
