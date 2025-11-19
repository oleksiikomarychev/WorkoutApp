import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:workout_app/models/exercise_definition.dart';
import 'package:workout_app/services/api_client.dart';
import 'package:workout_app/services/exercise_service.dart';

final exerciseServiceProvider = Provider<ExerciseService>((ref) => ExerciseService(ApiClient()));

final exerciseDefinitionsProvider = FutureProvider<List<ExerciseDefinition>>((ref) async {
  final svc = ref.watch(exerciseServiceProvider);
  return svc.getExerciseDefinitions();
});

class TagCatalog {
  final Set<String> movementTypes;
  final Set<String> regions;
  final Set<String> muscleGroups;
  final Set<String> equipment;
  const TagCatalog({
    required this.movementTypes,
    required this.regions,
    required this.muscleGroups,
    required this.equipment,
  });
}

final tagCatalogProvider = Provider<TagCatalog>((ref) {
  final defs = ref.watch(exerciseDefinitionsProvider).maybeWhen(data: (d) => d, orElse: () => const <ExerciseDefinition>[]);
  final mt = <String>{};
  final rg = <String>{};
  final mg = <String>{};
  final eq = <String>{};
  for (final e in defs) {
    if (e.movementType != null && e.movementType!.isNotEmpty) mt.add(e.movementType!.toLowerCase());
    if (e.region != null && e.region!.isNotEmpty) rg.add(e.region!.toLowerCase());
    if (e.muscleGroup != null && e.muscleGroup!.isNotEmpty) mg.add(e.muscleGroup!.toLowerCase());
    if (e.equipment != null && e.equipment!.isNotEmpty) eq.add(e.equipment!.toLowerCase());
  }
  return TagCatalog(movementTypes: mt, regions: rg, muscleGroups: mg, equipment: eq);
});
