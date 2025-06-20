import 'package:flutter/foundation.dart';

@immutable
class ExerciseInstance {
  final int? id;
  final int exerciseId;
  final int workoutId;
  final int volume;
  final int intensity;
  final int effort;
  final int? weight;
  final String? notes;
  final DateTime? createdAt;
  final DateTime? updatedAt;

  const ExerciseInstance({
    this.id,
    required this.exerciseId,
    required this.workoutId,
    this.volume = 0,
    this.intensity = 0,
    this.effort = 0,
    this.weight,
    this.notes,
    this.createdAt,
    this.updatedAt,
  });

  factory ExerciseInstance.fromJson(Map<String, dynamic>? json) {
    if (json == null) {
      throw const FormatException('ExerciseInstance JSON cannot be null');
    }
    
    try {
      // Safely parse required fields with fallbacks
      final exerciseId = _parseInt(json['exercise_id']);
      final workoutId = _parseInt(json['workout_id']);
      
      if (exerciseId == null || workoutId == null) {
        throw const FormatException('exercise_id and workout_id are required');
      }
      
      // Parse optional fields with fallbacks
      final volume = _parseInt(json['volume']) ?? 0;
      final intensity = _parseInt(json['intensity']) ?? 0;
      final effort = _parseInt(json['effort']) ?? 0;
      final weight = _parseInt(json['weight']);
      
      // Parse dates safely
      DateTime? parseDateTime(dynamic value) {
        if (value == null) return null;
        try {
          return DateTime.tryParse(value.toString());
        } catch (e) {
          debugPrint('Error parsing date: $e');
          return null;
        }
      }
      
      return ExerciseInstance(
        id: _parseInt(json['id']),
        exerciseId: exerciseId,
        workoutId: workoutId,
        volume: volume,
        intensity: intensity,
        effort: effort,
        weight: weight,
        notes: json['notes']?.toString(),
        createdAt: parseDateTime(json['created_at']),
        updatedAt: parseDateTime(json['updated_at']),
      );
    } catch (e, stackTrace) {
      debugPrint('Error parsing ExerciseInstance: $e\n$stackTrace');
      rethrow;
    }
  }
  
  static int? _parseInt(dynamic value) {
    if (value == null) return null;
    if (value is int) return value;
    if (value is num) return value.toInt();
    if (value is String) return int.tryParse(value);
    return null;
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'exercise_id': exerciseId,
      'workout_id': workoutId,
      'volume': volume,
      'intensity': intensity,
      'effort': effort,
      if (weight != null) 'weight': weight,
      if (notes != null) 'notes': notes,
    };
  }

  ExerciseInstance copyWith({
    int? id,
    int? exerciseId,
    int? workoutId,
    int? volume,
    int? intensity,
    int? effort,
    int? weight,
    String? notes,
    DateTime? createdAt,
    DateTime? updatedAt,
  }) {
    return ExerciseInstance(
      id: id ?? this.id,
      exerciseId: exerciseId ?? this.exerciseId,
      workoutId: workoutId ?? this.workoutId,
      volume: volume ?? this.volume,
      intensity: intensity ?? this.intensity,
      effort: effort ?? this.effort,
      weight: weight ?? this.weight,
      notes: notes ?? this.notes,
      createdAt: createdAt ?? (this.createdAt != null 
          ? DateTime.fromMillisecondsSinceEpoch(this.createdAt!.millisecondsSinceEpoch)
          : null),
      updatedAt: updatedAt ?? (this.updatedAt != null
          ? DateTime.fromMillisecondsSinceEpoch(this.updatedAt!.millisecondsSinceEpoch)
          : null),
    );
  }
}
