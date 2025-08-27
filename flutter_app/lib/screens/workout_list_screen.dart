import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:flutter_animate/flutter_animate.dart';
import 'package:heroicons/heroicons.dart';
import 'package:shimmer/shimmer.dart';
import 'package:animations/animations.dart';

import '../models/workout.dart';
import '../models/progression_template.dart';
import '../services/workout_service.dart';
import '../services/progression_service.dart';
import 'workout_detail_screen.dart';
import '../models/applied_calendar_plan.dart';
import '../services/applied_calendar_plan_service.dart';

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
  late Future<List<AppliedCalendarPlan>> _appliedPlansFuture;
  bool _isRefreshing = false;
  
  final TextEditingController _nameController = TextEditingController();

  @override
  void initState() {
    super.initState();
    _loadWorkouts();
  }
  
  Future<void> _loadWorkouts() async {
    final workoutService = Provider.of<WorkoutService>(context, listen: false);
    final appliedPlanService = Provider.of<AppliedCalendarPlanService>(context, listen: false);
    _appliedPlansFuture = appliedPlanService.getUserAppliedCalendarPlans();
    if (widget.progressionId > 0) {
      _workoutsFuture = workoutService.getWorkoutsByProgressionId(widget.progressionId);
    } else {
      _workoutsFuture = workoutService.getWorkouts();
    }
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
                      progressionTemplateId: widget.progressionId > 0 ? widget.progressionId : null,
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
    
    return Scaffold(
      appBar: AppBar(
        title: const Text('Тренировки'),
        actions: [
          const SizedBox(width: 8),
        ],
      ),
      body: RefreshIndicator(
        onRefresh: _refreshWorkouts,
        child: ListView(
          padding: const EdgeInsets.symmetric(vertical: 12),
          children: [
            // Applied Plans section
            FutureBuilder<List<AppliedCalendarPlan>>(
              future: _appliedPlansFuture,
              builder: (context, snapPlans) {
                if (snapPlans.connectionState == ConnectionState.waiting) {
                  return const Center(child: CircularProgressIndicator());
                }
                if (snapPlans.hasError) {
                  return Padding(
                    padding: const EdgeInsets.symmetric(horizontal: 16.0, vertical: 8),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        const Text('Ошибка загрузки примененных планов', style: TextStyle(color: Colors.red)),
                        const SizedBox(height: 8),
                        Text(snapPlans.error.toString(), style: const TextStyle(color: Colors.redAccent)),
                      ],
                    ),
                  );
                }
                final plans = (snapPlans.data ?? [])
                    .where((p) => p.isActive)
                    .toList();
                if (plans.isEmpty) return const SizedBox.shrink();
                return Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 16.0),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text('Активные планы', style: Theme.of(context).textTheme.titleLarge),
                      const SizedBox(height: 8),
                      for (final plan in plans)
                        Card(
                          margin: const EdgeInsets.only(bottom: 12),
                          child: ListTile(
                            leading: const Icon(Icons.event_available),
                            title: Text(plan.calendarPlan.name),
                            subtitle: Text(
                              plan.nextWorkout != null
                                  ? 'Следующая: ${plan.nextWorkout!.name}'
                                  : 'План активен',
                            ),
                            trailing: const Icon(Icons.chevron_right),
                            enabled: plan.nextWorkout != null,
                            onTap: plan.nextWorkout == null
                                ? null
                                : () async {
                                    // Open next workout details
                                    final workoutService = Provider.of<WorkoutService>(context, listen: false);
                                    try {
                                      final workout = await workoutService.getWorkoutWithDetails(plan.nextWorkout!.id);
                                      if (!mounted) return;
                                      await Navigator.of(context).push(
                                        MaterialPageRoute(
                                          builder: (_) => WorkoutDetailScreen(workout: workout),
                                        ),
                                      );
                                      if (!mounted) return;
                                      await _refreshWorkouts();
                                    } catch (e) {
                                      if (!mounted) return;
                                      ScaffoldMessenger.of(context).showSnackBar(
                                        SnackBar(content: Text('Не удалось открыть тренировку: $e')),
                                      );
                                    }
                                  },
                          ),
                        ),
                      const Divider(),
                    ],
                  ),
                );
              },
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
          ],
        ),
      ),
      floatingActionButton: FloatingActionButton(
        onPressed: _showAddWorkoutDialog,
        child: const Icon(Icons.add),
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
