import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:workout_app/config/constants/theme_constants.dart';
import 'package:workout_app/services/logger_service.dart';
import 'package:workout_app/services/exercise_service.dart';
import 'package:workout_app/widgets/empty_state.dart';
import 'package:workout_app/models/exercise_definition.dart';
import 'package:workout_app/services/service_locator.dart';

class ExercisesScreen extends ConsumerStatefulWidget {
  const ExercisesScreen({super.key});

  @override
  ConsumerState<ExercisesScreen> createState() => _ExercisesScreenState();
}

// State notifier for exercises
class ExercisesNotifier extends StateNotifier<AsyncValue<List<ExerciseDefinition>>> {
  final ExerciseService _exerciseService;
  
  ExercisesNotifier(this._exerciseService) : super(const AsyncValue.loading()) {
    loadExercises();
  }
  
  Future<void> loadExercises() async {
    state = const AsyncValue.loading();
    try {
      final exercises = await _exerciseService.getExerciseDefinitions();
      state = AsyncValue.data(exercises);
    } catch (e, stackTrace) {
      state = AsyncValue.error(e, stackTrace);
      rethrow;
    }
  }
}

// Provider for exercises notifier
final exercisesNotifierProvider = StateNotifierProvider<ExercisesNotifier, AsyncValue<List<ExerciseDefinition>>>((ref) {
  final exerciseService = ref.watch(exerciseServiceProvider);
  return ExercisesNotifier(exerciseService);
});

class _ExercisesScreenState extends ConsumerState<ExercisesScreen> {
  final LoggerService _logger = LoggerService('ExercisesScreen');
  final TextEditingController _nameController = TextEditingController();
  final TextEditingController _muscleController = TextEditingController();
  final TextEditingController _equipmentController = TextEditingController();
  String? _movementType; // 'compound' | 'isolation'
  String? _region; // 'upper' | 'lower'
  
  @override
  void initState() {
    super.initState();
    // Trigger initial load
    WidgetsBinding.instance.addPostFrameCallback((_) {
      ref.read(exercisesNotifierProvider.notifier).loadExercises();
    });
  }

  @override
  void dispose() {
    _nameController.dispose();
    _muscleController.dispose();
    _equipmentController.dispose();
    super.dispose();
  }

