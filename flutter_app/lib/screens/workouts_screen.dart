import 'package:flutter/material.dart';
import 'package:flutter/gestures.dart' show PointerDeviceKind;
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/intl.dart';
import 'package:workout_app/services/logger_service.dart';
import 'package:workout_app/services/workout_service.dart';
import 'package:workout_app/widgets/empty_state.dart';
import 'package:workout_app/models/workout.dart';
import 'package:workout_app/services/service_locator.dart';
import 'package:workout_app/screens/workout_detail_screen.dart';
import 'package:workout_app/screens/user_profile_screen.dart';
import 'package:workout_app/services/base_api_service.dart';
import 'package:workout_app/config/api_config.dart';
import 'package:workout_app/config/constants/theme_constants.dart';
import 'package:workout_app/widgets/primary_app_bar.dart';
import 'package:workout_app/widgets/assistant_chat_host.dart';
import '../models/applied_calendar_plan.dart';
import '../services/plan_service.dart';
import '../services/api_client.dart';
import 'active_plan_screen.dart';


final planServiceProvider = Provider<PlanService>((ref) => PlanService(apiClient: ref.watch(apiClientProvider)));

final manualWorkoutsNotifierProvider = StateNotifierProvider<ManualWorkoutsNotifier, AsyncValue<List<Workout>>>((ref) {
  final workoutService = ref.watch(workoutServiceProvider);
  return ManualWorkoutsNotifier(workoutService);
});


  final nextWorkoutProvider = FutureProvider<Workout?>((ref) async {
    final planService = ref.watch(planServiceProvider);
    final workoutService = ref.watch(workoutServiceProvider);

    debugPrint('[WorkoutsScreen] Fetching active plan...');
    final activePlan = await planService.getActivePlan();
    if (activePlan == null) return null;
    debugPrint('[WorkoutsScreen] Active plan id=${activePlan.id}');

    debugPrint('[WorkoutsScreen] Fetching workouts for active plan...');
    final workouts = await workoutService.getWorkoutsByAppliedPlan(activePlan.id);
    debugPrint('[WorkoutsScreen] Received ${workouts.length} workouts for active plan');
    if (workouts.isEmpty) return null;

    workouts.sort((a, b) => (a.planOrderIndex ?? 1 << 30).compareTo(b.planOrderIndex ?? 1 << 30));

    for (final w in workouts) {
      final completed = (w.status?.toLowerCase() == 'completed') || (w.completedAt != null);
      if (!completed) {
        debugPrint('[WorkoutsScreen] Next by order: id=${w.id}, idx=${w.planOrderIndex}, status=${w.status}');
        return w;
      }
    }
    return null;
  });

class WorkoutsScreen extends ConsumerStatefulWidget {
  const WorkoutsScreen({super.key});

  @override
  ConsumerState<WorkoutsScreen> createState() => _WorkoutsScreenState();
}


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

  Future<void> deleteWorkout(int workoutId) async {
    try {
      await _workoutService.deleteWorkout(workoutId);
      _items.removeWhere((workout) => workout.id == workoutId);
      state = AsyncValue.data(_items);
    } catch (e, stackTrace) {
      state = AsyncValue.error(e, stackTrace);
    }
  }
}

