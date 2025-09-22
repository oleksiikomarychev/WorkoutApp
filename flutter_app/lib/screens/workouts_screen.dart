import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/intl.dart';
import 'package:workout_app/services/logger_service.dart';
import 'package:workout_app/services/workout_service.dart';
import 'package:workout_app/widgets/empty_state.dart';
import 'package:workout_app/models/workout.dart';
import 'package:workout_app/services/service_locator.dart';
import 'package:workout_app/screens/workout_detail_screen.dart';
import 'package:workout_app/services/base_api_service.dart';
import 'package:workout_app/config/api_config.dart';
import '../models/applied_calendar_plan.dart';
import '../services/plan_service.dart';
import '../services/api_client.dart';

// Provider for ApiClient
final apiClientProvider = Provider<ApiClient>((ref) => ApiClient());

// Provider for PlanService
final planServiceProvider = Provider<PlanService>((ref) => PlanService(apiClient: ref.watch(apiClientProvider)));

// Provider for manual workouts notifier
final manualWorkoutsNotifierProvider = StateNotifierProvider<ManualWorkoutsNotifier, AsyncValue<List<Workout>>>((ref) {
  final workoutService = ref.watch(workoutServiceProvider);
  return ManualWorkoutsNotifier(workoutService);
});

// Provider for next workout in active plan
final nextWorkoutProvider = FutureProvider<Workout?>((ref) async {
  final planService = ref.watch(planServiceProvider);
  final workoutService = ref.watch(workoutServiceProvider);
  
  // Get active plan
  final activePlan = await planService.getActivePlan();
  if (activePlan == null) return null;
  
  // Get workouts for this plan
  final workouts = await workoutService.getWorkoutsByAppliedPlan(activePlan.id);
  
  // Filter workouts that are in the future and find the closest one
  final now = DateTime.now();
  Workout? nextWorkout;
  for (final workout in workouts) {
    if (workout.scheduledFor == null) continue;
    if (workout.scheduledFor!.isAfter(now)) {
      if (nextWorkout == null || workout.scheduledFor!.isBefore(nextWorkout.scheduledFor!)) {
        nextWorkout = workout;
      }
    }
  }
  return nextWorkout;
});

class WorkoutsScreen extends ConsumerStatefulWidget {
  const WorkoutsScreen({super.key});

  @override
  ConsumerState<WorkoutsScreen> createState() => _WorkoutsScreenState();
}

// State notifier for manual workouts
class ManualWorkoutsNotifier extends StateNotifier<AsyncValue<List<Workout>>> {
  final WorkoutService _workoutService;
  final int _limit = 20;
  int _skip = 0;
  bool _hasMore = true;
  bool _isLoadingMore = false;
  List<Workout> _items = [];

  ManualWorkoutsNotifier(this._workoutService) : super(const AsyncValue.loading()) {
    loadInitial();
  }

  bool get hasMore => _hasMore;
  bool get isLoadingMore => _isLoadingMore;
  List<Workout> get items => _items;

  Future<void> loadInitial() async {
    state = const AsyncValue.loading();
    _skip = 0;
    _hasMore = true;
    _items = [];
    try {
      final page = await _workoutService.getWorkoutsByType(WorkoutType.manual);
      _items = page;
      _hasMore = page.length == _limit;
      _skip = _items.length;
      state = AsyncValue.data(_items);
    } catch (e, stackTrace) {
      state = AsyncValue.error(e, stackTrace);
      rethrow;
    }
  }

  Future<void> loadMore() async {
    if (!_hasMore || _isLoadingMore) return;
    _isLoadingMore = true;
    try {
      final page = await _workoutService.getWorkoutsPaged(skip: _skip, limit: _limit);
      if (page.isEmpty) {
        _hasMore = false;
      } else {
        _items = [..._items, ...page];
        _skip = _items.length;
        _hasMore = page.length == _limit;
        state = AsyncValue.data(_items);
      }
    } catch (e, stackTrace) {
      state = AsyncValue.error(e, stackTrace);
    } finally {
      _isLoadingMore = false;
    }
  }
}

class _WorkoutsScreenState extends ConsumerState<WorkoutsScreen> {
  final LoggerService _logger = LoggerService('WorkoutsScreen');
  final TextEditingController _nameController = TextEditingController();
  final ScrollController _scrollController = ScrollController();
  
  Future<List<Map<String, dynamic>>> _fetchActivePlanWorkouts() async {
    final apiClient = ref.read(apiClientProvider);
    final response = await apiClient.get(ApiConfig.activePlanWorkoutsEndpoint);
    
    if (response is List) {
      return List<Map<String, dynamic>>.from(response.map((item) => item as Map<String, dynamic>));
    } else {
      throw Exception('Failed to load active plan workouts: response is not a list');
    }
  }

