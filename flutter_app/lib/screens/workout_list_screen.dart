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
  const WorkoutListScreen({super.key});
  
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
    _workoutsFuture = Provider.of<WorkoutService>(context, listen: false).getWorkouts();
  }
  
  Future<void> _refreshWorkouts() async {
    setState(() {
      _isRefreshing = true;
    });
    
    await _loadWorkouts();
    
    setState(() {
      _isRefreshing = false;
    });
  }
  
  @override
  Widget build(BuildContext context) {
    final colorScheme = Theme.of(context).colorScheme;
    final textTheme = Theme.of(context).textTheme;
    
    return Scaffold(
      body: RefreshIndicator(
        onRefresh: _refreshWorkouts,
        color: colorScheme.primary,
        child: CustomScrollView(
          physics: const AlwaysScrollableScrollPhysics(),
          slivers: [

            SliverAppBar.medium(
              title: const Text('Тренировки'),
              actions: [
                IconButton(
                  icon: const Icon(Icons.search),
                  tooltip: 'Поиск',
                  onPressed: () {
                    ScaffoldMessenger.of(context).showSnackBar(
                      const SnackBar(content: Text('Поиск будет доступен в следующих версиях')),
                    );
                  },
                ),
                IconButton(
                  icon: const Icon(Icons.filter_list),
                  tooltip: 'Фильтр',
                  onPressed: () {
                    ScaffoldMessenger.of(context).showSnackBar(
                      const SnackBar(content: Text('Фильтрация будет доступна в следующих версиях')),
                    );
                  },
                ),
              ],
            ),
            

            FutureBuilder<List<Workout>>(
              future: _workoutsFuture,
              builder: (context, snapshot) {
                if (snapshot.connectionState == ConnectionState.waiting && !_isRefreshing) {

                  return SliverPadding(
                    padding: const EdgeInsets.all(16.0),
                    sliver: SliverList(
                      delegate: SliverChildBuilderDelegate(
                        (context, index) => _buildShimmerEffect(context),
                        childCount: 5,
                      ),
                    ),
                  );
                } else if (snapshot.hasError) {

                  return SliverFillRemaining(
                    child: Center(
                      child: Column(
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: [
                          Icon(
                            Icons.error_outline,
                            size: 60,
                            color: colorScheme.error,
                          ),
                          const SizedBox(height: 16),
                          Text(
                            'Произошла ошибка',
                            style: textTheme.titleLarge,
                          ),
                          const SizedBox(height: 8),
                          Text(
                            'Не удалось загрузить тренировки: ${snapshot.error}',
                            style: textTheme.bodyMedium?.copyWith(
                              color: colorScheme.onSurfaceVariant,
                            ),
                            textAlign: TextAlign.center,
                          ),
                          const SizedBox(height: 24),
                          FilledButton.icon(
                            onPressed: _refreshWorkouts,
                            icon: const Icon(Icons.refresh),
                            label: const Text('Повторить'),
                          ),
                        ],
                      ),
                    ),
                  );
                } else if (!snapshot.hasData || snapshot.data!.isEmpty) {

                  return SliverFillRemaining(
                    child: Center(
                      child: Column(
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: [
                          HeroIcon(
                            HeroIcons.bolt,
                            style: HeroIconStyle.outline,
                            size: 80,
                            color: colorScheme.primary.withOpacity(0.6),
                          ),
                          const SizedBox(height: 24),
                          Text(
                            'Нет тренировок',
                            style: textTheme.titleLarge,
                          ),
                          const SizedBox(height: 8),
                          Text(
                            'Создайте свою первую тренировку, чтобы начать',
                            style: textTheme.bodyMedium?.copyWith(
                              color: colorScheme.onSurfaceVariant,
                            ),
                            textAlign: TextAlign.center,
                          ),
                          const SizedBox(height: 32),
                          FilledButton.icon(
                            onPressed: _navigateToCreateWorkout,
                            icon: const Icon(Icons.add),
                            label: const Text('Создать тренировку'),
                          ),
                        ],
                      ),
                    ),
                  );
                } else {

                  final workouts = snapshot.data!;
                  return SliverPadding(
                    padding: const EdgeInsets.all(16.0),
                    sliver: SliverList(
                      delegate: SliverChildBuilderDelegate(
                        (context, index) {
                          final workout = workouts[index];
                          return _buildWorkoutCard(
                            context: context, 
                            workout: workout,
                            index: index,
                          );
                        },
                        childCount: workouts.length,
                      ),
                    ),
                  );
                }
              },
            ),
            

            const SliverPadding(padding: EdgeInsets.only(bottom: 80)),
          ],
        ),
      ),
      floatingActionButton: FloatingActionButton.extended(
        onPressed: _navigateToCreateWorkout,
        icon: const Icon(Icons.add),
        label: const Text('Тренировка'),
        elevation: 4,
      ),
    );
  }
  
  Future<void> _navigateToCreateWorkout() async {
    final result = await Navigator.push(
      context,
      MaterialPageRoute(
        builder: (context) => const WorkoutDetailScreen(),
      ),
    );
    
    if (result == true || result == null) {
      await _refreshWorkouts();
    }
  }
  
  Widget _buildWorkoutCard({
    required BuildContext context,
    required Workout workout,
    required int index,
  }) {
    final colorScheme = Theme.of(context).colorScheme;
    final textTheme = Theme.of(context).textTheme;
    

    final categoryColors = [
      colorScheme.primary,
      colorScheme.secondary,
      colorScheme.tertiary,
      colorScheme.error,
    ];
    
    final categoryColor = categoryColors[index % categoryColors.length];
    final String categoryText = _getCategoryText(workout.name);
    
    return OpenContainer(
      transitionType: ContainerTransitionType.fadeThrough,
      openBuilder: (context, _) => WorkoutDetailScreen(workout: workout),
      closedElevation: 0,
      closedShape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
      closedColor: Theme.of(context).cardTheme.color ?? colorScheme.surface,
      onClosed: (result) {
        if (result == true) {
          _refreshWorkouts();
        }
      },
      closedBuilder: (context, openContainer) {
        return Card(
          elevation: 0,
          margin: const EdgeInsets.only(bottom: 16),
          child: InkWell(
            onTap: openContainer,
            borderRadius: BorderRadius.circular(16),
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      Container(
                        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                        decoration: BoxDecoration(
                          color: categoryColor.withOpacity(0.1),
                          borderRadius: BorderRadius.circular(8),
                        ),
                        child: Text(
                          categoryText,
                          style: textTheme.labelSmall?.copyWith(
                            color: categoryColor,
                            fontWeight: FontWeight.bold,
                          ),
                        ),
                      ),
                      const Spacer(),
                      Text(
                        'Упражнений: ${workout.exercises?.length ?? 0}',
                        style: textTheme.bodySmall?.copyWith(
                          color: colorScheme.onSurfaceVariant,
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 16),
                  Text(
                    workout.name,
                    style: textTheme.titleMedium?.copyWith(
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                  if (workout.description != null && workout.description!.isNotEmpty) ...[  
                    const SizedBox(height: 8),
                    Text(
                      workout.description!,
                      style: textTheme.bodyMedium?.copyWith(
                        color: colorScheme.onSurfaceVariant,
                      ),
                      maxLines: 2,
                      overflow: TextOverflow.ellipsis,
                    ),
                  ],
                  const SizedBox(height: 16),
                  Row(
                    children: [
                      _buildInfoChip(
                        icon: Icons.calendar_today, 
                        label: 'Пн, Чт', 
                        context: context
                      ),
                      const SizedBox(width: 16),
                      _buildInfoChip(
                        icon: Icons.access_time, 
                        label: '45-60 мин', 
                        context: context
                      ),
                    ],
                  ),
                ],
              ),
            ),
          ),
        )
        .animate(delay: (100 * index).ms)
        .fadeIn(duration: 200.ms)
        .slideY(begin: 0.1, end: 0, duration: 200.ms);
      },
    );
  }
  
  Widget _buildInfoChip({
    required IconData icon,
    required String label,
    required BuildContext context,
  }) {
    final colorScheme = Theme.of(context).colorScheme;
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Icon(
          icon,
          size: 16,
          color: colorScheme.onSurfaceVariant,
        ),
        const SizedBox(width: 4),
        Text(
          label,
          style: Theme.of(context).textTheme.bodySmall?.copyWith(
            color: colorScheme.onSurfaceVariant,
          ),
        ),
      ],
    );
  }
  
  Widget _buildShimmerEffect(BuildContext context) {
    final colorScheme = Theme.of(context).colorScheme;
    return Shimmer.fromColors(
      baseColor: colorScheme.surfaceVariant,
      highlightColor: colorScheme.surface,
      child: Card(
        elevation: 0,
        margin: const EdgeInsets.only(bottom: 16),
        child: Container(
          padding: const EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  Container(
                    width: 80,
                    height: 20,
                    decoration: BoxDecoration(
                      color: Colors.white,
                      borderRadius: BorderRadius.circular(8),
                    ),
                  ),
                  const Spacer(),
                  Container(
                    width: 100,
                    height: 14,
                    decoration: BoxDecoration(
                      color: Colors.white,
                      borderRadius: BorderRadius.circular(4),
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 16),
              Container(
                width: 200,
                height: 24,
                decoration: BoxDecoration(
                  color: Colors.white,
                  borderRadius: BorderRadius.circular(4),
                ),
              ),
              const SizedBox(height: 8),
              Container(
                width: double.infinity,
                height: 14,
                decoration: BoxDecoration(
                  color: Colors.white,
                  borderRadius: BorderRadius.circular(4),
                ),
              ),
              const SizedBox(height: 8),
              Container(
                width: 250,
                height: 14,
                decoration: BoxDecoration(
                  color: Colors.white,
                  borderRadius: BorderRadius.circular(4),
                ),
              ),
              const SizedBox(height: 16),
              Row(
                children: [
                  Container(
                    width: 80,
                    height: 20,
                    decoration: BoxDecoration(
                      color: Colors.white,
                      borderRadius: BorderRadius.circular(20),
                    ),
                  ),
                  const SizedBox(width: 16),
                  Container(
                    width: 80,
                    height: 20,
                    decoration: BoxDecoration(
                      color: Colors.white,
                      borderRadius: BorderRadius.circular(20),
                    ),
                  ),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }
  

  String _getCategoryText(String workoutName) {
    final nameLower = workoutName.toLowerCase();
    
    if (nameLower.contains('грудь') || nameLower.contains('push')) {
      return 'ГРУДЬ';
    } else if (nameLower.contains('спин') || nameLower.contains('pull')) {
      return 'СПИНА';
    } else if (nameLower.contains('ног') || nameLower.contains('leg')) {
      return 'НОГИ';
    } else if (nameLower.contains('плеч') || nameLower.contains('shoulder')) {
      return 'ПЛЕЧИ';
    } else if (nameLower.contains('рук') || nameLower.contains('arm')) {
      return 'РУКИ';
    } else if (nameLower.contains('кардио') || nameLower.contains('cardio')) {
      return 'КАРДИО';
    } else {
      return 'ОБЩАЯ';
    }
  }
}