class _WorkoutsScreenState extends ConsumerState<WorkoutsScreen> {
  final LoggerService _logger = LoggerService('WorkoutsScreen');
  final TextEditingController _nameController = TextEditingController();
  final ScrollController _scrollController = ScrollController();
  final PageController _bannerController = PageController();
  int _bannerIndex = 0;

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
    _bannerController.dispose();
    super.dispose();
  }

  Future<void> _showCreateWorkoutDialog() async {
    _nameController.clear();
    final workoutService = ref.read(workoutServiceProvider);


    final notesController = TextEditingController();
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
                  Row(
                    children: [
                      Checkbox(
                        value: startNow,
                        onChanged: (v) => setStateDialog(() => startNow = v ?? false),
                      ),
                      const Text('Start now (sets started_at)'),
                    ],
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
                  final name = _nameController.text.trim();
                  if (name.isEmpty) return;
                  try {
                    final workout = Workout(
                      name: name,
                      notes: emptyToNull(notesController.text),
                      startedAt: startNow ? DateTime.now() : null,
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
    return AssistantChatHost(
      builder: (context, openChat) {
        return Scaffold(
          backgroundColor: AppColors.background,
          appBar: PrimaryAppBar.main(
            title: 'Workouts',
            onTitleTap: openChat,
            actions: [
              IconButton(
                icon: const Icon(Icons.account_circle_outlined),
                onPressed: () async {
                  await Navigator.of(context).push(
                    MaterialPageRoute(builder: (_) => const UserProfileScreen()),
                  );
                },
              ),
            ],
          ),
          body: SafeArea(
            bottom: false,
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

                return Container(
                  color: AppColors.background,
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.stretch,
                    children: [
                      _HeroCarousel(
                        controller: _bannerController,
                        currentIndex: _bannerIndex,
                        onPageChanged: (i) => setState(() => _bannerIndex = i),
                      ),
                      const SizedBox(height: 24),
                      Expanded(
                        child: RefreshIndicator(
                          onRefresh: () async {

                            ref.invalidate(nextWorkoutProvider);
                            await Future.wait([
                              ref.read(manualWorkoutsNotifierProvider.notifier).loadInitial(),
                              ref.read(nextWorkoutProvider.future),
                            ]);
                          },
                          child: ListView(
                            controller: _scrollController,
                            physics: const BouncingScrollPhysics(parent: AlwaysScrollableScrollPhysics()),
                            padding: const EdgeInsets.fromLTRB(20, 0, 20, 0),
                            children: [
                              _PlansSection(nextWorkoutAsync: ref.watch(nextWorkoutProvider)),
                              const SizedBox(height: 24),
                              _LibrarySection(
                                manualWorkoutsState: manualWorkoutsState,
                                onRetry: () => ref.read(manualWorkoutsNotifierProvider.notifier).loadInitial(),
                                onOpenWorkout: (workoutId) async {
                                  await Navigator.of(context).push(
                                    MaterialPageRoute(
                                      builder: (_) => WorkoutDetailScreen(workoutId: workoutId),
                                    ),
                                  );
                                  if (!mounted) return;
                                  await ref.read(manualWorkoutsNotifierProvider.notifier).loadInitial();
                                },
                                readNotifier: () => ref.read(manualWorkoutsNotifierProvider.notifier),
                                buildError: buildError,
                                onCreateWorkout: _showCreateWorkoutDialog,
                              ),
                            ],
                          ),
                        ),
                      ),
                    ],
                  ),
                );
              },
            ),
          ),
        );
      },
    );
  }
}

class _HeroCarousel extends StatelessWidget {
  final PageController controller;
  final int currentIndex;
  final ValueChanged<int> onPageChanged;

  const _HeroCarousel({
    required this.controller,
    required this.currentIndex,
    required this.onPageChanged,
  });

