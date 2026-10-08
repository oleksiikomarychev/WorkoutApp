import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_animate/flutter_animate.dart';
import 'package:heroicons/heroicons.dart';
import 'package:shimmer/shimmer.dart';
import 'package:animations/animations.dart';
import 'package:intl/intl.dart';
import 'package:workout_app/widgets/primary_app_bar.dart';
import 'package:workout_app/widgets/assistant_chat_host.dart';
import 'package:workout_app/widgets/loading_indicator.dart';
import 'package:workout_app/widgets/error_message.dart';
import 'package:workout_app/widgets/empty_state.dart';

import '../models/workout.dart';
import '../models/progression_template.dart';
import '../services/workout_service.dart';
import '../services/progression_service.dart';
import '../services/plan_service.dart';
import 'package:workout_app/services/api_client.dart';
import 'package:workout_app/services/service_locator.dart';
import 'package:workout_app/l10n/app_localizations.dart';
import 'workout_detail_screen.dart';

class WorkoutListScreen extends ConsumerStatefulWidget {
  final int progressionId;

  const WorkoutListScreen({super.key, required this.progressionId});

  @override
  ConsumerState<WorkoutListScreen> createState() => _WorkoutListScreenState();
}

class _WorkoutListScreenState extends ConsumerState<WorkoutListScreen> {
  late Future<List<Workout>> _workoutsFuture;
  bool _isLoading = false;
  String? _errorMessage;
  late Future<Workout?> _nextWorkoutFuture;

  final TextEditingController _nameController = TextEditingController();

  @override
  void initState() {
    super.initState();
    _loadData();
  }

  Future<void> _loadData() async {
    setState(() {
      _isLoading = true;
      _errorMessage = null;
    });
    try {
      await _loadWorkouts();
      await _loadNextWorkout();
    } catch (e) {
      _errorMessage = e.toString();
    } finally {
      if (mounted) {
        setState(() {
          _isLoading = false;
        });
      }
    }
  }

  Future<void> _loadWorkouts() async {
    final workoutService = ref.read(workoutServiceProvider);
    if (widget.progressionId > 0) {
      _workoutsFuture = workoutService.getWorkoutsByProgressionId(
        widget.progressionId,
      );
    } else {
      _workoutsFuture = workoutService.getWorkouts();
    }
  }

