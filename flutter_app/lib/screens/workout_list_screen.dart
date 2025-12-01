import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:flutter_animate/flutter_animate.dart';
import 'package:heroicons/heroicons.dart';
import 'package:shimmer/shimmer.dart';
import 'package:animations/animations.dart';
import 'package:intl/intl.dart';
import 'package:workout_app/widgets/primary_app_bar.dart';
import 'package:workout_app/widgets/assistant_chat_host.dart';

import '../models/workout.dart';
import '../models/progression_template.dart';
import '../services/workout_service.dart';
import '../services/progression_service.dart';
import '../services/plan_service.dart';
import '../services/api_client.dart';
import 'workout_detail_screen.dart';

class WorkoutListScreen extends StatefulWidget {
  final int progressionId;
  
  const WorkoutListScreen({
    super.key,
    required this.progressionId,
  });
  
  @override
  State<WorkoutListScreen> createState() => _WorkoutListScreenState();
}

class _WorkoutListScreenState extends State<WorkoutListScreen> {
  late Future<List<Workout>> _workoutsFuture;
  bool _isRefreshing = false;
  late Future<Workout?> _nextWorkoutFuture;
  
  final TextEditingController _nameController = TextEditingController();

  @override
  void initState() {
    super.initState();
    _loadWorkouts();
    _loadNextWorkout();
  }
  
  Future<void> _loadWorkouts() async {
    final workoutService = Provider.of<WorkoutService>(context, listen: false);
    if (widget.progressionId > 0) {
      _workoutsFuture = workoutService.getWorkoutsByProgressionId(widget.progressionId);
    } else {
      _workoutsFuture = workoutService.getWorkouts();
    }
  }

  Future<void> _loadNextWorkout() async {
    final apiClient = ApiClient.create();
    final planService = PlanService(apiClient: apiClient);
    final workoutService = Provider.of<WorkoutService>(context, listen: false);
    _nextWorkoutFuture = () async {
      try {
        debugPrint('[WorkoutListScreen] Loading next workout (by plan order)...');
        final activePlan = await planService.getActivePlan();
        if (activePlan == null) {
          debugPrint('[WorkoutListScreen] No active plan');
          return null;
        }
        final workouts = await workoutService.getWorkoutsByAppliedPlan(activePlan.id);
        debugPrint('[WorkoutListScreen] Loaded ${workouts.length} workouts from active plan');
        if (workouts.isEmpty) return null;
        workouts.sort((a, b) => (a.planOrderIndex ?? 1 << 30).compareTo(b.planOrderIndex ?? 1 << 30));
        for (final w in workouts) {
          final completed = (w.status?.toLowerCase() == 'completed') || (w.completedAt != null);
          if (!completed) {
            debugPrint('[WorkoutListScreen] Next workout by order: id=${w.id}, idx=${w.planOrderIndex}');
            return w;
          }
        }
        debugPrint('[WorkoutListScreen] All workouts in plan are completed');
        return null;
      } catch (_) {
        return null;
      }
    }();
  }
  
  Future<void> _refreshWorkouts() async {
    setState(() {
      _isRefreshing = true;
    });
    
    await _loadWorkouts();
    await _loadNextWorkout();
    
    if (mounted) {
      setState(() {
        _isRefreshing = false;
      });
    }
  }