  @override
  Widget build(BuildContext context) {
    const items = [
      'assets/images/image.png',
      'assets/images/image1.png',
    ];
    final gradients = const [
      LinearGradient(colors: [Color(0xFFFFC37F), Color(0xFFFF9472)], begin: Alignment.centerLeft, end: Alignment.centerRight),
      LinearGradient(colors: [Color(0xFFFFC37F), Color(0xFFFF9472)], begin: Alignment.centerLeft, end: Alignment.centerRight),
    ];

    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 20),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Container(
            decoration: BoxDecoration(
              borderRadius: BorderRadius.circular(24),
              boxShadow: AppShadows.lg,
            ),
            child: ClipRRect(
              borderRadius: BorderRadius.circular(24),
              child: AspectRatio(
                aspectRatio: 335 / 150,
                child: ScrollConfiguration(
                  behavior: ScrollConfiguration.of(context).copyWith(
                    dragDevices: const {
                      PointerDeviceKind.touch,
                      PointerDeviceKind.mouse,
                      PointerDeviceKind.trackpad,
                    },
                  ),
                  child: PageView.builder(
                    controller: controller,
                    onPageChanged: onPageChanged,
                    itemCount: items.length,
                    itemBuilder: (context, index) {
                      return Image.asset(
                        items[index],
                        fit: BoxFit.cover,
                        errorBuilder: (context, error, stackTrace) {
                          return Container(
                            decoration: BoxDecoration(gradient: gradients[index % gradients.length]),
                          );
                        },
                      );
                    },
                  ),
                ),
              ),
            ),
          ),
          const SizedBox(height: 12),
          Row(
            mainAxisAlignment: MainAxisAlignment.center,
            children: List.generate(items.length, (i) {
              final active = i == currentIndex;
              return AnimatedContainer(
                duration: AppDurations.medium,
                margin: const EdgeInsets.symmetric(horizontal: 4),
                width: active ? 14 : 8,
                height: 8,
                decoration: BoxDecoration(
                  color: active ? AppColors.primary : AppColors.textDisabled.withOpacity(0.4),
                  borderRadius: BorderRadius.circular(4),
                ),
              );
            }),
          ),
        ],
      ),
    );
  }
}

class _PlansSection extends StatelessWidget {
  final AsyncValue<Workout?> nextWorkoutAsync;

  const _PlansSection({required this.nextWorkoutAsync});

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            const _SectionTitle(
              icon: Icons.calendar_today,
              title: 'Plans Workouts',
            ),
            IconButton(
              tooltip: 'Open Calendar',
              onPressed: () {
                Navigator.of(context).push(
                  MaterialPageRoute(builder: (_) => const ActivePlanScreen()),
                );
              },
              icon: const Icon(Icons.calendar_today_outlined, color: AppColors.primary),
            ),
          ],
        ),
        const SizedBox(height: 16),
        nextWorkoutAsync.when(
          loading: () => Container(
            padding: const EdgeInsets.all(24),
            decoration: BoxDecoration(
              color: Colors.white,
              borderRadius: BorderRadius.circular(20),
              boxShadow: AppShadows.md,
            ),
            child: const Center(child: CircularProgressIndicator()),
          ),
          error: (err, stack) => Container(
            padding: const EdgeInsets.all(24),
            decoration: BoxDecoration(
              color: Colors.white,
              borderRadius: BorderRadius.circular(20),
              boxShadow: AppShadows.md,
            ),
            child: Text('Error: $err'),
          ),
          data: (nextWorkout) {
            final isCompleted = nextWorkout == null;
            final statusLabel = isCompleted ? 'Completed' : 'In Progress';
            final statusBackground = isCompleted
                ? Colors.white.withOpacity(0.16)
                : Colors.white.withOpacity(0.24);
            final statusTextColor = isCompleted ? const Color(0xFFB2FF59) : Colors.white;
            final subtitle = nextWorkout?.name ?? 'No upcoming workouts';
            final scheduleText = isCompleted
                ? 'All workouts completed or no active plan'
                : 'Scheduled for ${nextWorkout!.scheduledFor != null ? DateFormat('MMM d, yyyy').format(nextWorkout.scheduledFor!) : 'today'}';

            final card = Container(
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 18),
              decoration: BoxDecoration(
                gradient: const LinearGradient(
                  colors: [
                    Color(0xFF0D47A1),
                    Color(0xFF1976D2),
                    Color(0xFF5E35B1),
                  ],
                  begin: Alignment.topLeft,
                  end: Alignment.bottomRight,
                ),
                borderRadius: BorderRadius.circular(20),
                boxShadow: AppShadows.sm,
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                mainAxisSize: MainAxisSize.min,
                children: [
                  Row(
                    crossAxisAlignment: CrossAxisAlignment.center,
                    children: [
                      Container(
                        height: 44,
                        width: 44,
                        padding: const EdgeInsets.all(10),
                        decoration: BoxDecoration(
                          color: Colors.white.withOpacity(0.16),
                          borderRadius: BorderRadius.circular(14),
                        ),
                        child: const Icon(Icons.auto_graph, color: Colors.white, size: 20),
                      ),
                      const SizedBox(width: 12),
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              isCompleted ? 'Nice work!' : 'Current Workout',
                              style: AppTextStyles.titleLarge.copyWith(
                                fontWeight: FontWeight.w700,
                                color: Colors.white,
                              ),
                            ),
                            const SizedBox(height: 4),
                            Text(
                              subtitle,
                              style: AppTextStyles.bodyMedium.copyWith(
                                color: Colors.white.withOpacity(0.85),
                                fontWeight: FontWeight.w600,
                              ),
                            ),
                          ],
                        ),
                      ),
                      const SizedBox(width: 10),
                      Container(
                        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                        decoration: BoxDecoration(
                          color: statusBackground,
                          borderRadius: BorderRadius.circular(24),
                        ),
                        child: Row(
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            Text(
                              statusLabel,
                              style: AppTextStyles.titleSmall.copyWith(
                                color: statusTextColor,
                                fontWeight: FontWeight.w600,
                              ),
                            ),
                          ],
                        ),
                      ),
                      if (!isCompleted) ...[
                        const SizedBox(width: 6),
                        Container(
                          height: 28,
                          width: 28,
                          decoration: BoxDecoration(
                            color: Colors.white.withOpacity(0.18),
                            shape: BoxShape.circle,
                          ),
                          child: const Icon(
                            Icons.chevron_right,
                            size: 18,
                            color: Colors.white,
                          ),
                        ),
                      ],
                    ],
                  ),
                  const SizedBox(height: 12),
                  Text(
                    scheduleText,
                    style: AppTextStyles.bodySmall.copyWith(
                      color: Colors.white.withOpacity(0.8),
                    ),
                  ),
                ],
              ),
            );

            if (nextWorkout != null && nextWorkout.id != null) {
              return Consumer(
                builder: (context, ref, _) => GestureDetector(
                  behavior: HitTestBehavior.opaque,
                  onTap: () async {
                    await Navigator.push(
                      context,
                      MaterialPageRoute(
                        builder: (_) => WorkoutDetailScreen(workoutId: nextWorkout.id!),
                      ),
                    );

                    ref.invalidate(nextWorkoutProvider);
                  },
                  child: card,
                ),
              );
            }
            return card;
          },
        ),
      ],
    );
  }
}

