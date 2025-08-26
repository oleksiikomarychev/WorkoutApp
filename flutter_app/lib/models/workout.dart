import 'package:flutter/foundation.dart';
import 'package:freezed_annotation/freezed_annotation.dart';
import 'package:collection/collection.dart';
import 'exercise_instance.dart';
import 'exercise_definition.dart';

part 'workout.freezed.dart';
part 'workout.g.dart';

@freezed
class Workout with _$Workout {
  const Workout._();
  
  @JsonSerializable(explicitToJson: true)
  const factory Workout({
    int? id,
    required String name,
    String? notes,
    @JsonKey(name: 'status') String? status,
    @JsonKey(name: 'started_at') DateTime? startedAt,
    @JsonKey(name: 'duration_seconds') int? durationSeconds,
    @JsonKey(name: 'rpe_session') double? rpeSession,
    String? location,
    @JsonKey(name: 'readiness_score') int? readinessScore,
    // Linkage to applied calendar plans (nullable for regular workouts)
    @JsonKey(name: 'applied_plan_id') int? appliedPlanId,
    @JsonKey(name: 'plan_order_index') int? planOrderIndex,
    // Scheduling/Completion timestamps
    @JsonKey(name: 'scheduled_for') DateTime? scheduledFor,
    @JsonKey(name: 'completed_at') DateTime? completedAt,
    @JsonKey(name: 'exercise_instances') @Default([]) List<ExerciseInstance> exerciseInstances,
    @JsonKey(includeFromJson: false, includeToJson: false) int? localId,
  }) = _Workout;

  factory Workout.fromJson(Map<String, dynamic> json) =>
      _$WorkoutFromJson(json);

  // Get list of exercise definition IDs in this workout
  List<int> get exerciseDefinitionIds {
    return exerciseInstances
        .map((e) => e.exerciseDefinitionId)
        .whereType<int>()
        .toList();
  }
  
  // Get exercise instances for a specific exercise definition
  List<ExerciseInstance> getExerciseInstancesForDefinition(int exerciseDefinitionId) {
    return exerciseInstances
        .where((ei) => ei.exerciseDefinitionId == exerciseDefinitionId)
        .toList();
  }
  
  // Add a new exercise instance to this workout
  Workout addExerciseInstance(ExerciseInstance instance) {
    final newInstances = List<ExerciseInstance>.from(exerciseInstances)..add(instance);
    return copyWith(exerciseInstances: newInstances);
  }
  
  // Update an existing exercise instance (match by non-null id only)
  Workout updateExerciseInstance(String instanceId, ExerciseInstance updatedInstance) {
    final index = exerciseInstances.indexWhere((ei) => 
      ei.id != null && ei.id.toString() == instanceId
    );
    if (index == -1) return this;
    
    final newInstances = List<ExerciseInstance>.from(exerciseInstances);
    newInstances[index] = updatedInstance;
    return copyWith(exerciseInstances: newInstances);
  }
  
  // Remove an exercise instance by ID (match by non-null id only)
  Workout removeExerciseInstance(String instanceId) {
    final newInstances = exerciseInstances.where((ei) => 
      !(ei.id != null && ei.id.toString() == instanceId)
    ).toList();
    return copyWith(exerciseInstances: newInstances);
  }
  
  // Get total volume for the entire workout
  double get totalVolume {
    return exerciseInstances.fold(0.0, (sum, instance) => sum + instance.calculatedVolume);
  }
  
  // Convert to form data for API submission
  Map<String, dynamic> toFormData() {
    return {
      if (id != null) 'id': id,
      'name': name,
      if (notes != null) 'notes': notes,
      if (status != null) 'status': status,
      if (startedAt != null) 'started_at': startedAt?.toIso8601String(),
      if (durationSeconds != null) 'duration_seconds': durationSeconds,
      if (rpeSession != null) 'rpe_session': rpeSession,
      if (location != null) 'location': location,
      if (readinessScore != null) 'readiness_score': readinessScore,
      if (appliedPlanId != null) 'applied_plan_id': appliedPlanId,
      if (planOrderIndex != null) 'plan_order_index': planOrderIndex,
      if (scheduledFor != null) 'scheduled_for': scheduledFor?.toIso8601String(),
      if (completedAt != null) 'completed_at': completedAt?.toIso8601String(),
      'exercise_instances': exerciseInstances
          .map((ei) => ei.toFormData())
          .toList(),
    };
  }
}