  @override
  void initState() {
    super.initState();
    // Trigger initial load
    WidgetsBinding.instance.addPostFrameCallback((_) {
      ref.read(manualWorkoutsNotifierProvider.notifier).loadInitial();
    });

    _scrollController.addListener(() {
      if (_scrollController.position.pixels >= _scrollController.position.maxScrollExtent - 200) {
        ref.read(manualWorkoutsNotifierProvider.notifier).loadMore();
      }
    });
  }

  @override
  void dispose() {
    _scrollController.dispose();
    _nameController.dispose();
    super.dispose();
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
                    await ref.read(manualWorkoutsNotifierProvider.notifier).loadInitial();
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
      body: SafeArea(
        child: Consumer(
        builder: (context, ref, child) {
          final manualWorkoutsState = ref.watch(manualWorkoutsNotifierProvider);

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

          return Column(
            children: [
              // Next Workout Section
              ref.watch(nextWorkoutProvider).when(
                loading: () => const Center(child: CircularProgressIndicator()),
                error: (err, stack) => Text('Error: $err'),
                data: (nextWorkout) {
                  if (nextWorkout == null) {
                    return const ListTile(
                      title: Text('No upcoming workouts'),
                      subtitle: Text('All workouts completed or no active plan'),
                    );
                  }
                  return Card(
                    margin: const EdgeInsets.all(16),
                    child: ListTile(
                      leading: const Icon(Icons.upcoming),
                      title: const Text('Next Workout'),
                      subtitle: Text(
                        '${nextWorkout.name} on ${DateFormat.yMd().format(nextWorkout.scheduledFor!)}',
                      ),
                      trailing: const Icon(Icons.chevron_right),
                      onTap: () {
                        Navigator.push(
                          context,
                          MaterialPageRoute(
                            builder: (_) => WorkoutDetailScreen(workoutId: nextWorkout.id!),
                          ),
                        );
                      },
                    ),
                  );
                },
              ),
              // Manual Workouts Section
              Expanded(
                child: manualWorkoutsState.when(
                  loading: () => const Center(child: CircularProgressIndicator()),
                  error: (werr, wst) => buildError('Error loading workouts', werr, wst, () {
                    ref.read(manualWorkoutsNotifierProvider.notifier).loadInitial();
                  }),
                  data: (workouts) {
                    final notifier = ref.read(manualWorkoutsNotifierProvider.notifier);
                    return RefreshIndicator(
                      onRefresh: () async {
                        await ref.read(manualWorkoutsNotifierProvider.notifier).loadInitial();
                      },
                      child: ListView(
                        controller: _scrollController,
                        padding: const EdgeInsets.all(16),
                        children: [
                          Text('Manual Workouts', style: Theme.of(context).textTheme.titleLarge),
                          const SizedBox(height: 12),

                          if (workouts.isEmpty)
                            EmptyState(
                              icon: Icons.fitness_center,
                              title: 'No Manual Workouts',
                              description: 'Create a manual workout',
                              action: ElevatedButton.icon(
                                onPressed: () async {
                                  await ref.read(manualWorkoutsNotifierProvider.notifier).loadInitial();
                                },
                                icon: const Icon(Icons.refresh),
                                label: const Text('Refresh'),
                              ),
                            ),

                          for (final workout in workouts) Card(
                            margin: const EdgeInsets.only(bottom: 16),
                            child: ListTile(
                              leading: const Icon(Icons.fitness_center),
                              title: Text(
                                workout.name,
                                style: Theme.of(context).textTheme.titleMedium,
                              ),
                              subtitle: Builder(builder: (_) {
                                String info = '';
                                if (workout.scheduledFor != null) {
                                  info = 'Scheduled: ${DateFormat('EEE, MMM d, HH:mm').format(workout.scheduledFor!)}';
                                } else if (workout.completedAt != null) {
                                  info = 'Completed: ${DateFormat('EEE, MMM d, HH:mm').format(workout.completedAt!)}';
                                }
                                return Text(
                                  info,
                                  style: Theme.of(context).textTheme.bodySmall,
                                );
                              }),
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
                                        await ref.read(manualWorkoutsNotifierProvider.notifier).loadInitial();
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
                                    builder: (_) => WorkoutDetailScreen(workoutId: workout.id!),
                                  ),
                                );
                                if (!mounted) return;
                                await ref.read(manualWorkoutsNotifierProvider.notifier).loadInitial();
                              },
                            ),
                          ),

                          // Pagination footer
                          if (notifier.isLoadingMore) const Center(child: Padding(
                            padding: EdgeInsets.symmetric(vertical: 16),
                            child: CircularProgressIndicator(),
                          )),
                          if (!notifier.hasMore && workouts.isNotEmpty)
                            const Center(child: Padding(
                              padding: EdgeInsets.symmetric(vertical: 16),
                              child: Text('No more workouts'),
                            )),
                        ],
                      ),
                    );
                  },
                ),
              ),
            ],
          );
        },
      ),
      ),
      floatingActionButton: FloatingActionButton(
        onPressed: _showCreateWorkoutDialog,
        child: const Icon(Icons.add),
      ),
    );
  }
}
