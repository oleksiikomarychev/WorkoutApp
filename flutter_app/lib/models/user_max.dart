import 'package:equatable/equatable.dart';
import 'package:meta/meta.dart';

class UserMax extends Equatable {
  final int? id;
  final int exerciseId;
  final int maxWeight;
  final int repMax;

  const UserMax({
    this.id,
    required this.exerciseId,
    required this.maxWeight,
    required this.repMax,
  });

  /// Creates a copy of this user max with the given fields replaced by the new values
  UserMax copyWith({
    int? id,
    int? exerciseId,
    int? maxWeight,
    int? repMax,
  }) {
    return UserMax(
      id: id ?? this.id,
      exerciseId: exerciseId ?? this.exerciseId,
      maxWeight: maxWeight ?? this.maxWeight,
      repMax: repMax ?? this.repMax,
    );
  }

  /// Creates a UserMax from JSON data
  factory UserMax.fromJson(Map<String, dynamic> json) {
    return UserMax(
      id: json['id'] as int?,
      exerciseId: json['exercise_id'] as int,
      maxWeight: json['max_weight'] as int,
      repMax: json['rep_max'] as int,
    );
  }

  /// Converts this UserMax to a JSON map
  Map<String, dynamic> toJson() {
    return {
      if (id != null) 'id': id,
      'exercise_id': exerciseId,
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
        exerciseId,
        maxWeight,
        repMax,
      ];

  @override
  bool? get stringify => true;
}
