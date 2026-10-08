import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:firebase_auth/firebase_auth.dart';
import 'dart:math' as math;
import 'package:intl/intl.dart';
import 'package:workout_app/l10n/app_localizations.dart';
import 'package:workout_app/config/constants/theme_constants.dart';
import 'package:workout_app/models/plan_analytics.dart';
import 'package:workout_app/models/workout.dart';
import 'package:workout_app/models/workout_session.dart';
import 'package:workout_app/models/user_profile.dart';
import 'package:workout_app/providers/providers.dart';
import 'package:workout_app/services/service_locator.dart' as sl;
import 'package:workout_app/services/workout_service.dart';
import 'package:workout_app/services/avatar_service.dart';
import 'package:workout_app/screens/session_log_screen.dart';
import 'package:workout_app/config/constants/route_names.dart';
import 'dart:typed_data';
import 'package:workout_app/widgets/floating_header_bar.dart';
import 'package:workout_app/widgets/assistant_chat_host.dart';
import 'package:workout_app/widgets/plan_analytics_chart.dart';
import 'package:workout_app/providers/profile_screen_sections_provider.dart';
import '../widgets/user_profile_view.dart';

const int kActivityWeeks = 48;
const int kProfileAnalyticsDays = 3650;
const int kProfileAnalyticsDaysDefault = 365;

final avatarPromptProvider = StateProvider<String>((ref) => '');
final avatarImageProvider = StateProvider<Uint8List?>((ref) => null);
final avatarLoadingProvider = StateProvider<bool>((ref) => false);

final _profileAnalyticsLayersProvider = StateProvider<List<String>>(
  (ref) => const [],
);

final profileWorkoutHistoryAnalyticsProvider =
    FutureProvider<PlanAnalyticsResponse?>((ref) async {
      final analytics = ref.watch(sl.analyticsServiceProvider);
      final layers = ref.watch(_profileAnalyticsLayersProvider);
      final sectionPrefs = ref.watch(profileScreenSectionsProvider);
      final days = sectionPrefs.workoutAnalyticsShowAllTime
          ? kProfileAnalyticsDays
          : kProfileAnalyticsDaysDefault;
      return await analytics.getWorkoutHistoryAnalytics(
        days: days,
        layers: layers,
        includeMeta: true,
        topLayersLimit: 50,
      );
    });