  Future<void> _loadNextWorkout() async {
    final apiClient = ApiClient.create();
    final planService = PlanService(apiClient: apiClient);
    final workoutService = ref.read(workoutServiceProvider);
    _nextWorkoutFuture = () async {
      try {
        debugPrint(
          '[WorkoutListScreen] Loading next workout (by plan order)...',
        );
        final activePlan = await planService.getActivePlan();
        if (activePlan == null) {
          debugPrint('[WorkoutListScreen] No active plan');
          return null;
        }
        final workouts = await workoutService.getWorkoutsByAppliedPlan(
          activePlan.id,
        );
        debugPrint(
          '[WorkoutListScreen] Loaded ${workouts.length} workouts from active plan',
        );
        if (workouts.isEmpty) return null;
        workouts.sort(
          (a, b) => (a.planOrderIndex ?? 1 << 30).compareTo(
            b.planOrderIndex ?? 1 << 30,
          ),
        );
        for (final w in workouts) {
          final completed =
              (w.status?.toLowerCase() == 'completed') ||
              (w.completedAt != null);
          if (!completed) {
            debugPrint(
              '[WorkoutListScreen] Next workout by order: id=${w.id}, idx=${w.planOrderIndex}',
            );
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
    await _loadData();
  }

  void _showAddWorkoutDialog() {
    _nameController.clear();

    showDialog(
      context: context,
      builder: (context) => StatefulBuilder(
        builder: (context, setModalState) {
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
                      const SnackBar(
                        content: Text('Введите название тренировки'),
                      ),
                    );
                    return;
                  }

                  try {
                    final workoutService = ref.read(workoutServiceProvider);
                    final workout = Workout(
                      name: _nameController.text,
                      exerciseInstances: [],
                      id: null,
                    );

                    await workoutService.createWorkout(workout);
                    if (mounted) {
                      Navigator.pop(context);
                      _loadData();
                    }
                  } catch (e) {
                    if (mounted) {
                      Navigator.pop(context);
                      ScaffoldMessenger.of(context).showSnackBar(
                        SnackBar(
                          content: Text('Ошибка при создании тренировки: $e'),
                        ),
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
    return AssistantChatHost(
      contextBuilder: () async => {
        'screen': 'workout_list',
        'entities': {'progression_id': widget.progressionId},
      },
      builder: (context, openChat) {
        return Scaffold(
          appBar: PrimaryAppBar(
            title: 'Тренировки',
            onTitleTap: openChat,
            actions: const [SizedBox(width: 8)],
          ),
          body: RefreshIndicator(
            onRefresh: _refreshWorkouts,
            child: _buildBody(),
          ),
          floatingActionButton: FloatingActionButton(
            onPressed: _showAddWorkoutDialog,
            child: const Icon(Icons.add),
          ),
        );
      },
    );
  }

  Widget _buildBody() {
    if (_isLoading) {
      return const LoadingIndicator();
    }

    if (_errorMessage != null) {
      return ErrorMessage(
        message: 'Ошибка загрузки тренировок: $_errorMessage',
        onRetry: _loadData,
      );
    }

    return FutureBuilder<List<Workout>>(
      future: _workoutsFuture,
      builder: (context, snapshot) {
        if (snapshot.connectionState == ConnectionState.waiting) {
          return const LoadingIndicator();
        }

        if (snapshot.hasError) {
          return ErrorMessage(
            message: 'Ошибка загрузки тренировок: ${snapshot.error}',
            onRetry: _loadData,
          );
        }

        final workouts = snapshot.data ?? [];

        if (workouts.isEmpty) {
          return const EmptyState(
            icon: Icons.fitness_center,
            title: 'Нет тренировок',
            description: 'В этой прогрессии пока нет тренировок',
          );
        }

        return ListView(
          padding: const EdgeInsets.symmetric(vertical: 12),
          children: [
            _buildNextWorkoutCard(),
            ...workouts.map((workout) => _buildWorkoutTile(workout)),
          ],
        );
      },
    );
  }

  Widget _buildNextWorkoutCard() {
    final l10n = AppLocalizations.of(context);
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 4),
      child: FutureBuilder<Workout?>(
        future: _nextWorkoutFuture,
        builder: (context, snap) {
          if (snap.connectionState == ConnectionState.waiting ||
              snap.hasError ||
              snap.data == null) {
            return const SizedBox.shrink();
          }
          final nw = snap.data!;
          final when = nw.scheduledFor != null
              ? ' • ${DateFormat('yMMMd, HH:mm').format(nw.scheduledFor!.toLocal())}'
              : '';
          return Card(
            child: ListTile(
              leading: const Icon(Icons.upcoming),
              title: Text(l10n.workoutListNextWorkout),
              subtitle: Text('${nw.name}$when'),
              trailing: const Icon(Icons.chevron_right),
              onTap: () async {
                final result = await Navigator.push<bool>(
                  context,
                  MaterialPageRoute(
                    builder: (context) =>
                        WorkoutDetailScreen(workoutId: nw.id!),
                  ),
                );
                if (result == true && mounted) {
                  await _refreshWorkouts();
                } else {
                  await _loadNextWorkout();
                  if (mounted) setState(() {});
                }
              },
            ),
          );
        },
      ),
    );
  }

  Widget _buildWorkoutTile(Workout workout) {
    final l10n = AppLocalizations.of(context);
    return ListTile(
      title: Text(workout.name),
      subtitle: Text(
        l10n.exerciseCount(workout.exerciseInstances.length),
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

        if (result == true && mounted) {
          await _refreshWorkouts();
        }
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
