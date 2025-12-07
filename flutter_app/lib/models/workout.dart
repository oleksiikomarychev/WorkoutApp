import 'package:flutter/foundation.dart';
import 'package:freezed_annotation/freezed_annotation.dart';
import 'exercise_instance.dart';

part 'workout.freezed.dart';
part 'workout.g.dart';


enum WorkoutType {
  manual,
  generated,
}

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

    @JsonKey(name: 'applied_plan_id') int? appliedPlanId,
    @JsonKey(name: 'plan_order_index') int? planOrderIndex,

    @JsonKey(name: 'scheduled_for') DateTime? scheduledFor,
    @JsonKey(name: 'completed_at') DateTime? completedAt,
    @JsonKey(name: 'exercise_instances') @Default([]) List<ExerciseInstance> exerciseInstances,
    @JsonKey(includeFromJson: false, includeToJson: false) int? localId,
    @JsonKey(name: 'next_workout_id') int? nextWorkoutId,

    @JsonKey(name: 'workout_type') @Default(WorkoutType.manual) WorkoutType workoutType,
  }) = _Workout;

  factory Workout.fromJson(Map<String, dynamic> json) =>
      _$WorkoutFromJson(json);


  List<int> get exerciseDefinitionIds {
    return exerciseInstances
        .map((e) => e.exerciseDefinitionId)
        .whereType<int>()
        .toList();
  }


  List<ExerciseInstance> getExerciseInstancesForDefinition(int exerciseDefinitionId) {
    return exerciseInstances
        .where((ei) => ei.exerciseDefinitionId == exerciseDefinitionId)
        .toList();
  }


  Workout addExerciseInstance(ExerciseInstance instance) {
    final newInstances = List<ExerciseInstance>.from(exerciseInstances)..add(instance);
    return copyWith(exerciseInstances: newInstances);
  }


  Workout updateExerciseInstance(String instanceId, ExerciseInstance updatedInstance) {
    final index = exerciseInstances.indexWhere((ei) =>
      ei.id != null && ei.id.toString() == instanceId
    );
    if (index == -1) return this;

    final newInstances = List<ExerciseInstance>.from(exerciseInstances);
    newInstances[index] = updatedInstance;
    return copyWith(exerciseInstances: newInstances);
  }


  Workout removeExerciseInstance(String instanceId) {
    final newInstances = exerciseInstances.where((ei) =>
      !(ei.id != null && ei.id.toString() == instanceId)
    ).toList();
    return copyWith(exerciseInstances: newInstances);
  }


  double get totalVolume {
    return exerciseInstances.fold(0.0, (sum, instance) => sum + instance.calculatedVolume);
  }


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
      if (nextWorkoutId != null) 'next_workout_id': nextWorkoutId,
      'exercise_instances': exerciseInstances
          .map((ei) => ei.toFormData())
          .toList(),
      'workout_type': workoutType.toString().split('.').last,
    };
  }
}