class _LibrarySection extends StatelessWidget {
  final AsyncValue<List<Workout>> manualWorkoutsState;
  final VoidCallback onRetry;
  final Future<void> Function(int workoutId) onOpenWorkout;
  final ManualWorkoutsNotifier Function() readNotifier;
  final Widget Function(String, Object, StackTrace?, VoidCallback) buildError;
  final VoidCallback onCreateWorkout;

  const _LibrarySection({
    required this.manualWorkoutsState,
    required this.onRetry,
    required this.onOpenWorkout,
    required this.readNotifier,
    required this.buildError,
    required this.onCreateWorkout,
  });

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            const _SectionTitle(
              icon: Icons.sports_gymnastics,
              title: 'Workout Library',
            ),
            TextButton(
              onPressed: () {},
              style: TextButton.styleFrom(
                foregroundColor: AppColors.primary,
              ),
              child: const Text('View All'),
            ),
          ],
        ),
        const SizedBox(height: 16),
        manualWorkoutsState.when(
          loading: () => const Center(
            child: Padding(
              padding: EdgeInsets.symmetric(vertical: 32),
              child: CircularProgressIndicator(),
            ),
          ),
          error: (werr, wst) => buildError('Error loading workouts', werr, wst, onRetry),
          data: (workouts) {
            if (workouts.isEmpty) {
              return EmptyState(
                icon: Icons.fitness_center,
                title: 'No Manual Workouts',
                description: 'Create a manual workout',
                action: ElevatedButton.icon(
                  onPressed: onCreateWorkout,
                  icon: const Icon(Icons.play_arrow),
                  label: const Text('Start Workout'),
                ),
              );
            }

            final notifier = readNotifier();
            return Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                for (final workout in workouts) ...[
                  _WorkoutCard(
                    workout: workout,
                    onTap: () => onOpenWorkout(workout.id!),
                    onDelete: () async {
                      final confirmed = await showDialog<bool>(
                        context: context,
                        builder: (ctx) => AlertDialog(
                          title: const Text('Delete workout?'),
                          content: const Text('Are you sure you want to delete this manual workout?'),
                          actions: [
                            TextButton(
                              onPressed: () => Navigator.of(ctx).pop(false),
                              child: const Text('Cancel'),
                            ),
                            TextButton(
                              onPressed: () => Navigator.of(ctx).pop(true),
                              child: const Text('Delete'),
                            ),
                          ],
                        ),
                      );
                      if (confirmed == true) {
                        await notifier.deleteWorkout(workout.id!);
                      }
                    },
                  ),
                  const SizedBox(height: 16),
                ],
                if (notifier.isLoadingMore)
                  const Center(
                    child: Padding(
                      padding: EdgeInsets.symmetric(vertical: 16),
                      child: CircularProgressIndicator(),
                    ),
                  ),
                if (!notifier.hasMore && workouts.isNotEmpty)
                  const Center(
                    child: Padding(
                      padding: EdgeInsets.symmetric(vertical: 16),
                      child: Text('No more workouts'),
                    ),
                  ),
              ],
            );
          },
        ),
      ],
    );
  }
}

