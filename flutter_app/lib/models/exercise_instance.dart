import 'package:flutter/foundation.dart';
import 'package:freezed_annotation/freezed_annotation.dart';
import 'exercise_set_dto.dart';
import 'exercise_definition.dart';

part 'exercise_instance.freezed.dart';
part 'exercise_instance.g.dart';

@freezed
class ExerciseInstance with _$ExerciseInstance {
  const ExerciseInstance._();
  
  @JsonSerializable(explicitToJson: true)
  const factory ExerciseInstance({
    int? id,
    @JsonKey(name: 'exercise_list_id') required int exerciseListId,
    @JsonKey(name: 'exercise_definition') ExerciseDefinition? exerciseDefinition,
    @JsonKey(name: 'workout_id') int? workoutId,
    @JsonKey(name: 'user_max_id') int? userMaxId,
    @Default([]) List<ExerciseSetDto> sets,
    String? notes,
    @JsonKey(name: 'order') int? order,
    @JsonKey(includeFromJson: false, includeToJson: false) int? localId,
  }) = _ExerciseInstance;

  factory ExerciseInstance.fromJson(Map<String, dynamic> json) =>
      _$ExerciseInstanceFromJson(json);

  // Getters for backward compatibility
  int? get exerciseDefinitionId => exerciseDefinition?.id;
  
  // Calculate total volume for all sets (prefer legacy provided volume if present)
  int get calculatedVolume {
    return sets.fold(0, (sum, set) => sum + set.computedVolume);
  }
  
  // Calculate average weight across all sets
  double? get calculatedWeight {
    if (sets.isEmpty) return null;
    final total = sets.fold(0.0, (sum, set) => sum + set.weight);
    return total / sets.length;
  }

  // Legacy UI getters
  int get volume => calculatedVolume;
  double? get weight => calculatedWeight;
  
  // Add a new set to this exercise instance
  ExerciseInstance addSet(ExerciseSetDto set) {
    final newSets = List<ExerciseSetDto>.from(sets)..add(set);
    return copyWith(sets: newSets);
  }
  
  // Update an existing set
  ExerciseInstance updateSet(String setId, ExerciseSetDto updatedSet) {
    final index = sets.indexWhere((s) => s.id.toString() == setId || s.localId.toString() == setId);
    if (index == -1) return this;
    
    final newSets = List<ExerciseSetDto>.from(sets);
    newSets[index] = updatedSet;
    return copyWith(sets: newSets);
  }
  
  // Remove a set by ID
  ExerciseInstance removeSet(String setId) {
    final newSets = sets.where((s) => 
      s.id.toString() != setId && s.localId.toString() != setId
    ).toList();
    return copyWith(sets: newSets);
  }
  
  // Convert to form data for API submission
  Map<String, dynamic> toFormData() {
    return {
      if (id != null) 'id': id,
      'exercise_list_id': exerciseListId,
      if (workoutId != null) 'workout_id': workoutId,
      if (userMaxId != null) 'user_max_id': userMaxId,
      'sets': sets.map((set) => set.toFormData()).toList(),
      if (notes != null) 'notes': notes,
      if (order != null) 'order': order,
    };
  }
}
