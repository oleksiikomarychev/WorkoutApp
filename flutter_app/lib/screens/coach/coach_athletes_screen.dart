import 'package:fl_chart/fl_chart.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:workout_app/models/crm_analytics.dart';
import 'package:workout_app/services/service_locator.dart' as sl;
import 'package:workout_app/screens/coach_athlete_plan_screen.dart';

final coachAthletesAnalyticsProvider = FutureProvider<CoachAthletesAnalyticsModel>((ref) async {
  final svc = ref.watch(sl.crmAnalyticsServiceProvider);
  return svc.getMyAthletesAnalytics();
});

final athleteDisplayNameProvider = FutureProvider.family<String, String>((ref, athleteId) async {
  final profileService = ref.watch(sl.profileServiceProvider);
  try {
    final profile = await profileService.fetchProfileById(athleteId);
    final displayName = profile.displayName;
    if (displayName != null && displayName.trim().isNotEmpty) {
      return displayName;
    }
  } catch (_) {}
  return athleteId;
});

final segmentFilterProvider = StateProvider<String?>((_) => null);
final minSessionsPerWeekProvider = StateProvider<double>((_) => 0);
final minPlanAdherenceProvider = StateProvider<double>((_) => 0);
final sortOptionProvider = StateProvider<_CoachAthleteSort>((_) => _CoachAthleteSort.recentlyActive);

enum _CoachAthleteSort { recentlyActive, sessionsPerWeek, planAdherence }

class CoachAthletesScreen extends ConsumerWidget {
  const CoachAthletesScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final asyncData = ref.watch(coachAthletesAnalyticsProvider);
    final segmentFilter = ref.watch(segmentFilterProvider);
    final minSessions = ref.watch(minSessionsPerWeekProvider);
    final minAdherence = ref.watch(minPlanAdherenceProvider);
    final sortOption = ref.watch(sortOptionProvider);

    return Scaffold(
      appBar: AppBar(
        title: const Text('My Athletes'),
      ),
      body: asyncData.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (error, _) => Center(child: Text('Error: $error')),
        data: (analytics) {
          if (analytics.athletes.isEmpty) {
            return const Center(child: Text('No athletes yet'));
          }
          var filtered = analytics.athletes.where((a) {
            final segOk = segmentFilter == null || a.segment == segmentFilter;
            final sessOk = (a.sessionsPerWeek ?? 0) >= minSessions;
            final adhOk = (a.planAdherence ?? 0) >= minAdherence;
            return segOk && sessOk && adhOk;
          }).toList();

          filtered.sort((a, b) {
            switch (sortOption) {
              case _CoachAthleteSort.sessionsPerWeek:
                return (b.sessionsPerWeek ?? -1).compareTo(a.sessionsPerWeek ?? -1);
              case _CoachAthleteSort.planAdherence:
                return (b.planAdherence ?? -1).compareTo(a.planAdherence ?? -1);
              case _CoachAthleteSort.recentlyActive:
                final aDays = a.daysSinceLastWorkout ?? 9999;
                final bDays = b.daysSinceLastWorkout ?? 9999;
                return aDays.compareTo(bDays);
            }
          });

          return ListView.builder(
            padding: const EdgeInsets.only(bottom: 24),
            itemCount: filtered.length + 1,
            itemBuilder: (context, index) {
              if (index == 0) {
                return _FilterPanel(
                  totalAthletes: analytics.athletes.length,
                  visibleCount: filtered.length,
                );
              }
              final a = filtered[index - 1];
              final displayNameAsync = ref.watch(athleteDisplayNameProvider(a.athleteId));
              return _AthleteCard(
                athlete: a,
                displayNameAsync: displayNameAsync,
              );
            },
          );
        },
      ),
    );
  }
}

class _FilterPanel extends ConsumerWidget {
  final int totalAthletes;
  final int visibleCount;

  const _FilterPanel({required this.totalAthletes, required this.visibleCount});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final segmentFilter = ref.watch(segmentFilterProvider);
    final minSessions = ref.watch(minSessionsPerWeekProvider);
    final minAdherence = ref.watch(minPlanAdherenceProvider);
    final sortOption = ref.watch(sortOptionProvider);

