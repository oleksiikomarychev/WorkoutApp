import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:firebase_auth/firebase_auth.dart';
import 'package:intl/intl.dart';
import 'package:workout_app/config/constants/theme_constants.dart';
import 'package:workout_app/models/workout.dart';
import 'package:workout_app/models/workout_session.dart';
import 'package:workout_app/providers/providers.dart';
import 'package:workout_app/services/service_locator.dart' as sl;
import 'package:workout_app/services/workout_service.dart';
import 'package:workout_app/screens/workout_session_history_screen.dart';
import 'package:workout_app/screens/session_log_screen.dart';

const int kActivityWeeks = 48;

final profileAggregatesProvider = FutureProvider<UserStats>((ref) async {
  final analytics = ref.watch(sl.analyticsServiceProvider);
  final data = await analytics.getProfileAggregates(weeks: kActivityWeeks, limit: 20);

  final totalWorkouts = (data['total_workouts'] ?? 0) as int;
  final totalVolume = (data['total_volume'] ?? 0).toDouble();
  final activeDays = (data['active_days'] ?? 0) as int;
  final maxDayVolume = (data['max_day_volume'] ?? 0).toDouble();

  final activityRaw = data['activity_map'] as Map<String, dynamic>? ?? const {};
  final activityMap = <DateTime, DayActivity>{};
  activityRaw.forEach((key, value) {
    if (value is Map) {
      try {
        final dt = DateTime.parse(key);
        final day = DateTime(dt.year, dt.month, dt.day);
        final sc = (value['session_count'] ?? 0) as int;
        final vol = (value['volume'] ?? 0).toDouble();
        activityMap[day] = DayActivity(sessionCount: sc, volume: vol);
      } catch (_) {}
    }
  });

  final sessionsRaw = data['completed_sessions'] as List<dynamic>? ?? const [];
  final completedSessions = <WorkoutSession>[];
  for (final item in sessionsRaw) {
    if (item is Map<String, dynamic>) {
      try {
        completedSessions.add(WorkoutSession.fromJson(item));
      } catch (_) {}
    }
  }

  return UserStats(
    totalWorkouts: totalWorkouts,
    totalVolume: totalVolume,
    activeDays: activeDays,
    activityMap: activityMap,
    completedSessions: completedSessions.take(20).toList(),
    maxDayVolume: maxDayVolume,
  );
});

class UserStats {
  final int totalWorkouts;
  final double totalVolume;
  final int activeDays;
  final Map<DateTime, DayActivity> activityMap;
  final List<WorkoutSession> completedSessions;
  final double maxDayVolume;

  const UserStats({
    required this.totalWorkouts,
    required this.totalVolume,
    required this.activeDays,
    required this.activityMap,
    required this.completedSessions,
    required this.maxDayVolume,
  });

  factory UserStats.empty() => const UserStats(
        totalWorkouts: 0,
        totalVolume: 0,
        activeDays: 0,
        activityMap: {},
        completedSessions: [],
        maxDayVolume: 0,
      );
}

class DayActivity {
  final int sessionCount;
  final double volume;

  const DayActivity({
    required this.sessionCount,
    required this.volume,
  });
}