  void _showAddWorkoutDialog() {
    _nameController.clear();
    
    showDialog(
      context: context,
      builder: (context) => StatefulBuilder(
        builder: (context, setState) {
          return AlertDialog(
            title: const Text('Добавить тренировку'),
            content: SingleChildScrollView(
              child: Column(
                mainAxisSize: MainAxisSize.min,
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  TextField(
                    controller: _nameController,
                    decoration: const InputDecoration(
                      labelText: 'Название тренировки',
                      border: OutlineInputBorder(),
                    ),
                  ),

                ],
              ),
            ),
            actions: [
              TextButton(
                onPressed: () => Navigator.pop(context),
                child: const Text('Отмена'),
              ),
              ElevatedButton(
                onPressed: () async {
                  if (_nameController.text.isEmpty) {
                    ScaffoldMessenger.of(context).showSnackBar(
                      const SnackBar(content: Text('Введите название тренировки')),
                    );
                    return;
                  }
                  
                  try {
                    final workoutService = Provider.of<WorkoutService>(context, listen: false);
                    final workout = Workout(
                      name: _nameController.text,
                      exerciseInstances: [],
                      id: null,
                    );
                    
                    await workoutService.createWorkout(workout);
                    if (mounted) {
                      Navigator.pop(context);
                      _loadWorkouts();
                    }
                  } catch (e) {
                    if (mounted) {
                      Navigator.pop(context);
                      ScaffoldMessenger.of(context).showSnackBar(
                        SnackBar(content: Text('Ошибка при создании тренировки: $e')),
                      );
                    }
                  }
                },
                child: const Text('Добавить'),
              ),
            ],
          );
        },
      ),
    );
  }

  @override
  void dispose() {
    _nameController.dispose();
    super.dispose();
  }
  
  @override
  Widget build(BuildContext context) {
    final colorScheme = Theme.of(context).colorScheme;
    final textTheme = Theme.of(context).textTheme;
    
    return AssistantChatHost(
      builder: (context, openChat) {
        return Scaffold(
          appBar: PrimaryAppBar(
            title: 'Тренировки',
            onTitleTap: openChat,
            actions: const [
              SizedBox(width: 8),
            ],
          ),
          body: RefreshIndicator(
        onRefresh: _refreshWorkouts,
        child: ListView(
          padding: const EdgeInsets.symmetric(vertical: 12),
          children: [
            // Next Workout section (from active plan)
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 4),
              child: FutureBuilder<Workout?>(
                future: _nextWorkoutFuture,
                builder: (context, snap) {
                  if (snap.connectionState == ConnectionState.waiting) {
                    return const SizedBox.shrink();
                  }
                  if (snap.hasError) {
                    return const SizedBox.shrink();
                  }
                  final nw = snap.data;
                  if (nw == null) {
                    return const SizedBox.shrink();
                  }
                  final when = nw.scheduledFor != null
                      ? ' • ${DateFormat('yMMMd, HH:mm').format(nw.scheduledFor!.toLocal())}'
                      : '';
                  return Card(
                    child: ListTile(
                      leading: const Icon(Icons.upcoming),
                      title: const Text('Следующая тренировка'),
                      subtitle: Text('${nw.name}$when'),
                      trailing: const Icon(Icons.chevron_right),
                      onTap: () async {
                        final result = await Navigator.push<bool>(
                          context,
                          MaterialPageRoute(
                            builder: (context) => WorkoutDetailScreen(workoutId: nw.id!),
                          ),
                        );
                        if (result == true && mounted) {
                          await _refreshWorkouts();
                        } else {
                          // Ensure next workout card is refreshed after returning
                          await _loadNextWorkout();
                          if (mounted) setState(() {});
                        }
                      },
                    ),
                  );
                },
              ),
            ),
            // Workouts list section
            FutureBuilder<List<Workout>>(
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
                  return const Center(
                    child: Column(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        Icon(
                          Icons.fitness_center,
                          size: 64,
                          color: Colors.grey,
                        ),
                        SizedBox(height: 16),
                        Text(
                          'Нет тренировок в этой прогрессии',
                          style: TextStyle(fontSize: 16),
                        ),
                        SizedBox(height: 8),

                      ],
                    ),
                  );
                }

                return ListView.builder(
                  shrinkWrap: true,
                  physics: const NeverScrollableScrollPhysics(),
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
                            builder: (context) => WorkoutDetailScreen(workoutId: workout.id!),
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
          ],
        ),
      ),
      floatingActionButton: FloatingActionButton(
        onPressed: _showAddWorkoutDialog,
        child: const Icon(Icons.add),
      ),
        );
      },
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