    const segments = ['top_performer', 'on_track', 'at_risk', 'new'];

    return Padding(
      padding: const EdgeInsets.fromLTRB(16, 16, 16, 8),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text('Visible $visibleCount / $totalAthletes', style: Theme.of(context).textTheme.labelMedium),
          const SizedBox(height: 8),
          Wrap(
            spacing: 8,
            children: [
              ChoiceChip(
                label: const Text('All segments'),
                selected: segmentFilter == null,
                onSelected: (_) => ref.read(segmentFilterProvider.notifier).state = null,
              ),
              for (final seg in segments)
                ChoiceChip(
                  label: Text(seg.replaceAll('_', ' ')),
                  selected: segmentFilter == seg,
                  onSelected: (_) => ref.read(segmentFilterProvider.notifier).state = seg,
                ),
            ],
          ),
          const SizedBox(height: 12),
          Row(
            children: [
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text('Min sessions / week: ${minSessions.toStringAsFixed(1)}'),
                    Slider(
                      value: minSessions,
                      min: 0,
                      max: 6,
                      divisions: 12,
                      label: minSessions.toStringAsFixed(1),
                      onChanged: (value) => ref.read(minSessionsPerWeekProvider.notifier).state = value,
                    ),
                  ],
                ),
              ),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text('Min adherence: ${(minAdherence * 100).round()}%'),
                    Slider(
                      value: minAdherence,
                      min: 0,
                      max: 1,
                      divisions: 10,
                      label: '${(minAdherence * 100).round()}%',
                      onChanged: (value) => ref.read(minPlanAdherenceProvider.notifier).state = value,
                    ),
                  ],
                ),
              ),
            ],
          ),
          const SizedBox(height: 12),
          Row(
            children: [
              const Text('Sort by:'),
              const SizedBox(width: 12),
              DropdownButton<_CoachAthleteSort>(
                value: sortOption,
                onChanged: (value) {
                  if (value != null) {
                    ref.read(sortOptionProvider.notifier).state = value;
                  }
                },
                items: const [
                  DropdownMenuItem(
                    value: _CoachAthleteSort.recentlyActive,
                    child: Text('Recently active'),
                  ),
                  DropdownMenuItem(
                    value: _CoachAthleteSort.sessionsPerWeek,
                    child: Text('Sessions / week'),
                  ),
                  DropdownMenuItem(
                    value: _CoachAthleteSort.planAdherence,
                    child: Text('Plan adherence'),
                  ),
                ],
              ),
            ],
          ),
        ],
      ),
    );
  }
}

class _AthleteCard extends ConsumerWidget {
  final AthleteTrainingSummaryModel athlete;
  final AsyncValue<String> displayNameAsync;

  const _AthleteCard({required this.athlete, required this.displayNameAsync});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final title = displayNameAsync.when(
      data: (value) => value,
      loading: () => athlete.athleteId,
      error: (_, __) => athlete.athleteId,
    );

    return Card(
      margin: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
      child: InkWell(
        borderRadius: BorderRadius.circular(12),
        onTap: () => Navigator.of(context).push(
          MaterialPageRoute(
            builder: (_) => CoachAthletePlanScreen(
              athleteId: athlete.athleteId,
              athleteName: title,
            ),
          ),
        ),
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  Expanded(
                    child: Text(
                      title,
                      style: Theme.of(context).textTheme.titleMedium,
                    ),
                  ),
                  if (athlete.segment != null)
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 4),
                      decoration: BoxDecoration(
                        color: Colors.blueGrey.shade50,
                        borderRadius: BorderRadius.circular(999),
                      ),
                      child: Text(
                        athlete.segment!.replaceAll('_', ' '),
                        style: Theme.of(context).textTheme.labelSmall,
                      ),
                    ),
                ],
              ),
              const SizedBox(height: 8),
              Wrap(
                spacing: 16,
                runSpacing: 8,
                children: [
                  _MetricChip(label: 'Sessions', value: '${athlete.sessionsCount}'),
                  _MetricChip(label: 'S / week', value: (athlete.sessionsPerWeek ?? 0).toStringAsFixed(1)),
                  _MetricChip(label: 'Plan %', value: athlete.planAdherence != null ? '${(athlete.planAdherence! * 100).round()}%' : '—'),
                  _MetricChip(label: 'Intensity', value: athlete.avgIntensity?.toStringAsFixed(1) ?? '—'),
                  _MetricChip(label: 'RPE', value: athlete.avgEffort?.toStringAsFixed(1) ?? '—'),
                ],
              ),
              const SizedBox(height: 12),
              _PlanAdherenceBar(value: athlete.planAdherence),
              const SizedBox(height: 12),
              _RpeMiniChart(distribution: athlete.rpeDistribution),
            ],
          ),
        ),
      ),
    );
  }
}

