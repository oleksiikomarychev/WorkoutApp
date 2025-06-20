import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../models/workout.dart';
import '../models/exercise.dart';
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
  List<Exercise> _exercises = [];
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
          // Get unique exercise IDs
          final exerciseIds = updatedWorkout.exerciseInstances
              .map((e) => e.exerciseId)
              .toSet()
              .toList();
              
          // Create a list of exercises from the instances
          _exercises = exerciseIds.map((id) {
            final instances = updatedWorkout.getInstancesForExercise(id);
            if (instances.isEmpty) return null;
            
            // Get the first instance to get exercise details
            final instance = instances.first;
            return Exercise(
              id: id,
              name: 'Exercise $id', // This should be replaced with actual exercise name
              instances: instances,
            );
          }).whereType<Exercise>().toList();
        });
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Ошибка загрузки упражнений: $e')),
        );
      }
    } finally {
      if (mounted) {
        setState(() {
          _isLoadingExercises = false;
        });
      }
    }
  }

  Widget _buildExerciseCard(Exercise exercise) {
    if (exercise.instances.isEmpty) return const SizedBox.shrink();
    
    // Get the first instance for display
    final instance = exercise.instances.first;
    
    return Card(
      margin: const EdgeInsets.symmetric(vertical: 8, horizontal: 16),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              exercise.name,
              style: const TextStyle(
                fontSize: 18,
                fontWeight: FontWeight.bold,
              ),
            ),
            if (exercise.description?.isNotEmpty ?? false) ...[
              const SizedBox(height: 8),
              Text(
                exercise.description!,
                style: TextStyle(
                  color: Colors.grey[600],
                  fontSize: 14,
                ),
              ),
            ],
            const SizedBox(height: 12),
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceAround,
              children: [
                _buildInfoColumn('Объем', '${instance.volume}'),
                _buildInfoColumn('Интенсивность', '${instance.intensity}%'),
                _buildInfoColumn('Усилие', '${instance.effort}'),
              ],
            ),
            if (exercise.instances.length > 1) ...[
              const SizedBox(height: 8),
              Text(
                '+${exercise.instances.length - 1} еще ${_getPluralForm(exercise.instances.length - 1, ['подход', 'подхода', 'подходов'])}',
                style: const TextStyle(
                  color: Colors.blue,
                  fontSize: 14,
                ),
              ),
            ],
          ],
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

  Widget _buildInfoColumn(String label, String value) {
    return Column(
      children: [
        Text(
          label,
          style: const TextStyle(
            fontSize: 12,
            color: Colors.grey,
          ),
        ),
        const SizedBox(height: 4),
        Text(
          value,
          style: const TextStyle(
            fontSize: 16,
            fontWeight: FontWeight.bold,
          ),
        ),
      ],
    );
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
              final exercise = await Navigator.push<ExerciseList>(
                context,
                MaterialPageRoute(
                  builder: (context) => ExerciseSelectionScreen(
                    workoutId: widget.workout!.id!,
                  ),
                ),
              );
              
              if (exercise != null) {
                // Navigate to exercise form with the selected exercise
                await Navigator.push<bool>(
                  context,
                  MaterialPageRoute(
                    builder: (context) => ExerciseFormScreen(
                      workoutId: widget.workout!.id!,
                      exercise: Exercise(
                        id: exercise.id,
                        name: exercise.name,
                        description: exercise.description ?? '',
                      ),
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

    if (_exercises.isEmpty) {
      return _buildEmptyState();
    }

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        if (widget.workout?.description?.isNotEmpty ?? false)
          Padding(
            padding: const EdgeInsets.all(16),
            child: Text(
              widget.workout!.description!,
              style: TextStyle(
                color: Colors.grey[600],
                fontSize: 14,
              ),
            ),
          ),
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
              itemCount: _exercises.length,
              itemBuilder: (context, index) {
                return _buildExerciseCard(_exercises[index]);
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
          final exercise = await Navigator.push<ExerciseList>(
            context,
            MaterialPageRoute(
              builder: (context) => ExerciseSelectionScreen(
                workoutId: _workout!.id!,
              ),
            ),
          );
          
          if (exercise != null && mounted) {
            // Navigate to exercise form with the selected exercise
            await Navigator.push<bool>(
              context,
              MaterialPageRoute(
                builder: (context) => ExerciseFormScreen(
                  workoutId: _workout!.id!,
                  exercise: Exercise(
                    id: exercise.id,
                    name: exercise.name,
                    description: exercise.description ?? '',
                  ),
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