final profileAggregatesProvider = FutureProvider<UserStats>((ref) async {
  final analytics = ref.watch(sl.analyticsServiceProvider);
  final data = await analytics.getProfileAggregates(
    weeks: kActivityWeeks,
    limit: 20,
  );

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

  const DayActivity({required this.sessionCount, required this.volume});
}

Future<Map<String, dynamic>> _buildProfileChatContext() async {
  final nowIso = DateTime.now().toUtc().toIso8601String();
  return <String, dynamic>{
    'v': 1,
    'app': 'WorkoutApp',
    'screen': 'user_profile',
    'role': 'athlete',
    'timestamp': nowIso,
    'entities': <String, dynamic>{},
  };
}

Future<UserStats> _calculateStats(
  WorkoutService workoutService,
  List<WorkoutSession> sessions,
) async {
  final completedSessions = sessions
      .where(
        (s) => s.status.toLowerCase() == 'completed' || s.finishedAt != null,
      )
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
    final day = DateTime(
      startedLocal.year,
      startedLocal.month,
      startedLocal.day,
    );
    uniqueActiveDays.add(day);
    if (!startedLocal.isBefore(gridStart) && !startedLocal.isAfter(gridEnd)) {
      recentSessions.add(session);
    }
  }

  final workoutCache = <int, Workout?>{};
  final setVolumeCache = <int, Map<int, double>>{};
  final uniqueWorkoutIds = recentSessions
      .map((s) => s.workoutId)
      .toSet()
      .toList();

  await Future.wait(
    uniqueWorkoutIds.map((id) async {
      try {
        final workout = await workoutService.getWorkoutWithDetails(id);
        workoutCache[id] = workout;
        setVolumeCache[id] = _buildSetVolumeLookup(workout);
      } catch (_) {
        workoutCache[id] = null;
        setVolumeCache[id] = <int, double>{};
      }
    }),
  );

  final dayVolumes = <DateTime, double>{};
  final dayCounts = <DateTime, int>{};
  double totalVolume = 0;

  for (final session in recentSessions) {
    final startedLocal = session.startedAt.toLocal();
    final day = DateTime(
      startedLocal.year,
      startedLocal.month,
      startedLocal.day,
    );
    final completedSetIds = _extractCompletedSetIds(session.progress);
    double sessionVolume = 0;

    final workout = workoutCache[session.workoutId];
    if (workout != null) {
      final setLookup =
          setVolumeCache[session.workoutId] ?? const <int, double>{};
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
    final l10n = AppLocalizations.of(context);
    final user = FirebaseAuth.instance.currentUser;
    final profileAsync = ref.watch(userProfileProvider);

    return AssistantChatHost(
      contextBuilder: _buildProfileChatContext,
      builder: (hostContext, openChat) {
        return Scaffold(
          backgroundColor: AppColors.background,
          body: Stack(
            children: [
              SafeArea(
                bottom: false,
                child: Stack(
                  children: [
                    RefreshIndicator(
                      onRefresh: () async {
                        try {
                          _invalidateAllProfileProviders(ref);
                          await Future.wait([
                            ref.read(userProfileProvider.future),
                            ref.read(profileAggregatesProvider.future),
                            ref.read(completedSessionsProvider.future),
                            ref.read(
                              profileWorkoutHistoryAnalyticsProvider.future,
                            ),
                          ]);
                        } catch (e) {
                          // RefreshIndicator will handle the error display
                          rethrow;
                        }
                      },
                      child: profileAsync.when(
                        loading: () =>
                            const Center(child: CircularProgressIndicator()),
                        error: (error, _) => _buildErrorState(ref, error),
                        data: (profile) {
                          return ref
                              .watch(profileAggregatesProvider)
                              .when(
                                loading: () => const Center(
                                  child: CircularProgressIndicator(),
                                ),
                                error: (error, _) =>
                                    _buildErrorState(ref, error),
                                data: (stats) => _buildContent(
                                  hostContext,
                                  ref,
                                  stats,
                                  user,
                                  profile,
                                ),
                              );
                        },
                      ),
                    ),
                    Align(
                      alignment: Alignment.topCenter,
                      child: FloatingHeaderBar(
                        title: l10n.accountTitle,
                        leading: IconButton(
                          icon: const Icon(
                            Icons.arrow_back,
                            color: AppColors.textPrimary,
                          ),
                          onPressed: () => Navigator.of(hostContext).maybePop(),
                        ),
                        actions: [
                          IconButton(
                            icon: const Icon(Icons.settings),
                            onPressed: () => Navigator.of(
                              hostContext,
                            ).pushNamed(RouteNames.settings),
                          ),
                        ],
                        onTitleTap: openChat,
                        onProfileTap: null,
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ),
        );
      },
    );
  }

  Widget _buildStatsRow(UserStats stats) {
    return Row(
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
    );
  }

  Future<void> _showEditProfileDialog(
    BuildContext context,
    WidgetRef ref,
    User? user,
    UserProfile profile,
  ) async {
    final nameController = TextEditingController(
      text: profile.displayName ?? user?.displayName ?? '',
    );
    final bioController = TextEditingController(text: profile.bio ?? '');

    final bodyweightController = TextEditingController(
      text: profile.bodyweightKg != null
          ? profile.bodyweightKg!.toStringAsFixed(1)
          : '',
    );
    final heightController = TextEditingController(
      text: profile.heightCm != null
          ? profile.heightCm!.toStringAsFixed(0)
          : '',
    );
    final ageController = TextEditingController(
      text: profile.age != null ? profile.age!.toString() : '',
    );
    final experienceYearsController = TextEditingController(
      text: profile.trainingExperienceYears != null
          ? profile.trainingExperienceYears!.toStringAsFixed(1)
          : '',
    );

    String? sex = profile.sex;
    String? experienceLevel = profile.trainingExperienceLevel;
    String? primaryGoal = profile.primaryDefaultGoal;
    String? trainingEnvironment = profile.trainingEnvironment;

    final result = await showDialog<bool>(
      context: context,
      builder: (ctx) {
        return StatefulBuilder(
          builder: (ctx, setState) {
            final l10n = AppLocalizations.of(ctx);
            return AlertDialog(
              title: Text(l10n.editProfileTitle),
              content: SingleChildScrollView(
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    TextField(
                      controller: nameController,
                      decoration: InputDecoration(labelText: l10n.displayName),
                    ),
                    TextField(
                      controller: bioController,
                      decoration: InputDecoration(labelText: l10n.bio),
                      maxLines: 3,
                    ),
                    const SizedBox(height: 12),

                    Row(
                      children: [
                        Expanded(
                          child: TextField(
                            controller: bodyweightController,
                            keyboardType: const TextInputType.numberWithOptions(
                              decimal: true,
                            ),
                            decoration: InputDecoration(
                              labelText: l10n.bodyweightKg,
                            ),
                          ),
                        ),
                        const SizedBox(width: 12),
                        Expanded(
                          child: TextField(
                            controller: heightController,
                            keyboardType: const TextInputType.numberWithOptions(
                              decimal: false,
                            ),
                            decoration: InputDecoration(
                              labelText: l10n.heightCm,
                            ),
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 8),
                    Row(
                      children: [
                        Expanded(
                          child: TextField(
                            controller: ageController,
                            keyboardType: const TextInputType.numberWithOptions(
                              decimal: false,
                            ),
                            decoration: InputDecoration(labelText: l10n.age),
                          ),
                        ),
                        const SizedBox(width: 12),
                        Expanded(
                          child: TextField(
                            controller: experienceYearsController,
                            keyboardType: const TextInputType.numberWithOptions(
                              decimal: true,
                            ),
                            decoration: InputDecoration(
                              labelText: l10n.trainingYears,
                            ),
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 8),
                    Row(
                      children: [
                        Expanded(
                          child: DropdownButtonFormField<String>(
                            value: sex,
                            decoration: const InputDecoration(labelText: 'Sex'),
                            items: const [
                              DropdownMenuItem(
                                value: 'male',
                                child: Text('Male'),
                              ),
                              DropdownMenuItem(
                                value: 'female',
                                child: Text('Female'),
                              ),
                            ],
                            onChanged: (value) {
                              setState(() => sex = value);
                            },
                          ),
                        ),
                        const SizedBox(width: 12),
                        Expanded(
                          child: DropdownButtonFormField<String>(
                            value: experienceLevel,
                            decoration: const InputDecoration(
                              labelText: 'Experience level',
                            ),
                            items: const [
                              DropdownMenuItem(
                                value: 'beginner',
                                child: Text('Beginner'),
                              ),
                              DropdownMenuItem(
                                value: 'intermediate',
                                child: Text('Intermediate'),
                              ),
                              DropdownMenuItem(
                                value: 'advanced',
                                child: Text('Advanced'),
                              ),
                            ],
                            onChanged: (value) {
                              setState(() => experienceLevel = value);
                            },
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 8),
                    DropdownButtonFormField<String>(
                      value: primaryGoal,
                      decoration: const InputDecoration(
                        labelText: 'Primary goal',
                      ),
                      items: const [
                        DropdownMenuItem(
                          value: 'strength',
                          child: Text('Strength'),
                        ),
                        DropdownMenuItem(
                          value: 'hypertrophy',
                          child: Text('Hypertrophy'),
                        ),
                        DropdownMenuItem(
                          value: 'fat_loss',
                          child: Text('Fat loss'),
                        ),
                        DropdownMenuItem(
                          value: 'general_fitness',
                          child: Text('General fitness'),
                        ),
                      ],
                      onChanged: (value) {
                        setState(() => primaryGoal = value);
                      },
                    ),
                    const SizedBox(height: 8),
                    DropdownButtonFormField<String>(
                      value: trainingEnvironment,
                      decoration: const InputDecoration(
                        labelText: 'Training environment',
                      ),
                      items: const [
                        DropdownMenuItem(
                          value: 'commercial_gym',
                          child: Text('Commercial gym'),
                        ),
                        DropdownMenuItem(value: 'home', child: Text('Home')),
                        DropdownMenuItem(
                          value: 'garage',
                          child: Text('Garage'),
                        ),
                      ],
                      onChanged: (value) {
                        setState(() => trainingEnvironment = value);
                      },
                    ),
                  ],
                ),
              ),
              actions: [
                TextButton(
                  onPressed: () => Navigator.of(ctx).pop(false),
                  child: Text(l10n.cancel),
                ),
                ElevatedButton(
                  onPressed: () => Navigator.of(ctx).pop(true),
                  child: Text(l10n.save),
                ),
              ],
            );
          },
        );
      },
    );

    if (result != true) return;

    final displayName = nameController.text.trim();
    final bio = bioController.text.trim();

    double? _parseDouble(String text) {
      if (text.trim().isEmpty) return null;
      return double.tryParse(text.replaceAll(',', '.'));
    }

    int? _parseInt(String text) {
      if (text.trim().isEmpty) return null;
      return int.tryParse(text);
    }

    try {
      final svc = ref.read(sl.profileServiceProvider);
      await svc.updateProfile(
        displayName: displayName.isEmpty ? null : displayName,
        bio: bio.isEmpty ? null : bio,
        bodyweightKg: _parseDouble(bodyweightController.text),
        heightCm: _parseDouble(heightController.text),
        age: _parseInt(ageController.text),
        sex: sex,
        trainingExperienceYears: _parseDouble(experienceYearsController.text),
        trainingExperienceLevel: experienceLevel,
        primaryDefaultGoal: primaryGoal,
        trainingEnvironment: trainingEnvironment,
      );
      ref.invalidate(userProfileProvider);
      if (context.mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text(AppLocalizations.of(context).profileUpdated)),
        );
      }
    } catch (e) {
      if (context.mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(
              '${AppLocalizations.of(context).failedToUpdateProfile}: $e',
            ),
          ),
        );
      }
    }
  }

  void _invalidateAllProfileProviders(WidgetRef ref) {
    ref.invalidate(userProfileProvider);
    ref.invalidate(profileAggregatesProvider);
    ref.invalidate(completedSessionsProvider);
    ref.invalidate(profileWorkoutHistoryAnalyticsProvider);
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
            onPressed: () => _invalidateAllProfileProviders(ref),
            child: const Text('Повторить'),
          ),
        ],
      ),
    );
  }

  Widget _buildContent(
    BuildContext context,
    WidgetRef ref,
    UserStats stats,
    User? user,
    UserProfile profile,
  ) {
    final sectionPrefs = ref.watch(profileScreenSectionsProvider);

    void openAvatarTool() {
      showModalBottomSheet<void>(
        context: context,
        isScrollControlled: true,
        showDragHandle: true,
        builder: (ctx) {
          return SafeArea(
            child: Padding(
              padding: EdgeInsets.only(
                left: 16,
                right: 16,
                top: 16,
                bottom: MediaQuery.of(ctx).viewInsets.bottom + 16,
              ),
              child: SingleChildScrollView(
                child: _buildAvatarGenerator(ctx, ref),
              ),
            ),
          );
        },
      );
    }

    return SingleChildScrollView(
      physics: const AlwaysScrollableScrollPhysics(),
      child: Column(
        children: [
          const SizedBox(height: kToolbarHeight + 24),
          Center(
            child: ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 720),
              child: Padding(
                padding: const EdgeInsets.symmetric(horizontal: 24),
                child: UserProfileView(
                  profile: profile,
                  isOwner: true,
                  subtitle: '',
                  avatarUrlOverride: user?.photoURL,
                  onEditProfile: () =>
                      _showEditProfileDialog(context, ref, user, profile),
                  onManageCoaching: null,
                  onAvatarTool: openAvatarTool,
                  showCoachingCard: false,
                  additionalSections: [
                    const SizedBox(height: 16),
                    Text(
                      user?.email ?? '',
                      textAlign: TextAlign.center,
                      style: const TextStyle(
                        fontSize: 14,
                        color: AppColors.textSecondary,
                      ),
                    ),
                    const SizedBox(height: 4),
                    Text(
                      'Member since ${user?.metadata.creationTime != null ? DateFormat('yyyy').format(user!.metadata.creationTime!) : DateFormat('yyyy').format(DateTime.now())}',
                      textAlign: TextAlign.center,
                      style: const TextStyle(
                        fontSize: 14,
                        color: AppColors.textSecondary,
                      ),
                    ),
                    const SizedBox(height: 24),
                    Center(
                      child: ConstrainedBox(
                        constraints: const BoxConstraints(maxWidth: 520),
                        child: _buildStatsRow(stats),
                      ),
                    ),
                    if (sectionPrefs.showWorkoutAnalytics) ...[
                      const SizedBox(height: 24),
                      const _UserHistoryAnalyticsSection(),
                    ],
                  ],
                ),
              ),
            ),
          ),
          const SizedBox(height: 24),
          if (sectionPrefs.showActivityChart) ...[
            Center(
              child: ConstrainedBox(
                constraints: const BoxConstraints(maxWidth: 720),
                child: Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 24),
                  child: _buildActivitySection(stats),
                ),
              ),
            ),
            const SizedBox(height: 32),
          ],
          if (sectionPrefs.showWorkoutHistory) ...[
            Center(
              child: ConstrainedBox(
                constraints: const BoxConstraints(maxWidth: 720),
                child: Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 24),
                  child: _buildCompletedWorkouts(context, ref),
                ),
              ),
            ),
            const SizedBox(height: 32),
          ],
        ],
      ),
    );
  }

  Widget _buildAvatarGenerator(BuildContext context, WidgetRef ref) {
    final loading = ref.watch(avatarLoadingProvider);
    final imageBytes = ref.watch(avatarImageProvider);
    final prompt = ref.watch(avatarPromptProvider);

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Row(
          children: [
            Icon(Icons.edit, color: AppColors.primary, size: 20),
            SizedBox(width: 8),
            Text(
              'Generate your Avatar',
              style: TextStyle(
                fontSize: 18,
                fontWeight: FontWeight.w600,
                color: AppColors.textPrimary,
              ),
            ),
          ],
        ),
        const SizedBox(height: 8),
        const Text(
          'Use fofr/sdxl-emoji to create something unique.',
          style: TextStyle(fontSize: 12, color: AppColors.textSecondary),
        ),
        const SizedBox(height: 12),
        if (imageBytes != null)
          Center(
            child: Container(
              width: 96,
              height: 96,
              decoration: const BoxDecoration(shape: BoxShape.circle),
              clipBehavior: Clip.antiAlias,
              child: Image.memory(imageBytes, fit: BoxFit.cover),
            ),
          ),
        if (imageBytes != null) const SizedBox(height: 8),
        if (imageBytes != null)
          Center(
            child: TextButton.icon(
              onPressed: loading
                  ? null
                  : () async {
                      try {
                        final svc = ref.read(sl.avatarServiceProvider);
                        final url = await svc.applyAsProfile(
                          pngBytes: imageBytes,
                        );
                        try {
                          await FirebaseAuth.instance.currentUser?.reload();
                        } catch (_) {}
                        ref.invalidate(profileAggregatesProvider);
                        if (context.mounted) {
                          ScaffoldMessenger.of(context).showSnackBar(
                            SnackBar(
                              content: Text(
                                url.isNotEmpty
                                    ? 'Profile photo updated'
                                    : 'Saved avatar',
                              ),
                            ),
                          );
                        }
                      } catch (e) {
                        if (context.mounted) {
                          ScaffoldMessenger.of(context).showSnackBar(
                            SnackBar(content: Text('Failed to apply: $e')),
                          );
                        }
                      }
                    },
              icon: const Icon(Icons.check_circle_outline),
              label: const Text('Use as profile picture'),
            ),
          ),
        if (imageBytes != null) const SizedBox(height: 12),
        Row(
          children: [
            Expanded(
              child: TextFormField(
                initialValue: prompt,
                onChanged: (v) =>
                    ref.read(avatarPromptProvider.notifier).state = v,
                decoration: InputDecoration(
                  prefixIcon: const Icon(Icons.casino_outlined),
                  hintText: 'Describe your avatar',
                  contentPadding: const EdgeInsets.symmetric(
                    horizontal: 12,
                    vertical: 12,
                  ),
                  filled: true,
                  fillColor: AppColors.surface,
                  border: OutlineInputBorder(
                    borderRadius: BorderRadius.circular(12),
                    borderSide: BorderSide.none,
                  ),
                ),
              ),
            ),
            const SizedBox(width: 8),
            SizedBox(
              height: 44,
              child: ElevatedButton(
                onPressed: loading
                    ? null
                    : () async {
                        final text = ref.read(avatarPromptProvider);
                        if (text.trim().isEmpty) return;
                        ref.read(avatarLoadingProvider.notifier).state = true;
                        try {
                          final svc = ref.read(sl.avatarServiceProvider);
                          final bytes = await svc.generateAvatar(prompt: text);
                          ref.read(avatarImageProvider.notifier).state = bytes;
                        } catch (e) {
                          if (context.mounted) {
                            ScaffoldMessenger.of(context).showSnackBar(
                              SnackBar(content: Text('Failed: $e')),
                            );
                          }
                        } finally {
                          ref.read(avatarLoadingProvider.notifier).state =
                              false;
                        }
                      },
                style: ElevatedButton.styleFrom(
                  backgroundColor: AppColors.textPrimary,
                  foregroundColor: Colors.white,
                  shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(12),
                  ),
                  padding: const EdgeInsets.symmetric(horizontal: 16),
                ),
                child: loading
                    ? const SizedBox(
                        width: 20,
                        height: 20,
                        child: CircularProgressIndicator(
                          strokeWidth: 2,
                          color: Colors.white,
                        ),
                      )
                    : const Text('Generate'),
              ),
            ),
          ],
        ),
        const SizedBox(height: 6),
        const Text(
          'Randomize or write your own prompt! Your avatar will be displayed on your public profile.',
          style: TextStyle(fontSize: 11, color: AppColors.textSecondary),
        ),
      ],
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
    return Column(
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
    );
  }

  Widget _buildActivityGrid(
    Map<DateTime, DayActivity> activityMap,
    double maxVolume,
  ) {
    final today = DateTime.now();
    final endDate = DateTime(today.year, today.month, today.day);

    final endWeekStart = endDate.subtract(Duration(days: endDate.weekday - 1));
    final startWeekStart = endWeekStart.subtract(
      Duration(days: (kActivityWeeks - 1) * 7),
    );

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
                  width: 12,
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
                    child: Builder(
                      builder: (_) {
                        final normalized = DateTime(
                          date.year,
                          date.month,
                          date.day,
                        );
                        final dayActivity = _getActivityForDate(
                          activityMap,
                          normalized,
                        );
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
                      },
                    ),
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

    if (intensity <= 0.25) return const Color(0xFFC6E48B);
    if (intensity <= 0.50) return const Color(0xFF7BC96F);
    if (intensity <= 0.75) return const Color(0xFF239A3B);
    return const Color(0xFF196127);
  }

  DayActivity? _getActivityForDate(
    Map<DateTime, DayActivity> map,
    DateTime date,
  ) {
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
    return Column(
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
            children: sessions
                .map((s) => _buildWorkoutCard(context, s))
                .toList(),
          ),
        ),
      ],
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
                  padding: const EdgeInsets.symmetric(
                    horizontal: 12,
                    vertical: 6,
                  ),
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