  Future<void> _showExerciseDialog({ExerciseDefinition? initial}) async {
    _nameController.text = initial?.name ?? '';
    _muscleController.text = initial?.muscleGroup ?? '';
    _equipmentController.text = initial?.equipment ?? '';
    _movementType = initial?.movementType;
    _region = initial?.region;

    final service = ref.read(exerciseServiceProvider);
    final isEdit = initial?.id != null;

    await showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        title: Text(isEdit ? 'Edit Exercise' : 'Create Exercise'),
        content: SingleChildScrollView(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              TextField(
                controller: _nameController,
                decoration: const InputDecoration(labelText: 'Name'),
              ),
              const SizedBox(height: 8),
              TextField(
                controller: _muscleController,
                decoration: const InputDecoration(labelText: 'Muscle group'),
              ),
              const SizedBox(height: 8),
              TextField(
                controller: _equipmentController,
                decoration: const InputDecoration(labelText: 'Equipment'),
              ),
              const SizedBox(height: 8),
              DropdownButtonFormField<String>(
                value: _movementType,
                decoration: const InputDecoration(labelText: 'Movement type'),
                items: const [
                  DropdownMenuItem(value: 'compound', child: Text('Compound')),
                  DropdownMenuItem(value: 'isolation', child: Text('Isolation')),
                ],
                onChanged: (val) => setState(() => _movementType = val),
              ),
              const SizedBox(height: 8),
              DropdownButtonFormField<String>(
                value: _region,
                decoration: const InputDecoration(labelText: 'Region'),
                items: const [
                  DropdownMenuItem(value: 'upper', child: Text('Upper')),
                  DropdownMenuItem(value: 'lower', child: Text('Lower')),
                ],
                onChanged: (val) => setState(() => _region = val),
              ),
            ],
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(ctx).pop(),
            child: const Text('Cancel'),
          ),
          ElevatedButton(
            onPressed: () async {
              final name = _nameController.text.trim();
              if (name.isEmpty) return;
              final payload = ExerciseDefinition(
                id: initial?.id,
                name: name,
                muscleGroup: _muscleController.text.trim().isEmpty ? null : _muscleController.text.trim(),
                equipment: _equipmentController.text.trim().isEmpty ? null : _equipmentController.text.trim(),
                movementType: _movementType,
                region: _region,
              );
              try {
                if (isEdit) {
                  await service.updateExerciseDefinition(payload);
                } else {
                  await service.createExerciseDefinition(payload);
                }
                if (!mounted) return;
                Navigator.of(ctx).pop();
                await ref.read(exercisesNotifierProvider.notifier).loadExercises();
              } catch (e) {
                if (!mounted) return;
                ScaffoldMessenger.of(context).showSnackBar(
                  SnackBar(content: Text('Failed to ${isEdit ? 'update' : 'create'} exercise: $e')),
                );
              }
            },
            child: Text(isEdit ? 'Save' : 'Create'),
          ),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Exercises'),
        actions: [
          IconButton(
            icon: const Icon(Icons.add),
            onPressed: () => _showExerciseDialog(),
          ),
        ],
      ),
      body: Consumer(
        builder: (context, ref, child) {
          final exercisesState = ref.watch(exercisesNotifierProvider);
          
          return exercisesState.when(
            loading: () => const Center(child: CircularProgressIndicator()),
            error: (error, stackTrace) {
              _logger.e('Error loading exercises: $error\n$stackTrace');
              return Center(
                child: Column(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    const Icon(Icons.error_outline, color: Colors.red, size: 48),
                    const SizedBox(height: 16),
                    Text(
                      'Error loading exercises',
                      style: Theme.of(context).textTheme.titleMedium,
                    ),
                    const SizedBox(height: 8),
                    Text(
                      error.toString(),
                      textAlign: TextAlign.center,
                      style: Theme.of(context).textTheme.bodySmall,
                    ),
                    const SizedBox(height: 16),
                    ElevatedButton.icon(
                      onPressed: () => ref.refresh(exercisesNotifierProvider),
                      icon: const Icon(Icons.refresh),
                      label: const Text('Retry'),
                    ),
                  ],
                ),
              );
            },
            data: (exercises) {
              if (exercises.isEmpty) {
                return EmptyState(
                  icon: Icons.fitness_center,
                  title: 'No Exercises',
                  description: 'No exercises found. Add your first exercise!',
                  action: ElevatedButton.icon(
                    onPressed: () => ref.refresh(exercisesNotifierProvider),
                    icon: const Icon(Icons.refresh),
                    label: const Text('Refresh'),
                  ),
                );
              }
              
              return RefreshIndicator(
                onRefresh: () async {
                  await ref.refresh(exercisesNotifierProvider);
                  await ref.read(exercisesNotifierProvider.notifier).loadExercises();
                },
                child: ListView.builder(
                  padding: const EdgeInsets.all(16),
                  itemCount: exercises.length,
                  itemBuilder: (context, index) {
                    final exercise = exercises[index];
                    return Card(
                      margin: const EdgeInsets.only(bottom: 16),
                      child: ListTile(
                        leading: const Icon(Icons.fitness_center),
                        title: Text(
                          exercise.name,
                          style: Theme.of(context).textTheme.titleMedium,
                        ),
                        subtitle: Text(
                          '${exercise.muscleGroup ?? 'No muscle group'} • ${exercise.equipment ?? 'No equipment'}',
                          style: Theme.of(context).textTheme.bodySmall,
                        ),
                        trailing: Row(
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            IconButton(
                              icon: const Icon(Icons.delete, color: Colors.redAccent),
                              onPressed: () async {
                                final confirm = await showDialog<bool>(
                                  context: context,
                                  builder: (ctx) => AlertDialog(
                                    title: const Text('Delete exercise?'),
                                    content: Text('Are you sure you want to delete "${exercise.name}"?'),
                                    actions: [
                                      TextButton(
                                        onPressed: () => Navigator.of(ctx).pop(false),
                                        child: const Text('Cancel'),
                                      ),
                                      ElevatedButton(
                                        onPressed: () => Navigator.of(ctx).pop(true),
                                        child: const Text('Delete'),
                                      ),
                                    ],
                                  ),
                                );
                                if (confirm != true) return;
                                try {
                                  await ref.read(exerciseServiceProvider).deleteExerciseDefinition(exercise.id!);
                                  if (!mounted) return;
                                  await ref.read(exercisesNotifierProvider.notifier).loadExercises();
                                } catch (e) {
                                  if (!mounted) return;
                                  ScaffoldMessenger.of(context).showSnackBar(
                                    SnackBar(content: Text('Failed to delete exercise: $e')),
                                  );
                                }
                              },
                            ),
                            const Icon(Icons.chevron_right),
                          ],
                        ),
                        onTap: () => _showExerciseDialog(initial: exercise),
                      ),
                    );
                  },
                ),
              );
            },
          );
        },
      ),
      floatingActionButton: FloatingActionButton(
        onPressed: () => _showExerciseDialog(),
        child: const Icon(Icons.add),
      ),
    );
  }
}
