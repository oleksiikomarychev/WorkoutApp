import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:workout_app/models/exercise_definition.dart';
import 'package:workout_app/models/workout.dart';
import 'package:workout_app/services/api_client.dart';
import 'package:workout_app/services/exercise_service.dart';
import 'package:workout_app/services/workout_service.dart';

class PreviewContextData {
  final Map<int, String> workoutNames;
  final Map<int, String> exerciseNames;
  const PreviewContextData({required this.workoutNames, required this.exerciseNames});
}

final _exerciseServiceProvider = Provider<ExerciseService>((ref) => ExerciseService(ApiClient()));
final _workoutServiceProvider = Provider<WorkoutService>((ref) => WorkoutService(apiClient: ApiClient()));

final previewContextProvider = FutureProvider.family<PreviewContextData, int>((ref, appliedPlanId) async {
  final exSvc = ref.watch(_exerciseServiceProvider);
  final woSvc = ref.watch(_workoutServiceProvider);

  // Workouts by applied plan
  final workouts = await woSvc.getWorkoutsByAppliedPlan(appliedPlanId);
  final workoutMap = <int, String>{
    for (final w in workouts)
      if (w.id != null) w.id!: (w.name ?? 'Workout ${w.id}')
  };

  // Exercise definitions
  final defs = await exSvc.getExerciseDefinitions();
  final exerciseMap = <int, String>{
    for (final d in defs)
      if (d.id != null) d.id!: (d.name ?? 'Exercise ${d.id}')
  };

  return PreviewContextData(workoutNames: workoutMap, exerciseNames: exerciseMap);
});

// Map structure: workoutId -> exerciseId -> setId -> {intensity, volume, weight}
typedef OriginalSetsMap = Map<int, Map<int?, Map<int?, Map<String, dynamic>>>>;

final workoutOriginalSetsProvider = FutureProvider.family<OriginalSetsMap, List<int>>((ref, workoutIds) async {
  final woSvc = ref.watch(_workoutServiceProvider);
  final out = <int, Map<int?, Map<int?, Map<String, dynamic>>>>{};
  for (final wid in workoutIds) {
    try {
      final w = await woSvc.getWorkoutWithDetails(wid);
      final mapEx = <int?, Map<int?, Map<String, dynamic>>>{};
      final instances = w.exerciseInstances ?? const [];
      for (final inst in instances) {
        final exId = inst.exerciseListId;
        final sets = inst.sets ?? const [];
        final mapSet = <int?, Map<String, dynamic>>{};
        for (final s in sets) {
          final sid = s.id;
          mapSet[sid] = {
            'rpe': s.rpe,
            'volume': s.reps, // reps is authoritative in DTO
            'weight': s.weight,
          };
        }
        mapEx[exId] = mapSet;
      }
      out[wid] = mapEx;
    } catch (_) {
      // ignore individual failures
    }
  }
  return out;
});