class _ProfileAnalyticsSeriesConfig {
  final int id;
  final String metric;
  final Set<int> exerciseIds;
  final Set<String> muscles;

  const _ProfileAnalyticsSeriesConfig({
    required this.id,
    required this.metric,
    this.exerciseIds = const <int>{},
    this.muscles = const <String>{},
  });

  bool get isAll => exerciseIds.isEmpty && muscles.isEmpty;
}

class _UserHistoryAnalyticsSection extends ConsumerStatefulWidget {
  const _UserHistoryAnalyticsSection();

  @override
  ConsumerState<_UserHistoryAnalyticsSection> createState() =>
      _UserHistoryAnalyticsSectionState();
}

class _UserHistoryAnalyticsSectionState
    extends ConsumerState<_UserHistoryAnalyticsSection> {
  final List<String> _metrics = const [
    'sets_count',
    'volume_sum',
    'reps_per_set_avg',
    'kilograms_avg',
    'tonnage_sum',
    'one_rm_est_avg',
    'intensity_avg',
    'effort_avg',
  ];

  final List<_ProfileAnalyticsSeriesConfig> _seriesConfigs =
      <_ProfileAnalyticsSeriesConfig>[];
  int _nextSeriesId = 1;

  void _ensureDefaultSeries() {
    if (_seriesConfigs.isNotEmpty) return;
    _seriesConfigs.add(
      _ProfileAnalyticsSeriesConfig(id: _nextSeriesId, metric: 'effort_avg'),
    );
    _nextSeriesId += 1;
  }

  String _seriesMetricKey(int id) => 'series:$id';

  bool _isAvgMetric(String m) =>
      m == 'effort_avg' ||
      m == 'intensity_avg' ||
      m == 'reps_per_set_avg' ||
      m == 'kilograms_avg' ||
      m == 'one_rm_est_avg';

  List<String> _requestedLayersForSeries() {
    final out = <String>[];
    final seen = <String>{};
    for (final s in _seriesConfigs) {
      for (final id in s.exerciseIds) {
        final k = 'exercise:$id';
        if (seen.add(k)) out.add(k);
      }
      for (final m in s.muscles) {
        final k = 'muscle:$m';
        if (seen.add(k)) out.add(k);
      }
    }
    return out;
  }

  void _syncAnalyticsLayers() {
    final layers = _requestedLayersForSeries();
    ref.read(_profileAnalyticsLayersProvider.notifier).state =
        List.unmodifiable(layers);
    ref.invalidate(profileWorkoutHistoryAnalyticsProvider);
  }

  String _metricLabel(String m) {
    final l10n = AppLocalizations.of(context);
    switch (m) {
      case 'sets_count':
        return l10n.coachAthletePlanMetricSets;
      case 'volume_sum':
        return 'КПШ';
      case 'reps_per_set_avg':
        return 'Повт. в подходе (ср.)';
      case 'kilograms_avg':
        return 'Килограммы (ср.)';
      case 'tonnage_sum':
        return 'Тоннаж';
      case 'one_rm_est_avg':
        return 'Разовый максимум (расч.)';
      case 'intensity_avg':
        return l10n.coachAthletePlanMetricIntensity;
      case 'effort_avg':
        return l10n.coachAthletePlanMetricEffort;
      default:
        return m;
    }
  }

  List<int> _availableExerciseIdsFromMeta(Map<String, dynamic>? meta) {
    final ids = <int>{};
    final labels = meta?['exercise_labels'];
    if (labels is Map) {
      for (final k in labels.keys) {
        if (k is int) {
          ids.add(k);
        } else if (k is String) {
          final id = int.tryParse(k);
          if (id != null) ids.add(id);
        }
      }
    }
    final out = ids.toList()..sort();
    return out;
  }

  List<String> _availableMusclesFromMeta(Map<String, dynamic>? meta) {
    final names = <String>{};
    final direct = meta?['available_muscles'];
    if (direct is List) {
      for (final m in direct) {
        final s = m?.toString().trim();
        if (s != null && s.isNotEmpty) names.add(s);
      }
    }
    final out = names.toList()..sort();
    return out;
  }

  String _layerKeyLabel(String layerKey, Map<String, dynamic>? meta) {
    final idx = layerKey.indexOf(':');
    if (idx <= 0 || idx >= layerKey.length - 1) {
      return layerKey;
    }
    final kind = layerKey.substring(0, idx);
    final raw = layerKey.substring(idx + 1);

    String titleCase(String s) {
      final cleaned = s.replaceAll('_', ' ').trim();
      final parts = cleaned.split(RegExp(r'\s+')).where((p) => p.isNotEmpty);
      return parts
          .map((p) => p.isEmpty ? p : '${p[0].toUpperCase()}${p.substring(1)}')
          .join(' ');
    }

    if (kind == 'exercise') {
      final labels = meta?['exercise_labels'];
      if (labels is Map) {
        final byString = labels[raw];
        if (byString is String && byString.trim().isNotEmpty) {
          return byString.trim();
        }
        final id = int.tryParse(raw);
        if (id != null) {
          final byInt = labels[id];
          if (byInt is String && byInt.trim().isNotEmpty) {
            return byInt.trim();
          }
        }
      }
      return 'Exercise #$raw';
    }

    if (kind == 'muscle') {
      return 'Muscle: ${titleCase(raw)}';
    }

    if (kind == 'muscle_group') {
      return 'Group: ${titleCase(raw)}';
    }

    return '${titleCase(kind)}: ${titleCase(raw)}';
  }

  String _seriesLabel(
    _ProfileAnalyticsSeriesConfig s,
    Map<String, dynamic>? meta,
  ) {
    final metricLabel = _metricLabel(s.metric);
    if (s.isAll) {
      return 'All · $metricLabel';
    }

    final parts = <String>[];
    if (s.exerciseIds.isNotEmpty) {
      if (s.exerciseIds.length == 1) {
        parts.add(_layerKeyLabel('exercise:${s.exerciseIds.first}', meta));
      } else {
        parts.add('${s.exerciseIds.length} exercises');
      }
    }
    if (s.muscles.isNotEmpty) {
      if (s.muscles.length == 1) {
        parts.add(_layerKeyLabel('muscle:${s.muscles.first}', meta));
      } else {
        parts.add('${s.muscles.length} muscles');
      }
    }
    return '${parts.join(' + ')} · $metricLabel';
  }

  double _computeSeriesPointValue(
    _ProfileAnalyticsSeriesConfig s,
    Map<String, double> values,
  ) {
    if (s.isAll) {
      return values[s.metric] ?? 0.0;
    }

    final layerIds = <String>[];
    for (final id in s.exerciseIds) {
      layerIds.add('exercise:$id');
    }
    for (final m in s.muscles) {
      layerIds.add('muscle:$m');
    }
    if (layerIds.isEmpty) return values[s.metric] ?? 0.0;

    if (_isAvgMetric(s.metric)) {
      double wSum = 0.0;
      double vSum = 0.0;
      for (final layerId in layerIds) {
        final v = values['layer:$layerId:${s.metric}'];
        if (v == null || v == 0.0) continue;
        final wRaw = values['layer:$layerId:sets_count'];
        final w = (wRaw != null && wRaw > 0) ? wRaw : 1.0;
        vSum += v * w;
        wSum += w;
      }
      return wSum > 0 ? (vSum / wSum) : 0.0;
    }

    double total = 0.0;
    for (final layerId in layerIds) {
      total += values['layer:$layerId:${s.metric}'] ?? 0.0;
    }
    return total;
  }

  List<PlanAnalyticsPoint> _mapAnalyticsResponse(PlanAnalyticsResponse? resp) {
    if (resp == null) return const [];
    final items = List.of(resp.items);
    items.sort((a, b) {
      final ad = a.date?.toLocal();
      final bd = b.date?.toLocal();
      if (ad != null && bd != null) {
        final cmp = ad.compareTo(bd);
        if (cmp != 0) return cmp;
      }
      final ao = a.orderIndex ?? 1 << 30;
      final bo = b.orderIndex ?? 1 << 30;
      if (ao != bo) return ao.compareTo(bo);
      return a.workoutId.compareTo(b.workoutId);
    });
    int order = 0;
    return items
        .map((item) {
          final label = item.date != null
              ? DateFormat('MMM d').format(item.date!.toLocal())
              : (item.orderIndex != null
                    ? 'Day ${item.orderIndex}'
                    : '#${order + 1}');
          return PlanAnalyticsPoint(
            order: order++,
            label: label,
            values: item.metrics,
            actualValues: null,
          );
        })
        .toList(growable: false);
  }

  Future<void> _openSeriesEditor(
    PlanAnalyticsResponse? resp, {
    _ProfileAnalyticsSeriesConfig? initial,
  }) async {
    final meta = resp?.meta is Map<String, dynamic>
        ? (resp!.meta as Map<String, dynamic>)
        : null;
    final initialMetric = initial?.metric ?? 'volume_sum';
    final initialExerciseIds = Set<int>.from(
      initial?.exerciseIds ?? const <int>{},
    );
    final initialMuscles = Set<String>.from(
      initial?.muscles ?? const <String>{},
    );

    final allExerciseIds = _availableExerciseIdsFromMeta(meta);
    final allMuscles = _availableMusclesFromMeta(meta);

    await showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      showDragHandle: true,
      builder: (ctx) {
        var metric = initialMetric;
        final selectedExerciseIds = initialExerciseIds;
        final selectedMuscles = initialMuscles;

        return StatefulBuilder(
          builder: (ctx2, setStateDialog) {
            Widget buildMultiSelect<T>({
              required String title,
              required List<T> options,
              required Set<T> selected,
              required String Function(T) labelOf,
            }) {
              return Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const SizedBox(height: 10),
                  Text(
                    title,
                    style: const TextStyle(fontWeight: FontWeight.w600),
                  ),
                  const SizedBox(height: 6),
                  if (options.isEmpty)
                    const Text(
                      'Нет опций',
                      style: TextStyle(color: Colors.black54),
                    )
                  else
                    SizedBox(
                      height: 220,
                      child: ListView(
                        children: options.map((o) {
                          final checked = selected.contains(o);
                          return CheckboxListTile(
                            dense: true,
                            value: checked,
                            title: Text(labelOf(o)),
                            onChanged: (v) {
                              if (v == null) return;
                              setStateDialog(() {
                                if (v) {
                                  selected.add(o);
                                } else {
                                  selected.remove(o);
                                }
                              });
                            },
                          );
                        }).toList(),
                      ),
                    ),
                ],
              );
            }

            return Padding(
              padding: EdgeInsets.only(
                left: 16,
                right: 16,
                top: 6,
                bottom: 16 + MediaQuery.of(ctx2).viewInsets.bottom,
              ),
              child: SingleChildScrollView(
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    Text(
                      initial == null ? 'Add series' : 'Edit series',
                      style: const TextStyle(
                        fontSize: 16,
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                    const SizedBox(height: 12),
                    DropdownButtonFormField<String>(
                      value: metric,
                      decoration: const InputDecoration(labelText: 'Ось Y'),
                      items: _metrics
                          .map(
                            (m) => DropdownMenuItem<String>(
                              value: m,
                              child: Text(_metricLabel(m)),
                            ),
                          )
                          .toList(growable: false),
                      onChanged: (v) {
                        if (v == null) return;
                        setStateDialog(() => metric = v);
                      },
                    ),
                    buildMultiSelect<int>(
                      title: 'Упражнения',
                      options: allExerciseIds,
                      selected: selectedExerciseIds,
                      labelOf: (id) => _layerKeyLabel('exercise:$id', meta),
                    ),
                    buildMultiSelect<String>(
                      title: 'Мышцы',
                      options: allMuscles,
                      selected: selectedMuscles,
                      labelOf: (m) => _layerKeyLabel('muscle:$m', meta),
                    ),
                    const SizedBox(height: 10),
                    Row(
                      children: [
                        Expanded(
                          child: TextButton(
                            onPressed: () => Navigator.of(ctx2).pop(),
                            child: const Text('Cancel'),
                          ),
                        ),
                        Expanded(
                          child: FilledButton(
                            onPressed: () {
                              final normalized = _ProfileAnalyticsSeriesConfig(
                                id: initial?.id ?? _nextSeriesId,
                                metric: metric,
                                exerciseIds: Set<int>.from(selectedExerciseIds),
                                muscles: Set<String>.from(selectedMuscles),
                              );

                              setState(() {
                                if (initial == null) {
                                  _seriesConfigs.add(normalized);
                                  _nextSeriesId += 1;
                                } else {
                                  final idx = _seriesConfigs.indexWhere(
                                    (e) => e.id == initial.id,
                                  );
                                  if (idx >= 0) {
                                    _seriesConfigs[idx] = normalized;
                                  }
                                }
                              });

                              _syncAnalyticsLayers();
                              Navigator.of(ctx2).pop();
                            },
                            child: const Text('Apply'),
                          ),
                        ),
                      ],
                    ),
                  ],
                ),
              ),
            );
          },
        );
      },
    );
  }

  @override
  Widget build(BuildContext context) {
    _ensureDefaultSeries();
    final async = ref.watch(profileWorkoutHistoryAnalyticsProvider);
    final sectionPrefs = ref.watch(profileScreenSectionsProvider);
    final useHScroll = sectionPrefs.workoutAnalyticsUseHorizontalScroll;

    return async.when(
      loading: () => const SizedBox(
        height: 280,
        child: Center(child: CircularProgressIndicator()),
      ),
      error: (e, _) => SizedBox(
        height: 280,
        child: Center(child: Text('Failed to load analytics: $e')),
      ),
      data: (resp) {
        final meta = resp?.meta is Map<String, dynamic>
            ? (resp!.meta as Map<String, dynamic>)
            : null;
        final analytics = _mapAnalyticsResponse(resp);

        final palette = <Color>[
          Colors.blue.shade400,
          Colors.green.shade400,
          Colors.orange.shade400,
          Colors.purple.shade400,
          Colors.teal.shade400,
          Colors.redAccent,
        ];

        final series = <PlanAnalyticsLineSeries>[];
        for (int i = 0; i < _seriesConfigs.length; i++) {
          final s = _seriesConfigs[i];
          series.add(
            PlanAnalyticsLineSeries(
              metric: _seriesMetricKey(s.id),
              name: _seriesLabel(s, meta),
              color: palette[i % palette.length],
            ),
          );
        }

        final derivedPoints = <PlanAnalyticsPoint>[];
        for (final p in analytics) {
          final nextValues = Map<String, double>.from(p.values);
          for (final s in _seriesConfigs) {
            final key = _seriesMetricKey(s.id);
            nextValues[key] = _computeSeriesPointValue(s, p.values);
          }
          derivedPoints.add(
            PlanAnalyticsPoint(
              order: p.order,
              label: p.label,
              values: nextValues,
              actualValues: null,
            ),
          );
        }

        final title = Text(
          'Workout analytics',
          style: Theme.of(context).textTheme.titleMedium?.copyWith(
            fontWeight: FontWeight.w700,
            fontSize: 15,
          ),
        );

        final metricX = _seriesConfigs.isNotEmpty
            ? _seriesMetricKey(_seriesConfigs.first.id)
            : 'volume_sum';

        return Container(
          width: double.infinity,
          padding: const EdgeInsets.fromLTRB(12, 12, 12, 12),
          decoration: BoxDecoration(
            color: AppColors.surface,
            borderRadius: BorderRadius.circular(16),
            boxShadow: AppShadows.sm,
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  Expanded(child: title),
                  IconButton(
                    visualDensity: VisualDensity.compact,
                    padding: EdgeInsets.zero,
                    tooltip: 'Add series',
                    onPressed: () => _openSeriesEditor(resp),
                    icon: const Icon(Icons.add),
                  ),
                  IconButton(
                    visualDensity: VisualDensity.compact,
                    padding: EdgeInsets.zero,
                    tooltip: 'Clear',
                    onPressed: () {
                      setState(() {
                        _seriesConfigs.clear();
                        _ensureDefaultSeries();
                      });
                      _syncAnalyticsLayers();
                    },
                    icon: const Icon(Icons.delete_outline),
                  ),
                ],
              ),
              const SizedBox(height: 6),
              Wrap(
                spacing: 8,
                runSpacing: 6,
                children: [
                  for (final s in _seriesConfigs)
                    InputChip(
                      visualDensity: VisualDensity.compact,
                      materialTapTargetSize: MaterialTapTargetSize.shrinkWrap,
                      labelPadding: const EdgeInsets.symmetric(horizontal: 6),
                      label: Text(
                        _seriesLabel(s, meta),
                        style: const TextStyle(fontSize: 12),
                      ),
                      onPressed: () => _openSeriesEditor(resp, initial: s),
                      onDeleted: () {
                        setState(() {
                          _seriesConfigs.removeWhere((e) => e.id == s.id);
                          _ensureDefaultSeries();
                        });
                        _syncAnalyticsLayers();
                      },
                    ),
                ],
              ),
              const SizedBox(height: 8),
              SizedBox(
                height: 150,
                child: LayoutBuilder(
                  builder: (context, constraints) {
                    final pointCount = math.max(derivedPoints.length, 1);
                    final desiredWidth = useHScroll
                        ? math.max(constraints.maxWidth, pointCount * 42.0)
                        : constraints.maxWidth;

                    final chart = SizedBox(
                      width: desiredWidth,
                      child: PlanAnalyticsChart(
                        points: derivedPoints,
                        metricX: metricX,
                        metricY: metricX,
                        lineSeries: series,
                        scatterSeries: null,
                        emptyText: 'Нет данных',
                        showScatterAxisTitles: false,
                        bottomLabelModulo:
                            useHScroll && desiredWidth > constraints.maxWidth
                            ? 1
                            : null,
                      ),
                    );

                    if (!useHScroll) {
                      return chart;
                    }

                    return SingleChildScrollView(
                      scrollDirection: Axis.horizontal,
                      child: chart,
                    );
                  },
                ),
              ),
            ],
          ),
        );
      },
    );
  }
}
