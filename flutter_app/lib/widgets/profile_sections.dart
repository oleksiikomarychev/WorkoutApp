import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import 'package:workout_app/l10n/app_localizations.dart';

import '../config/constants/theme_constants.dart';
import '../models/user_stats.dart';
import '../models/workout_session.dart';

class ProfileStatsRow extends StatelessWidget {
  final UserStats stats;
  final EdgeInsetsGeometry padding;

  const ProfileStatsRow({
    super.key,
    required this.stats,
    this.padding = const EdgeInsets.symmetric(horizontal: 24),
  });

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    return Padding(
      padding: padding,
      child: Center(
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 520),
          child: Row(
            children: [
              Expanded(
                child: _StatCard(
                  value: '${stats.totalWorkouts}',
                  label: l10n.statsTotalWorkouts,
                  color: Theme.of(context).colorScheme.tertiaryContainer,
                  foregroundColor: Theme.of(
                    context,
                  ).colorScheme.onTertiaryContainer,
                ),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: _StatCard(
                  value: stats.totalVolume.toStringAsFixed(0),
                  label: l10n.statsVolumeKg,
                  color: Theme.of(context).colorScheme.primaryContainer,
                  foregroundColor: Theme.of(
                    context,
                  ).colorScheme.onPrimaryContainer,
                ),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: _StatCard(
                  value: '${stats.activeDays}',
                  label: l10n.statsActiveDays,
                  color: Theme.of(context).colorScheme.secondaryContainer,
                  foregroundColor: Theme.of(
                    context,
                  ).colorScheme.onSecondaryContainer,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _StatCard extends StatelessWidget {
  final String value;
  final String label;
  final Color color;
  final Color foregroundColor;

  const _StatCard({
    required this.value,
    required this.label,
    required this.color,
    required this.foregroundColor,
  });

  @override
  Widget build(BuildContext context) {
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
            style: TextStyle(
              fontSize: 20,
              fontWeight: FontWeight.bold,
              color: foregroundColor,
            ),
          ),
          const SizedBox(height: 4),
          Text(
            label,
            textAlign: TextAlign.center,
            style: TextStyle(fontSize: 11, color: foregroundColor),
          ),
        ],
      ),
    );
  }
}

class ProfileActivitySection extends StatelessWidget {
  final UserStats stats;
  final EdgeInsetsGeometry padding;

  const ProfileActivitySection({
    super.key,
    required this.stats,
    this.padding = const EdgeInsets.symmetric(horizontal: 24),
  });

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    return Padding(
      padding: padding,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            l10n.activityTitle,
            style: TextStyle(
              fontSize: 20,
              fontWeight: FontWeight.bold,
              color: Theme.of(context).colorScheme.onSurface,
            ),
          ),
          const SizedBox(height: 8),
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text(
                l10n.lastWeeks(stats.weeks),
                style: TextStyle(
                  fontSize: 14,
                  color: Theme.of(context).colorScheme.onSurfaceVariant,
                ),
              ),
              Text(
                l10n.maxKgPerDay(stats.maxDayVolume.toStringAsFixed(0)),
                style: TextStyle(
                  fontSize: 12,
                  color: Theme.of(context).colorScheme.onSurfaceVariant,
                  fontWeight: FontWeight.w500,
                ),
              ),
            ],
          ),
          const SizedBox(height: 16),
          _ActivityGrid(
            activityMap: stats.activityMap,
            maxVolume: stats.maxDayVolume,
            weeks: stats.weeks,
          ),
          const SizedBox(height: 8),
          _ActivityLegend(),
        ],
      ),
    );
  }
}

class _ActivityGrid extends StatelessWidget {
  final Map<DateTime, DayActivity> activityMap;
  final double maxVolume;
  final int weeks;

  const _ActivityGrid({
    required this.activityMap,
    required this.maxVolume,
    required this.weeks,
  });

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    final locale = Localizations.localeOf(context).languageCode;
    final today = DateTime.now();
    final endDate = DateTime(today.year, today.month, today.day);
    final endWeekStart = endDate.subtract(Duration(days: endDate.weekday - 1));
    final startWeekStart = endWeekStart.subtract(
      Duration(days: (weeks - 1) * 7),
    );

    final columns = <List<DateTime>>[];
    for (int w = 0; w < weeks; w++) {
      final weekStart = startWeekStart.add(Duration(days: w * 7));
      columns.add(List.generate(7, (d) => weekStart.add(Duration(days: d))));
    }