Future<UserStats> _calculateStats(WorkoutService workoutService, List<WorkoutSession> sessions) async {
  final completedSessions = sessions
      .where((s) => s.status.toLowerCase() == 'completed' || s.finishedAt != null)
      .toList();

  if (completedSessions.isEmpty) {
    return UserStats.empty();
  }

  completedSessions.sort((a, b) => b.startedAt.compareTo(a.startedAt));

  final todayLocal = DateTime.now();
  final gridEnd = DateTime(todayLocal.year, todayLocal.month, todayLocal.day);
  final gridStart = gridEnd.subtract(Duration(days: kActivityWeeks * 7 - 1));
  final uniqueActiveDays = <DateTime>{};
  final recentSessions = <WorkoutSession>[];

  for (final session in completedSessions) {
    final startedLocal = session.startedAt.toLocal();
    final day = DateTime(startedLocal.year, startedLocal.month, startedLocal.day);
    uniqueActiveDays.add(day);
    if (!startedLocal.isBefore(gridStart) && !startedLocal.isAfter(gridEnd)) {
      recentSessions.add(session);
    }
  }

  final workoutCache = <int, Workout?>{};
  final setVolumeCache = <int, Map<int, double>>{};
  final uniqueWorkoutIds = recentSessions.map((s) => s.workoutId).toSet().toList();

  await Future.wait(uniqueWorkoutIds.map((id) async {
    try {
      final workout = await workoutService.getWorkoutWithDetails(id);
      workoutCache[id] = workout;
      setVolumeCache[id] = _buildSetVolumeLookup(workout);
    } catch (_) {
      workoutCache[id] = null;
      setVolumeCache[id] = <int, double>{};
    }
  }));

  final dayVolumes = <DateTime, double>{};
  final dayCounts = <DateTime, int>{};
  double totalVolume = 0;

  for (final session in recentSessions) {
    final startedLocal = session.startedAt.toLocal();
    final day = DateTime(startedLocal.year, startedLocal.month, startedLocal.day);
    final completedSetIds = _extractCompletedSetIds(session.progress);
    double sessionVolume = 0;

    final workout = workoutCache[session.workoutId];
    if (workout != null) {
      final setLookup = setVolumeCache[session.workoutId] ?? const <int, double>{};
      if (completedSetIds.isEmpty) {
        sessionVolume = workout.totalVolume;
      } else {
        for (final setId in completedSetIds) {
          final volume = setLookup[setId];
          if (volume != null) {
            sessionVolume += volume;
          }
        }
        if (sessionVolume == 0 && workout.totalVolume > 0) {
          sessionVolume = workout.totalVolume;
        }
      }
    }

    dayVolumes[day] = (dayVolumes[day] ?? 0) + sessionVolume;
    dayCounts[day] = (dayCounts[day] ?? 0) + 1;
    totalVolume += sessionVolume;
  }

  final activityMap = <DateTime, DayActivity>{
    for (final entry in dayVolumes.entries)
      entry.key: DayActivity(
        sessionCount: dayCounts[entry.key] ?? 0,
        volume: entry.value,
      ),
  };

  double maxDayVolume = 0;
  for (final entry in activityMap.entries) {
    final d = entry.key;
    if (!d.isBefore(gridStart) && !d.isAfter(gridEnd)) {
      if (entry.value.volume > maxDayVolume) maxDayVolume = entry.value.volume;
    }
  }

  return UserStats(
    totalWorkouts: completedSessions.length,
    totalVolume: totalVolume,
    activeDays: uniqueActiveDays.length,
    activityMap: activityMap,
    completedSessions: completedSessions.take(20).toList(),
    maxDayVolume: maxDayVolume,
  );
}

Set<int> _extractCompletedSetIds(Map<String, dynamic> progress) {
  final completedField = progress['completed'];
  if (completedField is Map) {
    final ids = <int>{};
    for (final value in completedField.values) {
      if (value is List) {
        for (final raw in value) {
          final id = raw is int ? raw : int.tryParse(raw.toString());
          if (id != null) {
            ids.add(id);
          }
        }
      }
    }
    return ids;
  }
  return <int>{};
}

Map<int, double> _buildSetVolumeLookup(Workout workout) {
  final map = <int, double>{};
  for (final instance in workout.exerciseInstances) {
    for (final set in instance.sets) {
      final setId = set.id;
      if (setId != null) {
        map[setId] = set.computedVolume.toDouble();
      }
    }
  }
  return map;
}

class UserProfileScreen extends ConsumerWidget {
  const UserProfileScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final user = FirebaseAuth.instance.currentUser;

