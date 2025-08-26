import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/intl.dart';
import 'package:workout_app/config/constants/theme_constants.dart';
import 'package:workout_app/services/logger_service.dart';
import 'package:workout_app/services/workout_service.dart';
import 'package:workout_app/services/applied_calendar_plan_service.dart';
import 'package:workout_app/widgets/empty_state.dart';
import 'package:workout_app/models/workout.dart';
import 'package:workout_app/models/applied_calendar_plan.dart';
import 'package:workout_app/services/service_locator.dart';
import 'package:workout_app/screens/workout_detail_screen.dart';

class WorkoutsScreen extends ConsumerStatefulWidget {
  const WorkoutsScreen({super.key});

  @override
  ConsumerState<WorkoutsScreen> createState() => _WorkoutsScreenState();
}

// State notifier for applied calendar plans
class AppliedPlansNotifier extends StateNotifier<AsyncValue<List<AppliedCalendarPlan>>> {
  final AppliedCalendarPlanService _service;

  AppliedPlansNotifier(this._service) : super(const AsyncValue.loading()) {
    loadPlans();
  }

  Future<void> loadPlans() async {
    state = const AsyncValue.loading();
    try {
      final plans = await _service.getUserAppliedCalendarPlans();
      state = AsyncValue.data(plans);
    } catch (e, stackTrace) {
      state = AsyncValue.error(e, stackTrace);
      rethrow;
    }
  }
}

// State notifier for workouts
class WorkoutsNotifier extends StateNotifier<AsyncValue<List<Workout>>> {
  final WorkoutService _workoutService;
  
  WorkoutsNotifier(this._workoutService) : super(const AsyncValue.loading()) {
    loadWorkouts();
  }

  Future<void> loadWorkouts() async {
    state = const AsyncValue.loading();
    try {
      final workouts = await _workoutService.getWorkouts();
      state = AsyncValue.data(workouts);
    } catch (e, stackTrace) {
      state = AsyncValue.error(e, stackTrace);
      rethrow;
    }
  }
}

// Provider for workouts notifier
final workoutsNotifierProvider = StateNotifierProvider<WorkoutsNotifier, AsyncValue<List<Workout>>>((ref) {
  final workoutService = ref.watch(workoutServiceProvider);
  return WorkoutsNotifier(workoutService);
});

final appliedPlansNotifierProvider = StateNotifierProvider<AppliedPlansNotifier, AsyncValue<List<AppliedCalendarPlan>>>((ref) {
  final service = ref.watch(appliedCalendarPlanServiceProvider);
  return AppliedPlansNotifier(service);
});

class _WorkoutsScreenState extends ConsumerState<WorkoutsScreen> {
  final LoggerService _logger = LoggerService('WorkoutsScreen');
  final TextEditingController _nameController = TextEditingController();
  
  @override
  void initState() {
    super.initState();
    // Trigger initial load
    WidgetsBinding.instance.addPostFrameCallback((_) {
      ref.read(workoutsNotifierProvider.notifier).loadWorkouts();
      ref.read(appliedPlansNotifierProvider.notifier).loadPlans();
    });
  }

