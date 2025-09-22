import 'package:equatable/equatable.dart';

class UserMax extends Equatable {
  final int id;
  final String name;
  final int exerciseId;
  final String exerciseName;
  final int maxWeight;
  final int repMax;

  const UserMax({
    required this.id,
    required this.name,
    required this.exerciseId,
    required this.exerciseName,
    required this.maxWeight,
    required this.repMax,
  });

  /// Creates a copy of this user max with the given fields replaced by the new values
  UserMax copyWith({
    int? id,
    String? name,
    int? exerciseId,
    String? exerciseName,
    int? maxWeight,
    int? repMax,
  }) {
    return UserMax(
      id: id ?? this.id,
      name: name ?? this.name,
      exerciseId: exerciseId ?? this.exerciseId,
      exerciseName: exerciseName ?? this.exerciseName,
      maxWeight: maxWeight ?? this.maxWeight,
      repMax: repMax ?? this.repMax,
    );
  }

  /// Creates a UserMax from JSON data
  factory UserMax.fromJson(Map<String, dynamic> json) {
    return UserMax(
      id: (json['id'] as num?)?.toInt() ?? 0,
      name: json['name'] as String? ?? 'Unnamed',
      exerciseId: (json['exercise_id'] as num?)?.toInt() ?? 0,
      exerciseName: json['exercise_name'] as String? ?? 'Unknown',
      maxWeight: (json['max_weight'] as num?)?.toInt() ?? 0,
      repMax: (json['rep_max'] as num?)?.toInt() ?? 0,
    );
  }

  /// Converts this UserMax to a JSON map
  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'name': name,
      'exercise_id': exerciseId,
      'exercise_name': exerciseName,
      'max_weight': maxWeight,
      'rep_max': repMax,
    };
  }

  /// Validates the user max data
  bool validate() {
    return exerciseId > 0 && 
           maxWeight > 0 && 
           repMax > 0 && 
           repMax <= 12; // Assuming 12 is the maximum rep max
  }

  @override
  List<Object?> get props => [
        id,
        name,
        exerciseId,
        exerciseName,
        maxWeight,
        repMax,
      ];

  @override
  bool? get stringify => true;
}