    return Scaffold(
      backgroundColor: AppColors.background,
      appBar: AppBar(
        backgroundColor: AppColors.surface,
        elevation: 0,
        leading: IconButton(
          icon: const Icon(Icons.arrow_back, color: AppColors.textPrimary),
          onPressed: () => Navigator.of(context).maybePop(),
        ),
        title: const Text(
          'Account',
          style: TextStyle(
            color: AppColors.textPrimary,
            fontSize: 24,
            fontWeight: FontWeight.bold,
          ),
        ),
        centerTitle: true,
      ),
      body: RefreshIndicator(
        onRefresh: () async {
          ref.invalidate(profileAggregatesProvider);
          ref.invalidate(completedSessionsProvider);
          await Future.wait([
            ref.read(profileAggregatesProvider.future),
            ref.read(completedSessionsProvider.future),
          ]);
        },
        child: ref.watch(profileAggregatesProvider).when(
          loading: () => const Center(child: CircularProgressIndicator()),
          error: (error, _) => _buildErrorState(ref, error),
          data: (stats) => _buildContent(context, ref, stats, user),
        ),
      ),
    );
  }

  Widget _buildErrorState(WidgetRef ref, Object error) {
    return Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          const Icon(Icons.error_outline, size: 48, color: AppColors.error),
          const SizedBox(height: 16),
          Text('Ошибка загрузки: $error'),
          const SizedBox(height: 16),
          ElevatedButton(
            onPressed: () {
              ref.invalidate(profileAggregatesProvider);
              ref.invalidate(completedSessionsProvider);
            },
            child: const Text('Повторить'),
          ),
        ],
      ),
    );
  }

  Widget _buildContent(BuildContext context, WidgetRef ref, UserStats stats, User? user) {
    return SingleChildScrollView(
      physics: const AlwaysScrollableScrollPhysics(),
      child: Column(
        children: [
          const SizedBox(height: 24),
          _buildProfileHeader(user, stats),
          const SizedBox(height: 32),
          _buildActivitySection(stats),
          const SizedBox(height: 32),
          _buildCompletedWorkouts(context, ref),
          const SizedBox(height: 32),
        ],
      ),
    );
  }

  Widget _buildProfileHeader(User? user, UserStats stats) {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 24),
      child: Column(
        children: [
          Container(
            width: 100,
            height: 100,
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              color: AppColors.primary.withOpacity(0.15),
              image: user?.photoURL != null
                  ? DecorationImage(
                      image: NetworkImage(user!.photoURL!),
                      fit: BoxFit.cover,
                    )
                  : null,
            ),
            child: user?.photoURL == null
                ? Center(
                    child: Text(
                      (user?.displayName?.isNotEmpty == true)
                          ? user!.displayName!.substring(0, 1).toUpperCase()
                          : 'U',
                      style: const TextStyle(
                        fontSize: 40,
                        fontWeight: FontWeight.bold,
                        color: AppColors.primary,
                      ),
                    ),
                  )
                : null,
          ),
          const SizedBox(height: 16),
          Text(
            user?.displayName ?? 'User',
            style: const TextStyle(
              fontSize: 24,
              fontWeight: FontWeight.bold,
              color: AppColors.textPrimary,
            ),
          ),
          const SizedBox(height: 4),
          Text(
            user?.email ?? '',
            style: const TextStyle(
              fontSize: 14,
              color: AppColors.textSecondary,
            ),
          ),
          const SizedBox(height: 4),
          Text(
            'Member since ${user?.metadata.creationTime != null ? DateFormat('yyyy').format(user!.metadata.creationTime!) : DateFormat('yyyy').format(DateTime.now())}',
            style: const TextStyle(
              fontSize: 14,
              color: AppColors.textSecondary,
            ),
          ),
          const SizedBox(height: 24),
          Row(
            children: [
              Expanded(
                child: _buildStatCard(
                  '${stats.totalWorkouts}',
                  'Total Workouts',
                  const Color(0xFFD4F1D5),
                ),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: _buildStatCard(
                  stats.totalVolume.toStringAsFixed(0),
                  'Volume (kg)',
                  const Color(0xFFD4E6F1),
                ),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: _buildStatCard(
                  '${stats.activeDays}',
                  'Active Days',
                  const Color(0xFFFFE4C4),
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildStatCard(String value, String label, Color color) {
    return Container(
      padding: const EdgeInsets.symmetric(vertical: 12, horizontal: 8),
      decoration: BoxDecoration(
        color: color,
        borderRadius: BorderRadius.circular(12),
      ),
      child: Column(
        children: [
          Text(
            value,
            style: const TextStyle(
              fontSize: 20,
              fontWeight: FontWeight.bold,
              color: AppColors.textPrimary,
            ),
          ),
          const SizedBox(height: 4),
          Text(
            label,
            textAlign: TextAlign.center,
            style: const TextStyle(
              fontSize: 11,
              color: AppColors.textSecondary,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildActivitySection(UserStats stats) {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 24),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text(
            'Activity',
            style: TextStyle(
              fontSize: 20,
              fontWeight: FontWeight.bold,
              color: AppColors.textPrimary,
            ),
          ),
          const SizedBox(height: 8),
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text(
                'Last $kActivityWeeks weeks',
                style: const TextStyle(
                  fontSize: 14,
                  color: AppColors.textSecondary,
                ),
              ),
              Text(
                'Max: ${stats.maxDayVolume.toStringAsFixed(0)} kg/day',
                style: const TextStyle(
                  fontSize: 12,
                  color: AppColors.textSecondary,
                  fontWeight: FontWeight.w500,
                ),
              ),
            ],
          ),
          const SizedBox(height: 16),
          _buildActivityGrid(stats.activityMap, stats.maxDayVolume),
          const SizedBox(height: 8),
          _buildActivityLegend(stats.maxDayVolume),
        ],
      ),
    );
  }

  Widget _buildActivityGrid(Map<DateTime, DayActivity> activityMap, double maxVolume) {
    final today = DateTime.now();
    final endDate = DateTime(today.year, today.month, today.day);
    // Align to Monday (1 = Monday, 7 = Sunday)
    final endWeekStart = endDate.subtract(Duration(days: endDate.weekday - 1));
    final startWeekStart = endWeekStart.subtract(Duration(days: (kActivityWeeks - 1) * 7));

    final weeks = <List<DateTime>>[];
    for (int w = 0; w < kActivityWeeks; w++) {
      final weekStart = startWeekStart.add(Duration(days: w * 7));
      final weekDays = <DateTime>[];
      for (int d = 0; d < 7; d++) {
        weekDays.add(weekStart.add(Duration(days: d)));
      }
      weeks.add(weekDays);
    }

    return SingleChildScrollView(
      scrollDirection: Axis.horizontal,
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: weeks.map((weekDays) {
          // Determine month label for this column (if the week contains the 1st day of any month)
          String label = '';
          for (final d in weekDays) {
            if (d.day == 1) {
              label = DateFormat('MMM').format(d);
              break;
            }
          }

          return Padding(
            padding: const EdgeInsets.only(right: 4),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                SizedBox(
                  width: 12, // exact cell width; padding on the column adds the 4px gutter
                  child: Text(
                    label,
                    style: const TextStyle(
                      fontSize: 10,
                      fontWeight: FontWeight.w600,
                      color: AppColors.textPrimary,
                    ),
                    textAlign: TextAlign.center,
                    softWrap: false,
                    overflow: TextOverflow.visible,
                  ),
                ),
                const SizedBox(height: 6),
                for (final date in weekDays)
                  Padding(
                    padding: const EdgeInsets.only(bottom: 4),
                    child: Builder(builder: (_) {
                      final normalized = DateTime(date.year, date.month, date.day);
                      final dayActivity = _getActivityForDate(activityMap, normalized);
                      final volume = dayActivity?.volume ?? 0;
                      final color = _getActivityColor(volume, maxVolume);
                      return Tooltip(
                        message: dayActivity != null
                            ? '${DateFormat('MMM d').format(date)}\n${dayActivity.sessionCount} session(s)\n${volume.toStringAsFixed(0)} kg'
                            : '${DateFormat('MMM d').format(date)}\nNo activity',
                        child: Container(
                          width: 12,
                          height: 12,
                          decoration: BoxDecoration(
                            color: color,
                            borderRadius: BorderRadius.circular(3),
                          ),
                        ),
                      );
                    }),
                  ),
              ],
            ),
          );
        }).toList(),
      ),
    );
  }

  Color _getActivityColor(double volume, double maxVolume) {
    if (volume == 0) return const Color(0xFFEBEDF0);
    if (maxVolume == 0) return const Color(0xFFEBEDF0);
    
    final intensity = volume / maxVolume;
    
    if (intensity <= 0.25) return const Color(0xFFC6E48B); // Light green
    if (intensity <= 0.50) return const Color(0xFF7BC96F); // Medium green
    if (intensity <= 0.75) return const Color(0xFF239A3B); // Dark green
    return const Color(0xFF196127); // Darkest green
  }

  DayActivity? _getActivityForDate(Map<DateTime, DayActivity> map, DateTime date) {
    for (final entry in map.entries) {
      final d = entry.key;
      if (d.year == date.year && d.month == date.month && d.day == date.day) {
        return entry.value;
      }
    }
    return null;
  }

  Widget _buildActivityLegend(double maxVolume) {
    return Row(
      mainAxisAlignment: MainAxisAlignment.center,
      children: [
        const Text(
          'Less',
          style: TextStyle(fontSize: 10, color: AppColors.textSecondary),
        ),
        const SizedBox(width: 4),
        _legendBox(const Color(0xFFEBEDF0)),
        const SizedBox(width: 2),
        _legendBox(const Color(0xFFC6E48B)),
        const SizedBox(width: 2),
        _legendBox(const Color(0xFF7BC96F)),
        const SizedBox(width: 2),
        _legendBox(const Color(0xFF239A3B)),
        const SizedBox(width: 2),
        _legendBox(const Color(0xFF196127)),
        const SizedBox(width: 4),
        const Text(
          'More',
          style: TextStyle(fontSize: 10, color: AppColors.textSecondary),
        ),
      ],
    );
  }

  Widget _legendBox(Color color) {
    return Container(
      width: 10,
      height: 10,
      decoration: BoxDecoration(
        color: color,
        borderRadius: BorderRadius.circular(2),
      ),
    );
  }

  Widget _buildCompletedWorkouts(BuildContext context, WidgetRef ref) {
    final sessionsAsync = ref.watch(completedSessionsProvider);
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 24),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Row(
            children: [
              Icon(Icons.calendar_today, color: AppColors.primary, size: 24),
              SizedBox(width: 8),
              Text(
                'Completed Workouts',
                style: TextStyle(
                  fontSize: 20,
                  fontWeight: FontWeight.bold,
                  color: AppColors.textPrimary,
                ),
              ),
            ],
          ),
          const SizedBox(height: 16),
          sessionsAsync.when(
            loading: () => const Center(child: CircularProgressIndicator()),
            error: (error, _) => Text('Ошибка загрузки списка: $error'),
            data: (sessions) => Column(
              children: sessions.map((s) => _buildWorkoutCard(context, s)).toList(),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildWorkoutCard(BuildContext context, WorkoutSession session) {
    final dateFormat = DateFormat('MMM dd');
    final workoutCode = 'WO${session.workoutId}';

    return Container(
      margin: const EdgeInsets.only(bottom: 12),
      decoration: BoxDecoration(
        color: AppColors.surface,
        borderRadius: BorderRadius.circular(12),
        boxShadow: AppShadows.sm,
      ),
      child: Material(
        color: Colors.transparent,
        borderRadius: BorderRadius.circular(12),
        child: InkWell(
          borderRadius: BorderRadius.circular(12),
          onTap: () {
            Navigator.of(context).push(
              MaterialPageRoute(
                builder: (_) => SessionLogScreen(session: session),
              ),
            );
          },
          child: Padding(
            padding: const EdgeInsets.all(16),
            child: Row(
              children: [
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                  decoration: BoxDecoration(
                    color: AppColors.success,
                    borderRadius: BorderRadius.circular(20),
                  ),
                  child: Text(
                    workoutCode,
                    style: const TextStyle(
                      color: Colors.white,
                      fontSize: 12,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                ),
                const SizedBox(width: 16),
                Text(
                  dateFormat.format(session.startedAt),
                  style: const TextStyle(
                    fontSize: 14,
                    color: AppColors.textSecondary,
                  ),
                ),
                const Spacer(),
                const Icon(
                  Icons.check_circle,
                  color: AppColors.success,
                  size: 24,
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
