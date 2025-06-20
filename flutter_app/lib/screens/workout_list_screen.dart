import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:flutter_animate/flutter_animate.dart';
import 'package:heroicons/heroicons.dart';
import 'package:shimmer/shimmer.dart';
import 'package:animations/animations.dart';

import '../models/workout.dart';
import '../services/workout_service.dart';
import 'workout_detail_screen.dart';

class WorkoutListScreen extends StatefulWidget {
  final int progressionId;
  
  const WorkoutListScreen({
    Key? key,
    required this.progressionId,
  }) : super(key: key);
  
  @override
  State<WorkoutListScreen> createState() => _WorkoutListScreenState();
}

class _WorkoutListScreenState extends State<WorkoutListScreen> {
  late Future<List<Workout>> _workoutsFuture;
  bool _isRefreshing = false;
  
  @override
  void initState() {
    super.initState();
    _loadWorkouts();
  }
  
  Future<void> _loadWorkouts() async {
    final workoutService = Provider.of<WorkoutService>(context, listen: false);
    _workoutsFuture = workoutService.getWorkoutsByProgressionId(widget.progressionId);
  }
  
  Future<void> _refreshWorkouts() async {
    setState(() {
      _isRefreshing = true;
    });
    
    await _loadWorkouts();
    
    if (mounted) {
      setState(() {
        _isRefreshing = false;
      });
    }
  }

  void _showAddWorkoutDialog() {
    // TODO: Implement add workout dialog
  }
  
  @override
  Widget build(BuildContext context) {
    final colorScheme = Theme.of(context).colorScheme;
    final textTheme = Theme.of(context).textTheme;
    
    return Scaffold(
      appBar: AppBar(
        title: const Text('Тренировки'),
        leading: IconButton(
          icon: const Icon(Icons.arrow_back),
          onPressed: () => Navigator.of(context).pop(),
        ),
        actions: [
          IconButton(
            icon: const Icon(Icons.add),
            onPressed: _isRefreshing ? null : _showAddWorkoutDialog,
          ),
          const SizedBox(width: 8),
        ],
      ),
      body: RefreshIndicator(
        onRefresh: _refreshWorkouts,
        child: FutureBuilder<List<Workout>>(
          future: _workoutsFuture,
          builder: (context, snapshot) {
            if (snapshot.connectionState == ConnectionState.waiting) {
              return const Center(child: CircularProgressIndicator());
            }

            if (snapshot.hasError) {
              return Center(
                child: Column(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    const Icon(
                      Icons.error_outline,
                      size: 48,
                      color: Colors.red,
                    ),
                    const SizedBox(height: 16),
                    Text(
                      'Ошибка загрузки тренировок: ${snapshot.error}',
                      textAlign: TextAlign.center,
                      style: const TextStyle(color: Colors.red),
                    ),
                    const SizedBox(height: 16),
                    ElevatedButton.icon(
                      onPressed: _loadWorkouts,
                      icon: const Icon(Icons.refresh),
                      label: const Text('Повторить'),
                    ),
                  ],
                ),
              );
            }

            final workouts = snapshot.data ?? [];

            if (workouts.isEmpty) {
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
                      'Нет тренировок в этой прогрессии',
                      style: TextStyle(fontSize: 16),
                    ),
                    const SizedBox(height: 8),
                    ElevatedButton.icon(
                      onPressed: () {
                        // TODO: Implement add workout functionality
                      },
                      icon: const Icon(Icons.add),
                      label: const Text('Добавить тренировку'),
                    ),
                  ],
                ),
              );
            }

            return ListView.builder(
              itemCount: workouts.length,
              itemBuilder: (context, index) {
                final workout = workouts[index];
                return ListTile(
                  title: Text(workout.name),
                  subtitle: Text(
                    '${workout.exerciseInstances.length} ${_getExerciseCountText(workout.exerciseInstances.length)}',
                    style: const TextStyle(color: Colors.grey),
                  ),
                  trailing: const Icon(Icons.chevron_right),
                  onTap: () async {
                    final result = await Navigator.push<bool>(
                      context,
                      MaterialPageRoute(
                        builder: (context) => WorkoutDetailScreen(workout: workout),
                      ),
                    );
                    
                    // Refresh the workout list if we got back a true result
                    if (result == true && mounted) {
                      await _refreshWorkouts();
                    }
                  },
                );
              },
            );
          },
        ),
      ),
    );
  }
  
  String _getExerciseCountText(int count) {
    if (count % 10 == 1 && count % 100 != 11) {
      return 'упражнение';
    } else if ([2, 3, 4].contains(count % 10) && 
        ![12, 13, 14].contains(count % 100)) {
      return 'упражнения';
    } else {
      return 'упражнений';
    }
  }
}
