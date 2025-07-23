import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../models/workout.dart';
import '../models/exercise_instance.dart';

import '../models/exercise_list.dart';
import '../services/workout_service.dart';
import '../services/exercise_service.dart';
import 'exercise_form_screen.dart';
import 'exercise_selection_screen.dart';

class WorkoutDetailScreen extends StatefulWidget {
  final Workout? workout;

  const WorkoutDetailScreen({Key? key, this.workout}) : super(key: key);

  @override
  _WorkoutDetailScreenState createState() => _WorkoutDetailScreenState();
}

class _WorkoutDetailScreenState extends State<WorkoutDetailScreen> {
  bool _isLoading = false;
  bool _isLoadingExercises = false;
  List<ExerciseList> _uniqueExercises = [];
  Workout? _workout;

  @override
  void initState() {
    super.initState();
    _workout = widget.workout;
    if (_workout != null) {
      _loadExercises();
    }
  }

  Future<void> _loadExercises() async {
    if (_workout == null || _workout!.id == null) return;
    
    setState(() {
      _isLoadingExercises = true;
    });
    
    try {
      // Get workout with exercise instances
      final workoutService = Provider.of<WorkoutService>(context, listen: false);
      final updatedWorkout = await workoutService.getWorkoutWithDetails(_workout!.id!);
      
      if (mounted) {
        setState(() {
          _workout = updatedWorkout;
          final instances = updatedWorkout.exerciseInstances;
          final uniqueExerciseDefs = <int, ExerciseList>{};
          for (var instance in instances) {
            if (instance.exerciseDefinition != null) {
              uniqueExerciseDefs[instance.exerciseListId] = instance.exerciseDefinition!;
            }
          }
          _uniqueExercises = uniqueExerciseDefs.values.toList();
        });
      }
    } catch (e) {
      if (mounted) {
        WidgetsBinding.instance.addPostFrameCallback((_) {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(content: Text('Ошибка загрузки упражнений: $e')),
          );
        });
      }
    } finally {
      if (mounted) {
        setState(() {
          _isLoadingExercises = false;
        });
      }
    }
  }

  Widget _buildExerciseCard(ExerciseList exercise) {
    final instances = exercise.id != null ? _workout!.getInstancesForExercise(exercise.id!) : <ExerciseInstance>[];
    if (instances.isEmpty) return const SizedBox.shrink();

    final firstInstance = instances.first;

    return Card(
      margin: const EdgeInsets.symmetric(vertical: 8.0, horizontal: 16.0),
      elevation: 2,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
      child: InkWell(
        onTap: () => _navigateToExerciseForm(exercise, firstInstance),
        borderRadius: BorderRadius.circular(10),
        child: Padding(
          padding: const EdgeInsets.all(16.0),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                exercise.name,
                style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 18),
              ),
              const SizedBox(height: 8),
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  _buildInfoChip('Вес', '${firstInstance.weight} кг'),
                  _buildInfoChip('Объем', '${firstInstance.volume} повт.'),
                  _buildInfoChip('RPE', '${firstInstance.effort}'),
                ],
              ),
              if (instances.length > 1) ...[
                const SizedBox(height: 4),
                Text(
                  '+${instances.length - 1} ${_getPluralForm(instances.length - 1, ['подход', 'подхода', 'подходов'])}',
                  style: TextStyle(
                    color: Theme.of(context).primaryColor,
                    fontSize: 12,
                    fontWeight: FontWeight.w500,
                  ),
                ),
              ],
            ],
          ),
        ),
      ),
    );
  }

  String _getPluralForm(int n, List<String> forms) {
    n = n.abs() % 100;
    int n1 = n % 10;
    if (n > 10 && n < 20) return forms[2];
    if (n1 > 1 && n1 < 5) return forms[1];
    if (n1 == 1) return forms[0];
    return forms[2];
  }

  Widget _buildInfoChip(String label, String value) {
    return Chip(
      label: Text(
        '$label: $value',
        style: const TextStyle(fontSize: 14),
      ),
      backgroundColor: Theme.of(context).primaryColor.withOpacity(0.2),
    );
  }

  void _navigateToExerciseForm(ExerciseList exercise, ExerciseInstance? instance) async {
    final workoutId = _workout?.id;
    if (workoutId == null) return;

    final result = await Navigator.push<bool>(
      context,
      MaterialPageRoute(
        builder: (context) => ExerciseFormScreen(
          workoutId: workoutId,
          exercise: exercise,
          instance: instance,
        ),
      ),
    );

    if (result == true) {
      _loadExercises();
    }
  }

  Widget _buildEmptyState() {
    return Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          const Icon(
            Icons.fitness_center,
            size: 64,
            color: Colors.grey,
          ),
          const SizedBox(height: 16),
          const Text(
            'В этой тренировке пока нет упражнений',
            style: TextStyle(fontSize: 16),
            textAlign: TextAlign.center,
          ),
          const SizedBox(height: 8),
          ElevatedButton.icon(
            onPressed: () async {
              // Navigate to exercise selection screen
              final selectedExercise = await Navigator.push<ExerciseList>(
                context,
                MaterialPageRoute(
                  builder: (context) => ExerciseSelectionScreen(
                    workoutId: widget.workout!.id!,
                  ),
                ),
              );

              if (selectedExercise != null && mounted) {
                // Navigate to exercise form with the selected exercise
                await Navigator.push<bool>(
                  context,
                  MaterialPageRoute(
                    builder: (context) => ExerciseFormScreen(
                      workoutId: widget.workout!.id!,
                      exercise: selectedExercise,
                    ),
                  ),
                );

                await _loadExercises();

                if (mounted) {
                  ScaffoldMessenger.of(context).showSnackBar(
                    const SnackBar(content: Text('Упражнение добавлено')),
                  );
                }
              }
            },
            icon: const Icon(Icons.add),
            label: const Text('Добавить упражнение'),
          ),
        ],
      ),
    );
  }

  Widget _buildWorkoutDetails() {
    if (_isLoadingExercises) {
      return const Center(child: CircularProgressIndicator());
    }

    if (_uniqueExercises.isEmpty) {
      return _buildEmptyState();
    }

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [

        const Padding(
          padding: EdgeInsets.symmetric(horizontal: 16, vertical: 8),
          child: Text(
            'Упражнения',
            style: TextStyle(
              fontSize: 18,
              fontWeight: FontWeight.bold,
            ),
          ),
        ),
        Expanded(
          child: RefreshIndicator(
            onRefresh: _loadExercises,
            child: ListView.builder(
              padding: const EdgeInsets.only(bottom: 80), // Space for FAB
              itemCount: _uniqueExercises.length,
              itemBuilder: (context, index) {
                return _buildExerciseCard(_uniqueExercises[index]);
              },
            ),
          ),
        ),
      ],
    );
  }

  @override
  Widget build(BuildContext context) {
    if (widget.workout == null) {
      return Scaffold(
        appBar: AppBar(
          title: const Text('Ошибка'),
        ),
        body: const Center(
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Icon(
                Icons.error_outline,
                size: 64,
                color: Colors.red,
              ),
              SizedBox(height: 16),
              Text(
                'Тренировка не найдена',
                style: TextStyle(fontSize: 18),
              ),
            ],
          ),
        ),
      );
    }

    return Scaffold(
      appBar: AppBar(
        title: Text(_workout?.name ?? 'Тренировка'),
        actions: [
          IconButton(
            icon: const Icon(Icons.edit),
            onPressed: () {
              // TODO: Implement edit workout
            },
          ),
        ],
      ),
      body: _isLoading
          ? const Center(child: CircularProgressIndicator())
          : _buildWorkoutDetails(),
      floatingActionButton: _workout != null ? FloatingActionButton(
        onPressed: () async {
          // Navigate to exercise selection screen
          final selectedExercise = await Navigator.push<ExerciseList>(
            context,
            MaterialPageRoute(
              builder: (context) => ExerciseSelectionScreen(
                workoutId: _workout!.id!,
              ),
            ),
          );

          if (selectedExercise != null && mounted) {
            // Navigate to exercise form with the selected exercise
            await Navigator.push<bool>(
              context,
              MaterialPageRoute(
                builder: (context) => ExerciseFormScreen(
                  workoutId: _workout!.id!,
                  exercise: selectedExercise,
                ),
              ),
            );

            await _loadExercises();
            // Notify the user
            if (mounted) {
              ScaffoldMessenger.of(context).showSnackBar(
                const SnackBar(content: Text('Упражнение добавлено')),
              );
            }
          }
        },
        child: const Icon(Icons.add),
      ) : null,
    );
  }
}