class _MetricChip extends StatelessWidget {
  final String label;
  final String value;

  const _MetricChip({required this.label, required this.value});

  @override
  Widget build(BuildContext context) {
    return Column(
      mainAxisSize: MainAxisSize.min,
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(label, style: Theme.of(context).textTheme.labelSmall?.copyWith(color: Colors.grey.shade600)),
        Text(value, style: Theme.of(context).textTheme.titleMedium?.copyWith(fontWeight: FontWeight.w600)),
      ],
    );
  }
}

class _PlanAdherenceBar extends StatelessWidget {
  final double? value;

  const _PlanAdherenceBar({this.value});

  @override
  Widget build(BuildContext context) {
    final double? percent =
        value != null ? value!.clamp(0.0, 1.0) as double : null;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            const Text('Plan adherence'),
            Text(value != null ? '${((percent ?? 0) * 100).round()}%' : 'n/a'),
          ],
        ),
        const SizedBox(height: 4),
        ClipRRect(
          borderRadius: BorderRadius.circular(8),
          child: LinearProgressIndicator(
            value: percent,
            minHeight: 8,
          ),
        ),
      ],
    );
  }
}

class _RpeMiniChart extends StatelessWidget {
  final Map<String, double>? distribution;

  const _RpeMiniChart({this.distribution});

  @override
  Widget build(BuildContext context) {
    final data = distribution;
    if (data == null || data.isEmpty) {
      return const Text('No RPE data');
    }

    final entries = data.entries
        .map((e) => MapEntry(int.tryParse(e.key) ?? 0, e.value))
        .where((e) => e.key > 0)
        .toList()
      ..sort((a, b) => a.key.compareTo(b.key));

    final barGroups = <BarChartGroupData>[];
    for (var i = 0; i < entries.length; i++) {
      barGroups.add(
        BarChartGroupData(
          x: entries[i].key,
          barRods: [
            BarChartRodData(toY: entries[i].value * 100, color: Theme.of(context).colorScheme.primary, width: 6),
          ],
        ),
      );
    }

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Text('RPE distribution'),
        const SizedBox(height: 8),
        SizedBox(
          height: 140,
          child: BarChart(
            BarChartData(
              barTouchData: BarTouchData(enabled: false),
              titlesData: FlTitlesData(
                leftTitles: AxisTitles(
                  sideTitles: SideTitles(showTitles: true, reservedSize: 32, interval: 20, getTitlesWidget: (value, meta) => Text('${value.toInt()}%')),
                ),
                rightTitles: const AxisTitles(sideTitles: SideTitles(showTitles: false)),
                topTitles: const AxisTitles(sideTitles: SideTitles(showTitles: false)),
                bottomTitles: AxisTitles(
                  sideTitles: SideTitles(
                    showTitles: true,
                    reservedSize: 22,
                    getTitlesWidget: (value, meta) => Text(value.toInt().toString(), style: const TextStyle(fontSize: 10)),
                  ),
                ),
              ),
              gridData: FlGridData(show: false),
              borderData: FlBorderData(show: false),
              barGroups: barGroups,
            ),
          ),
        ),
      ],
    );
  }
}
