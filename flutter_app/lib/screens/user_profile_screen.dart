import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:firebase_auth/firebase_auth.dart';
import 'package:intl/intl.dart';
import 'package:workout_app/config/constants/theme_constants.dart';
import 'package:workout_app/models/workout.dart';
import 'package:workout_app/models/workout_session.dart';
import 'package:workout_app/models/user_profile.dart';
import 'package:workout_app/providers/providers.dart';
import 'package:workout_app/services/service_locator.dart' as sl;
import 'package:workout_app/services/workout_service.dart';
import 'package:workout_app/services/avatar_service.dart';
import 'package:workout_app/screens/workout_session_history_screen.dart';
import 'package:workout_app/screens/session_log_screen.dart';
import 'package:workout_app/config/constants/route_names.dart';
import 'dart:typed_data';
import 'package:workout_app/widgets/floating_header_bar.dart';
import '../widgets/user_profile_view.dart';

const int kActivityWeeks = 48;

// Avatar generator state
final avatarPromptProvider = StateProvider<String>((ref) => '');
final avatarImageProvider = StateProvider<Uint8List?>((ref) => null);
final avatarLoadingProvider = StateProvider<bool>((ref) => false);

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
    final profileAsync = ref.watch(userProfileProvider);

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
                    ref.invalidate(userProfileProvider);
                    ref.invalidate(profileAggregatesProvider);
                    ref.invalidate(completedSessionsProvider);
                    await Future.wait([
                      ref.read(userProfileProvider.future),
                      ref.read(profileAggregatesProvider.future),
                      ref.read(completedSessionsProvider.future),
                    ]);
                  },
                  child: profileAsync.when(
                    loading: () => const Center(child: CircularProgressIndicator()),
                    error: (error, _) => _buildErrorState(ref, error),
                    data: (profile) {
                      return ref.watch(profileAggregatesProvider).when(
                        loading: () => const Center(child: CircularProgressIndicator()),
                        error: (error, _) => _buildErrorState(ref, error),
                        data: (stats) => _buildContent(context, ref, stats, user, profile),
                      );
                    },
                  ),
                ),
                Align(
                  alignment: Alignment.topCenter,
                  child: FloatingHeaderBar(
                    title: 'Account',
                    leading: IconButton(
                      icon: const Icon(Icons.arrow_back, color: AppColors.textPrimary),
                      onPressed: () => Navigator.of(context).maybePop(),
                    ),
                    onProfileTap: null,
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
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

  Future<void> _showEditProfileDialog(BuildContext context, WidgetRef ref, User? user, UserProfile profile) async {
    final nameController = TextEditingController(text: profile.displayName ?? user?.displayName ?? '');
    final bioController = TextEditingController(text: profile.bio ?? '');

    bool isPublic = profile.isPublic;
    String unitSystem = profile.settings.unitSystem;
    String locale = profile.settings.locale;
    String timezone = profile.settings.timezone ?? '';
    bool notificationsEnabled = profile.settings.notificationsEnabled;

    // New profile fields
    final bodyweightController = TextEditingController(
      text: profile.bodyweightKg != null ? profile.bodyweightKg!.toStringAsFixed(1) : '',
    );
    final heightController = TextEditingController(
      text: profile.heightCm != null ? profile.heightCm!.toStringAsFixed(0) : '',
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
            return AlertDialog(
              title: const Text('Edit profile'),
              content: SingleChildScrollView(
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    TextField(
                      controller: nameController,
                      decoration: const InputDecoration(labelText: 'Display name'),
                    ),
                    TextField(
                      controller: bioController,
                      decoration: const InputDecoration(labelText: 'Bio'),
                      maxLines: 3,
                    ),
                    const SizedBox(height: 12),
                    // New core profile fields
                    Row(
                      children: [
                        Expanded(
                          child: TextField(
                            controller: bodyweightController,
                            keyboardType: const TextInputType.numberWithOptions(decimal: true),
                            decoration: const InputDecoration(labelText: 'Bodyweight (kg)'),
                          ),
                        ),
                        const SizedBox(width: 12),
                        Expanded(
                          child: TextField(
                            controller: heightController,
                            keyboardType: const TextInputType.numberWithOptions(decimal: false),
                            decoration: const InputDecoration(labelText: 'Height (cm)'),
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
                            keyboardType: const TextInputType.numberWithOptions(decimal: false),
                            decoration: const InputDecoration(labelText: 'Age'),
                          ),
                        ),
                        const SizedBox(width: 12),
                        Expanded(
                          child: TextField(
                            controller: experienceYearsController,
                            keyboardType: const TextInputType.numberWithOptions(decimal: true),
                            decoration: const InputDecoration(labelText: 'Training years'),
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
                              DropdownMenuItem(value: 'male', child: Text('Male')),
                              DropdownMenuItem(value: 'female', child: Text('Female')),
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
                            decoration: const InputDecoration(labelText: 'Experience level'),
                            items: const [
                              DropdownMenuItem(value: 'beginner', child: Text('Beginner')),
                              DropdownMenuItem(value: 'intermediate', child: Text('Intermediate')),
                              DropdownMenuItem(value: 'advanced', child: Text('Advanced')),
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
                      decoration: const InputDecoration(labelText: 'Primary goal'),
                      items: const [
                        DropdownMenuItem(value: 'strength', child: Text('Strength')),
                        DropdownMenuItem(value: 'hypertrophy', child: Text('Hypertrophy')),
                        DropdownMenuItem(value: 'fat_loss', child: Text('Fat loss')),
                        DropdownMenuItem(value: 'general_fitness', child: Text('General fitness')),
                      ],
                      onChanged: (value) {
                        setState(() => primaryGoal = value);
                      },
                    ),
                    const SizedBox(height: 8),
                    DropdownButtonFormField<String>(
                      value: trainingEnvironment,
                      decoration: const InputDecoration(labelText: 'Training environment'),
                      items: const [
                        DropdownMenuItem(value: 'commercial_gym', child: Text('Commercial gym')),
                        DropdownMenuItem(value: 'home', child: Text('Home')),
                        DropdownMenuItem(value: 'garage', child: Text('Garage')),
                      ],
                      onChanged: (value) {
                        setState(() => trainingEnvironment = value);
                      },
                    ),
                    const SizedBox(height: 12),
                    SwitchListTile(
                      contentPadding: EdgeInsets.zero,
                      title: const Text('Public profile'),
                      value: isPublic,
                      onChanged: (value) => setState(() => isPublic = value),
                    ),
                    const SizedBox(height: 8),
                    Row(
                      children: [
                        const Text('Units'),
                        const SizedBox(width: 16),
                        DropdownButton<String>(
                          value: unitSystem,
                          items: const [
                            DropdownMenuItem(value: 'metric', child: Text('Metric')),
                            DropdownMenuItem(value: 'imperial', child: Text('Imperial')),
                          ],
                          onChanged: (value) {
                            if (value != null) {
                              setState(() => unitSystem = value);
                            }
                          },
                        ),
                      ],
                    ),
                    TextField(
                      decoration: const InputDecoration(labelText: 'Locale'),
                      controller: TextEditingController(text: locale),
                      onChanged: (value) => locale = value,
                    ),
                    TextField(
                      decoration: const InputDecoration(labelText: 'Timezone'),
                      controller: TextEditingController(text: timezone),
                      onChanged: (value) => timezone = value,
                    ),
                    SwitchListTile(
                      contentPadding: EdgeInsets.zero,
                      title: const Text('Notifications'),
                      value: notificationsEnabled,
                      onChanged: (value) => setState(() => notificationsEnabled = value),
                    ),
                  ],
                ),
              ),
              actions: [
                TextButton(
                  onPressed: () => Navigator.of(ctx).pop(false),
                  child: const Text('Cancel'),
                ),
                ElevatedButton(
                  onPressed: () => Navigator.of(ctx).pop(true),
                  child: const Text('Save'),
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
        isPublic: isPublic,
        bodyweightKg: _parseDouble(bodyweightController.text),
        heightCm: _parseDouble(heightController.text),
        age: _parseInt(ageController.text),
        sex: sex,
        trainingExperienceYears: _parseDouble(experienceYearsController.text),
        trainingExperienceLevel: experienceLevel,
        primaryDefaultGoal: primaryGoal,
        trainingEnvironment: trainingEnvironment,
      );
      await svc.updateSettings(
        unitSystem: unitSystem,
        locale: locale.isEmpty ? null : locale,
        timezone: timezone.isEmpty ? null : timezone,
        notificationsEnabled: notificationsEnabled,
      );
      ref.invalidate(userProfileProvider);
      if (context.mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Profile updated')),
        );
      }
    } catch (e) {
      if (context.mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Failed to update profile: $e')),
        );
      }
    }
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

  Widget _buildContent(BuildContext context, WidgetRef ref, UserStats stats, User? user, UserProfile profile) {
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
                  subtitle:
                      'Units: ${profile.settings.unitSystem} • Locale: ${profile.settings.locale}${profile.settings.timezone != null && profile.settings.timezone!.isNotEmpty ? ' • TZ: ${profile.settings.timezone}' : ''}',
                  avatarUrlOverride: user?.photoURL,
                  onEditProfile: () => _showEditProfileDialog(context, ref, user, profile),
                  onManageCoaching: () => _showCoachingProfileDialog(context, ref, profile),
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
                  ],
                ),
              ),
            ),
          ),
          const SizedBox(height: 24),
          Center(
            child: ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 720),
              child: Padding(
                padding: const EdgeInsets.symmetric(horizontal: 24),
                child: _buildCoachingSection(context, ref, profile),
              ),
            ),
          ),
          const SizedBox(height: 32),
          Center(
            child: ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 720),
              child: Padding(
                padding: const EdgeInsets.symmetric(horizontal: 24),
                child: _buildAvatarGenerator(context, ref),
              ),
            ),
          ),
          const SizedBox(height: 32),
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
      ),
    );
  }

  Widget _buildCoachingSection(BuildContext context, WidgetRef ref, UserProfile profile) {
    final coaching = profile.coaching;
    final enabled = coaching?.enabled ?? false;
    final accepting = coaching?.acceptingClients ?? false;

    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(20),
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
              const Icon(Icons.workspaces_outline, color: AppColors.primary),
              const SizedBox(width: 12),
              Expanded(
                child: Text(
                  'Coaching profile',
                  style: Theme.of(context).textTheme.titleMedium?.copyWith(fontWeight: FontWeight.bold),
                ),
              ),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                decoration: BoxDecoration(
                  color: enabled ? const Color(0xFFE6F4EA) : const Color(0xFFFFF3E0),
                  borderRadius: BorderRadius.circular(20),
                ),
                child: Text(
                  enabled ? (accepting ? 'Accepting clients' : 'Coaching paused') : 'Disabled',
                  style: TextStyle(
                    fontSize: 12,
                    color: enabled
                        ? (accepting ? AppColors.success : AppColors.textSecondary)
                        : AppColors.textSecondary,
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 16),
          if (!enabled)
            const Text(
              'Turn on coaching features to let other athletes see a "Hire" button on your profile and manage your athletes via the CRM tab.',
              style: TextStyle(color: AppColors.textSecondary, fontSize: 13),
            )
          else ...[
            if ((coaching?.tagline?.isNotEmpty ?? false)) ...[
              Text(
                coaching!.tagline!,
                style: const TextStyle(fontSize: 16, fontWeight: FontWeight.w600),
              ),
              const SizedBox(height: 8),
            ],
            if ((coaching?.description?.isNotEmpty ?? false)) ...[
              Text(
                coaching!.description!,
                style: const TextStyle(fontSize: 13, color: AppColors.textSecondary),
              ),
              const SizedBox(height: 12),
            ],
            Wrap(
              spacing: 8,
              runSpacing: 8,
              children: [
                if ((coaching?.specializations ?? []).isNotEmpty)
                  _coachingChip('Focus', coaching!.specializations.join(', ')),
                if ((coaching?.languages ?? []).isNotEmpty)
                  _coachingChip('Languages', coaching!.languages.join(', ')),
                if (coaching?.experienceYears != null)
                  _coachingChip('Experience', '${coaching!.experienceYears} yrs'),
                if ((coaching?.timezone?.isNotEmpty ?? false))
                  _coachingChip('Timezone', coaching!.timezone!),
                if (coaching?.ratePlan != null)
                  _coachingChip(
                    'Rate',
                    coaching!.ratePlan!.amountMinor != null && coaching.ratePlan!.currency != null
                        ? '${(coaching.ratePlan!.amountMinor! / 100).toStringAsFixed(0)} ${coaching.ratePlan!.currency!.toUpperCase()} ${coaching.ratePlan!.type ?? ''}'
                        : (coaching.ratePlan!.type ?? 'Custom rate'),
                  ),
              ],
            ),
          ],
          const SizedBox(height: 16),
          SizedBox(
            width: double.infinity,
            child: ElevatedButton(
              onPressed: () => _showCoachingProfileDialog(context, ref, profile),
              style: ElevatedButton.styleFrom(
                backgroundColor: AppColors.textPrimary,
                foregroundColor: Colors.white,
                padding: const EdgeInsets.symmetric(vertical: 14),
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
              ),
              child: Text(enabled ? 'Manage coaching profile' : 'Enable coaching features'),
            ),
          ),
          const SizedBox(height: 12),
          SizedBox(
            width: double.infinity,
            child: OutlinedButton(
              onPressed: () {
                Navigator.of(context).pushNamed(RouteNames.myCoaches);
              },
              child: const Text('My coaches'),
            ),
          ),
        ],
      ),
    );
  }

  Widget _coachingChip(String label, String value) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
      decoration: BoxDecoration(
        color: AppColors.background,
        borderRadius: BorderRadius.circular(12),
      ),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(label, style: const TextStyle(fontSize: 11, color: AppColors.textSecondary)),
          const SizedBox(height: 2),
          Text(value, style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w600)),
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
                        final url = await svc.applyAsProfile(pngBytes: imageBytes);
                        try {
                          await FirebaseAuth.instance.currentUser?.reload();
                        } catch (_) {}
                        ref.invalidate(profileAggregatesProvider);
                        if (context.mounted) {
                          ScaffoldMessenger.of(context).showSnackBar(
                            SnackBar(content: Text(url.isNotEmpty ? 'Profile photo updated' : 'Saved avatar')),
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
                onChanged: (v) => ref.read(avatarPromptProvider.notifier).state = v,
                decoration: InputDecoration(
                  prefixIcon: const Icon(Icons.casino_outlined),
                  hintText: 'Describe your avatar',
                  contentPadding: const EdgeInsets.symmetric(horizontal: 12, vertical: 12),
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
                          ref.read(avatarLoadingProvider.notifier).state = false;
                        }
                      },
                style: ElevatedButton.styleFrom(
                  backgroundColor: AppColors.textPrimary,
                  foregroundColor: Colors.white,
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                  padding: const EdgeInsets.symmetric(horizontal: 16),
                ),
                child: loading
                    ? const SizedBox(width: 20, height: 20, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white))
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
            children: sessions.map((s) => _buildWorkoutCard(context, s)).toList(),
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

  Future<void> _showCoachingProfileDialog(BuildContext context, WidgetRef ref, UserProfile profile) async {
    final coaching = profile.coaching;

    bool enabled = coaching?.enabled ?? false;
    bool acceptingClients = coaching?.acceptingClients ?? false;
    final taglineController = TextEditingController(text: coaching?.tagline ?? '');
    final descriptionController = TextEditingController(text: coaching?.description ?? '');
    final specializationsController = TextEditingController(text: (coaching?.specializations ?? []).join(', '));
    final languagesController = TextEditingController(text: (coaching?.languages ?? []).join(', '));
    final experienceController = TextEditingController(
      text: coaching?.experienceYears != null ? coaching!.experienceYears!.toString() : '',
    );
    final timezoneController = TextEditingController(text: coaching?.timezone ?? '');
    String? rateType = coaching?.ratePlan?.type;
    final rateCurrencyController = TextEditingController(text: coaching?.ratePlan?.currency ?? '');
    final rateAmountController = TextEditingController(
      text: coaching?.ratePlan?.amountMinor != null ? (coaching!.ratePlan!.amountMinor! / 100).toStringAsFixed(0) : '',
    );

    final result = await showDialog<bool>(
      context: context,
      builder: (ctx) {
        return StatefulBuilder(
          builder: (ctx, setState) {
            return AlertDialog(
              title: const Text('Coaching settings'),
              content: SingleChildScrollView(
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    SwitchListTile(
                      contentPadding: EdgeInsets.zero,
                      title: const Text('Enable coaching features'),
                      value: enabled,
                      onChanged: (value) => setState(() => enabled = value),
                    ),
                    SwitchListTile(
                      contentPadding: EdgeInsets.zero,
                      title: const Text('Accepting new clients'),
                      value: acceptingClients,
                      onChanged: enabled ? (value) => setState(() => acceptingClients = value) : null,
                    ),
                    TextField(
                      controller: taglineController,
                      decoration: const InputDecoration(labelText: 'Tagline'),
                    ),
                    TextField(
                      controller: descriptionController,
                      decoration: const InputDecoration(labelText: 'Description'),
                      maxLines: 3,
                    ),
                    TextField(
                      controller: specializationsController,
                      decoration: const InputDecoration(
                        labelText: 'Specializations (comma separated)',
                      ),
                    ),
                    TextField(
                      controller: languagesController,
                      decoration: const InputDecoration(
                        labelText: 'Languages (comma separated)',
                      ),
                    ),
                    TextField(
                      controller: experienceController,
                      decoration: const InputDecoration(labelText: 'Experience (years)'),
                      keyboardType: TextInputType.number,
                    ),
                    TextField(
                      controller: timezoneController,
                      decoration: const InputDecoration(labelText: 'Timezone (e.g. Europe/Kyiv)'),
                    ),
                    const SizedBox(height: 12),
                    DropdownButtonFormField<String>(
                      value: rateType,
                      decoration: const InputDecoration(labelText: 'Rate type'),
                      items: const [
                        DropdownMenuItem(value: 'per_month', child: Text('Per month')),
                        DropdownMenuItem(value: 'per_program', child: Text('Per program')),
                        DropdownMenuItem(value: 'per_session', child: Text('Per session')),
                      ],
                      onChanged: (value) => setState(() => rateType = value),
                    ),
                    Row(
                      children: [
                        Expanded(
                          child: TextField(
                            controller: rateCurrencyController,
                            decoration: const InputDecoration(labelText: 'Currency (e.g. USD)'),
                          ),
                        ),
                        const SizedBox(width: 12),
                        Expanded(
                          child: TextField(
                            controller: rateAmountController,
                            decoration: const InputDecoration(labelText: 'Amount'),
                            keyboardType: TextInputType.number,
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 4),
                    const Align(
                      alignment: Alignment.centerLeft,
                      child: Text(
                        'Amount is entered in whole units (e.g. 120 = 120.00).',
                        style: TextStyle(fontSize: 11, color: AppColors.textSecondary),
                      ),
                    ),
                  ],
                ),
              ),
              actions: [
                TextButton(
                  onPressed: () => Navigator.of(ctx).pop(false),
                  child: const Text('Cancel'),
                ),
                ElevatedButton(
                  onPressed: () => Navigator.of(ctx).pop(true),
                  child: const Text('Save'),
                ),
              ],
            );
          },
        );
      },
    );

    if (result != true) return;

    List<String> _parseList(String text) {
      return text
          .split(',')
          .map((e) => e.trim())
          .where((element) => element.isNotEmpty)
          .toList();
    }

    int? _parseInt(String text) {
      if (text.trim().isEmpty) return null;
      return int.tryParse(text.trim());
    }

    int? _parseAmount(String text) {
      if (text.trim().isEmpty) return null;
      final value = double.tryParse(text.trim());
      if (value == null) return null;
      return (value * 100).round();
    }

    final svc = ref.read(sl.profileServiceProvider);
    try {
      await svc.updateCoachingProfile(
        enabled: enabled,
        acceptingClients: acceptingClients,
        tagline: taglineController.text.trim(),
        description: descriptionController.text.trim(),
        specializations: _parseList(specializationsController.text),
        languages: _parseList(languagesController.text),
        experienceYears: _parseInt(experienceController.text),
        timezone: timezoneController.text.trim(),
        ratePlan: (rateType != null || rateCurrencyController.text.trim().isNotEmpty || rateAmountController.text.trim().isNotEmpty)
            ? CoachingRatePlan(
                type: rateType,
                currency: rateCurrencyController.text.trim().isEmpty ? null : rateCurrencyController.text.trim().toLowerCase(),
                amountMinor: _parseAmount(rateAmountController.text),
              )
            : null,
      );
      ref.invalidate(userProfileProvider);
      if (context.mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Coaching profile updated')),
        );
      }
    } catch (e) {
      if (context.mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Failed to update coaching profile: $e')),
        );
      }
    }
  }
}