class _WorkoutCard extends StatelessWidget {
  final Workout workout;
  final VoidCallback onTap;
  final Future<void> Function() onDelete;

  const _WorkoutCard({required this.workout, required this.onTap, required this.onDelete});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(20),
        boxShadow: AppShadows.sm,
      ),
      child: Row(
        children: [
          Container(
            width: 44,
            height: 44,
            decoration: BoxDecoration(
              color: const Color(0xFFE8ECFF),
              borderRadius: BorderRadius.circular(12),
            ),
            child: const Icon(
              Icons.fitness_center,
              color: AppColors.primary,
            ),
          ),
          const SizedBox(width: 16),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  workout.name,
                  style: const TextStyle(
                    fontWeight: FontWeight.w600,
                    fontSize: 16,
                  ),
                ),
                const SizedBox(height: 4),
                Text(
                  _buildSubtitle(workout),
                  style: const TextStyle(
                    color: AppColors.textSecondary,
                    fontSize: 13,
                  ),
                ),
              ],
            ),
          ),
          IconButton(
            icon: const Icon(Icons.delete_outline, color: Colors.redAccent),
            onPressed: () async {
              await onDelete();
            },
          ),
          IconButton(
            onPressed: onTap,
            icon: const Icon(Icons.chevron_right),
            color: AppColors.primary,
          ),
        ],
      ),
    );
  }

  String _buildSubtitle(Workout workout) {
    if (workout.exerciseInstances.isNotEmpty) {
      return '${workout.exerciseInstances.length} exercises';
    }
    if (workout.durationSeconds != null) {
      final minutes = (workout.durationSeconds! / 60).round();
      return '$minutes min session';
    }
    if (workout.scheduledFor != null) {
      return 'Scheduled ${DateFormat('MMM d').format(workout.scheduledFor!)}';
    }
    return 'Manual session';
  }

}

class _SectionTitle extends StatelessWidget {
  final IconData icon;
  final String title;

  const _SectionTitle({required this.icon, required this.title});

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        Container(
          padding: const EdgeInsets.all(8),
          decoration: BoxDecoration(
            color: const Color(0xFFE8ECFF),
            borderRadius: BorderRadius.circular(12),
          ),
          child: Icon(icon, color: AppColors.primary, size: 20),
        ),
        const SizedBox(width: 12),
        Text(
          title,
          style: const TextStyle(
            fontWeight: FontWeight.w700,
            fontSize: 18,
          ),
        ),
      ],
    );
  }
}