    return SingleChildScrollView(
      scrollDirection: Axis.horizontal,
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: columns.map((weekDays) {
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
                    style: TextStyle(
                      fontSize: 10,
                      fontWeight: FontWeight.w600,
                      color: Theme.of(context).colorScheme.onSurface,
                    ),
                    textAlign: TextAlign.center,
                    softWrap: false,
                  ),
                ),
                const SizedBox(height: 6),
                for (final date in weekDays)
                  Padding(
                    padding: const EdgeInsets.only(bottom: 4),
                    child: Builder(
                      builder: (_) {
                        final day = DateTime(date.year, date.month, date.day);
                        final dayActivity = _getActivityForDate(
                          activityMap,
                          day,
                        );
                        final volume = dayActivity?.volume ?? 0;
                        final color = _getActivityColor(volume, maxVolume);
                        return Tooltip(
                          message: dayActivity != null
                              ? '${DateFormat('MMM d', locale).format(date)}\n${l10n.sessionsCount(dayActivity.sessionCount)}\n${volume.toStringAsFixed(0)} kg'
                              : '${DateFormat('MMM d', locale).format(date)}\n${l10n.noActivity}',
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
    if (volume == 0 || maxVolume == 0) return const Color(0xFFEBEDF0);
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
}

class _ActivityLegend extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    return Row(
      mainAxisAlignment: MainAxisAlignment.center,
      children: [
        Text(
          l10n.less,
          style: TextStyle(fontSize: 10, color: Theme.of(context).colorScheme.onSurfaceVariant),
        ),
        const SizedBox(width: 4),
        const _LegendBox(Color(0xFFEBEDF0)),
        const SizedBox(width: 2),
        const _LegendBox(Color(0xFFC6E48B)),
        const SizedBox(width: 2),
        const _LegendBox(Color(0xFF7BC96F)),
        const SizedBox(width: 2),
        const _LegendBox(Color(0xFF239A3B)),
        const SizedBox(width: 2),
        const _LegendBox(Color(0xFF196127)),
        const SizedBox(width: 4),
        Text(
          l10n.more,
          style: TextStyle(fontSize: 10, color: Theme.of(context).colorScheme.onSurfaceVariant),
        ),
      ],
    );
  }
}

class _LegendBox extends StatelessWidget {
  final Color color;
  const _LegendBox(this.color);

  @override
  Widget build(BuildContext context) {
    return Container(
      width: 10,
      height: 10,
      decoration: BoxDecoration(
        color: color,
        borderRadius: BorderRadius.circular(2),
      ),
    );
  }
}

class ProfileCompletedWorkoutsSection extends StatelessWidget {
  final List<WorkoutSession> sessions;
  final EdgeInsetsGeometry padding;
  final void Function(WorkoutSession session)? onSessionTap;

  const ProfileCompletedWorkoutsSection({
    super.key,
    required this.sessions,
    this.padding = const EdgeInsets.symmetric(horizontal: 24),
    this.onSessionTap,
  });

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    return Padding(
      padding: padding,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(
                Icons.calendar_today,
                color: Theme.of(context).colorScheme.primary,
                size: 24,
              ),
              const SizedBox(width: 8),
              Text(
                l10n.completedWorkoutsTitle,
                style: TextStyle(
                  fontSize: 20,
                  fontWeight: FontWeight.bold,
                  color: Theme.of(context).colorScheme.onSurface,
                ),
              ),
            ],
          ),
          const SizedBox(height: 16),
          if (sessions.isEmpty)
            Text(
              l10n.noCompletedWorkoutsYet,
              style: TextStyle(color: Theme.of(context).colorScheme.onSurfaceVariant),
            )
          else
            Column(
              children: sessions
                  .map((s) => _WorkoutCard(session: s, onTap: onSessionTap))
                  .toList(),
            ),
        ],
      ),
    );
  }
}

class _WorkoutCard extends StatelessWidget {
  final WorkoutSession session;
  final void Function(WorkoutSession session)? onTap;

  const _WorkoutCard({required this.session, this.onTap});

  @override
  Widget build(BuildContext context) {
    final dateFormat = DateFormat('MMM dd');
    final workoutCode = 'WO${session.workoutId}';

    return Container(
      margin: const EdgeInsets.only(bottom: 12),
      decoration: BoxDecoration(
        color: Theme.of(context).colorScheme.surfaceContainerLow,
        borderRadius: BorderRadius.circular(12),
        boxShadow: AppShadows.sm,
      ),
      child: Material(
        color: Colors.transparent,
        borderRadius: BorderRadius.circular(12),
        child: InkWell(
          borderRadius: BorderRadius.circular(12),
          onTap: onTap != null ? () => onTap!(session) : null,
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
                    color: Theme.of(context).colorScheme.tertiaryContainer,
                    borderRadius: BorderRadius.circular(20),
                  ),
                  child: Text(
                    workoutCode,
                    style: TextStyle(
                      color: Theme.of(context).colorScheme.onTertiaryContainer,
                      fontSize: 12,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                ),
                const SizedBox(width: 16),
                Text(
                  dateFormat.format(session.startedAt),
                  style: TextStyle(
                    fontSize: 14,
                    color: Theme.of(context).colorScheme.onSurfaceVariant,
                  ),
                ),
                const Spacer(),
                Icon(
                  Icons.check_circle,
                  color: Theme.of(context).colorScheme.tertiary,
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