  Future<void> _showCreateWorkoutDialog() async {
    _nameController.clear();
    final workoutService = ref.read(workoutServiceProvider);
    
    // Dialog-local controllers/state
    final notesController = TextEditingController();
    final statusController = TextEditingController();
    final locationController = TextEditingController();
    final durationController = TextEditingController(); // seconds
    final rpeController = TextEditingController();
    final readinessController = TextEditingController();
    bool startNow = false;

    await showDialog(
      context: context,
      builder: (ctx) => StatefulBuilder(
        builder: (ctx, setStateDialog) {
          return AlertDialog(
            title: const Text('Create Workout'),
            content: SingleChildScrollView(
              child: Column(
                mainAxisSize: MainAxisSize.min,
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  TextField(
                    controller: _nameController,
                    decoration: const InputDecoration(labelText: 'Name *'),
                  ),
                  const SizedBox(height: 8),
                  TextField(
                    controller: notesController,
                    decoration: const InputDecoration(labelText: 'Notes'),
                    maxLines: 3,
                  ),
                  const SizedBox(height: 8),
                  TextField(
                    controller: statusController,
                    decoration: const InputDecoration(labelText: 'Status'),
                  ),
                  const SizedBox(height: 8),
                  Row(
                    children: [
                      Checkbox(
                        value: startNow,
                        onChanged: (v) => setStateDialog(() => startNow = v ?? false),
                      ),
                      const Text('Start now (sets started_at)'),
                    ],
                  ),
                  const SizedBox(height: 8),
                  TextField(
                    controller: durationController,
                    decoration: const InputDecoration(labelText: 'Duration (seconds)'),
                    keyboardType: TextInputType.number,
                  ),
                  const SizedBox(height: 8),
                  TextField(
                    controller: rpeController,
                    decoration: const InputDecoration(labelText: 'Session RPE (1-10)'),
                    keyboardType: const TextInputType.numberWithOptions(decimal: true),
                  ),
                  const SizedBox(height: 8),
                  TextField(
                    controller: locationController,
                    decoration: const InputDecoration(labelText: 'Location'),
                  ),
                  const SizedBox(height: 8),
                  TextField(
                    controller: readinessController,
                    decoration: const InputDecoration(labelText: 'Readiness score (0-100)'),
                    keyboardType: TextInputType.number,
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
                  String? emptyToNull(String s) => s.trim().isEmpty ? null : s.trim();
                  int? parseInt(String s) => int.tryParse(s.trim());
                  double? parseDouble(String s) => double.tryParse(s.trim().replaceAll(',', '.'));
                  final name = _nameController.text.trim();
                  if (name.isEmpty) return;
                  try {
                    final workout = Workout(
                      name: name,
                      notes: emptyToNull(notesController.text),
                      status: emptyToNull(statusController.text),
                      startedAt: startNow ? DateTime.now() : null,
                      durationSeconds: parseInt(durationController.text),
                      rpeSession: parseDouble(rpeController.text),
                      location: emptyToNull(locationController.text),
                      readinessScore: parseInt(readinessController.text),
                      exerciseInstances: const [],
                    );
                    await workoutService.createWorkout(workout);
                    if (!mounted) return;
                    Navigator.of(ctx).pop();
                    await ref.read(workoutsNotifierProvider.notifier).loadWorkouts();
                  } catch (e) {
                    if (!mounted) return;
                    ScaffoldMessenger.of(context).showSnackBar(
                      SnackBar(content: Text('Failed to create workout: $e')),
                    );
                  }
                },
                child: const Text('Create'),
              ),
            ],
          );
        },
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    
    return Scaffold(
      appBar: AppBar(
        title: const Text('Workouts'),
        actions: [
          IconButton(
            icon: const Icon(Icons.add),
            onPressed: _showCreateWorkoutDialog,
          ),
        ],
      ),
      body: Consumer(
        builder: (context, ref, child) {
          final workoutsState = ref.watch(workoutsNotifierProvider);
          final plansState = ref.watch(appliedPlansNotifierProvider);

          Widget buildError(String title, Object error, StackTrace? stackTrace, VoidCallback retry) {
            _logger.e('$title: $error\n$stackTrace');
            return Center(
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  const Icon(Icons.error_outline, color: Colors.red, size: 48),
                  const SizedBox(height: 16),
                  Text(title, style: Theme.of(context).textTheme.titleMedium),
                  const SizedBox(height: 8),
                  Text(error.toString(), textAlign: TextAlign.center, style: Theme.of(context).textTheme.bodySmall),
                  const SizedBox(height: 16),
                  ElevatedButton.icon(onPressed: retry, icon: const Icon(Icons.refresh), label: const Text('Retry')),
                ],
              ),
            );
          }

          return plansState.when(
            loading: () => const Center(child: CircularProgressIndicator()),
            error: (perr, pst) => buildError('Error loading plans', perr, pst, () {
              ref.read(appliedPlansNotifierProvider.notifier).loadPlans();
            }),
            data: (plans) {
              return workoutsState.when(
                loading: () => const Center(child: CircularProgressIndicator()),
                error: (werr, wst) => buildError('Error loading workouts', werr, wst, () {
                  ref.read(workoutsNotifierProvider.notifier).loadWorkouts();
                }),
                data: (workouts) {
                  // Show only truly active plans that still have a next workout
                  final activePlans = plans
                      .where((p) => p.isActive && p.nextWorkout != null)
                      .toList();
                  final activePlanIds = activePlans.map((p) => p.id).toSet();
                  final regularWorkouts = workouts.where((w) => w.appliedPlanId == null || !activePlanIds.contains(w.appliedPlanId)).toList();

                  final dateFmt = DateFormat('EEE, MMM d, HH:mm');

                  return RefreshIndicator(
                    onRefresh: () async {
                      await ref.read(appliedPlansNotifierProvider.notifier).loadPlans();
                      await ref.read(workoutsNotifierProvider.notifier).loadWorkouts();
                    },
                    child: ListView(
                      padding: const EdgeInsets.all(16),
                      children: [
                        if (activePlans.isNotEmpty) ...[
                          Text('Active Plans', style: Theme.of(context).textTheme.titleLarge),
                          const SizedBox(height: 12),
                          for (final plan in activePlans) Card(
                            margin: const EdgeInsets.only(bottom: 12),
                            child: ListTile(
                              leading: const Icon(Icons.event_available),
                              title: Text(plan.calendarPlan.name, style: Theme.of(context).textTheme.titleMedium),
                              subtitle: Builder(
                                builder: (_) {
                                  final nw = plan.nextWorkout;
                                  if (nw == null) {
                                    return Text('All workouts completed', style: Theme.of(context).textTheme.bodySmall);
                                  }
                                  final when = nw.scheduledFor != null ? ' • ${dateFmt.format(nw.scheduledFor!)}' : '';
                                  return Text('Next: ${nw.name}$when', style: Theme.of(context).textTheme.bodySmall);
                                },
                              ),
                              trailing: const Icon(Icons.chevron_right),
                              enabled: plan.nextWorkout != null,
                              onTap: plan.nextWorkout == null ? null : () async {
                                try {
                                  final workout = await ref.read(workoutServiceProvider).getWorkoutWithDetails(plan.nextWorkout!.id);
                                  if (!mounted) return;
                                  await Navigator.of(context).push(
                                    MaterialPageRoute(
                                      builder: (_) => WorkoutDetailScreen(workout: workout),
                                    ),
                                  );
                                  if (!mounted) return;
                                  await ref.read(appliedPlansNotifierProvider.notifier).loadPlans();
                                  await ref.read(workoutsNotifierProvider.notifier).loadWorkouts();
                                } catch (e) {
                                  if (!mounted) return;
                                  ScaffoldMessenger.of(context).showSnackBar(
                                    SnackBar(content: Text('Failed to open next workout: $e')),
                                  );
                                }
                              },
                            ),
                          ),
                          const SizedBox(height: 16),
                          const Divider(),
                          const SizedBox(height: 16),
                        ],

                        Text('Workouts', style: Theme.of(context).textTheme.titleLarge),
                        const SizedBox(height: 12),

                        if (regularWorkouts.isEmpty)
                          EmptyState(
                            icon: Icons.fitness_center,
                            title: 'No Regular Workouts',
                            description: 'Create a workout or pick one from a plan.',
                            action: ElevatedButton.icon(
                              onPressed: () async {
                                await ref.read(workoutsNotifierProvider.notifier).loadWorkouts();
                              },
                              icon: const Icon(Icons.refresh),
                              label: const Text('Refresh'),
                            ),
                          ),

                        for (final workout in regularWorkouts) Card(
                          margin: const EdgeInsets.only(bottom: 16),
                          child: ListTile(
                            leading: const Icon(Icons.fitness_center),
                            title: Text(
                              workout.name,
                              style: Theme.of(context).textTheme.titleMedium,
                            ),
                            subtitle: Text(
                              'Exercises: ${workout.exerciseInstances.length}',
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
                                        title: const Text('Delete workout?'),
                                        content: Text('Are you sure you want to delete "${workout.name}"?'),
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
                                      await ref.read(workoutServiceProvider).deleteWorkout(workout.id!);
                                      if (!mounted) return;
                                      await ref.read(workoutsNotifierProvider.notifier).loadWorkouts();
                                    } catch (e) {
                                      if (!mounted) return;
                                      ScaffoldMessenger.of(context).showSnackBar(
                                        SnackBar(content: Text('Failed to delete workout: $e')),
                                      );
                                    }
                                  },
                                ),
                                const Icon(Icons.chevron_right),
                              ],
                            ),
                            onTap: () async {
                              await Navigator.of(context).push(
                                MaterialPageRoute(
                                  builder: (_) => WorkoutDetailScreen(workout: workout),
                                ),
                              );
                              if (!mounted) return;
                              await ref.read(workoutsNotifierProvider.notifier).loadWorkouts();
                            },
                          ),
                        ),
                      ],
                    ),
                  );
                },
              );
            },
          );
        },
      ),
      floatingActionButton: FloatingActionButton(
        onPressed: _showCreateWorkoutDialog,
        child: const Icon(Icons.add),
      ),
    );
  }
}
