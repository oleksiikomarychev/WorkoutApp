import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/intl.dart';
import 'package:fl_chart/fl_chart.dart';
import 'package:workout_app/config/constants/theme_constants.dart';
import 'package:workout_app/models/crm_analytics.dart';
import 'package:workout_app/services/service_locator.dart' as sl;
import 'package:workout_app/widgets/floating_header_bar.dart';
import 'package:workout_app/widgets/plan_analytics_chart.dart';

final athleteDetailedAnalyticsProvider = FutureProvider.family<AthleteDetailedAnalyticsModel, String>((ref, athleteId) async {
  final svc = ref.watch(sl.crmAnalyticsServiceProvider);
  return svc.getAthleteAnalytics(athleteId: athleteId);
});

final athleteDetailDisplayNameProvider = FutureProvider.family<String, String>((ref, athleteId) async {
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

class AthleteDetailScreen extends ConsumerWidget {
  final String athleteId;

  const AthleteDetailScreen({super.key, required this.athleteId});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final asyncData = ref.watch(athleteDetailedAnalyticsProvider(athleteId));
    final displayNameAsync = ref.watch(athleteDetailDisplayNameProvider(athleteId));
    final df = DateFormat('dd.MM.yyyy');

    final headerTitle = displayNameAsync.when(
      data: (name) => name,
      loading: () => 'Athlete',
      error: (_, __) => 'Athlete',
    );

    return Scaffold(
      backgroundColor: AppColors.background,
      body: SafeArea(
        bottom: false,
        child: Stack(
          children: [
            asyncData.when(
              loading: () => const Center(child: CircularProgressIndicator()),
              error: (error, _) => Center(child: Text('Error: $error')),
              data: (details) {
                final cardName = displayNameAsync.when(
                  data: (name) => name,
                  loading: () => athleteId,
                  error: (_, __) => athleteId,
                );
                return SingleChildScrollView(
                  physics: const AlwaysScrollableScrollPhysics(),
                  child: Padding(
                    padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 24),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.stretch,
                      children: [
                        const SizedBox(height: kToolbarHeight + 24),
                        Container(
                          padding: const EdgeInsets.all(20),
                          decoration: BoxDecoration(
                            color: Colors.white,
                            borderRadius: BorderRadius.circular(20),
                            boxShadow: AppShadows.sm,
                          ),
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(
                                cardName,
                                style: Theme.of(context).textTheme.titleMedium?.copyWith(
                                      color: AppColors.textPrimary,
                                      fontWeight: FontWeight.w700,
                                    ),
                              ),
                              const SizedBox(height: 12),
                              Text('Sessions: ${details.sessionsCount}'),
                              const SizedBox(height: 4),
                              Text('Total volume: ${details.totalVolume?.toStringAsFixed(1) ?? '-'}'),
                              const SizedBox(height: 4),
                              if (details.sessionsPerWeek != null)
                                Text('Sessions/week: ${details.sessionsPerWeek!.toStringAsFixed(1)}'),
                              if (details.sessionsPerWeek != null)
                                const SizedBox(height: 4),
                              if (details.planAdherence != null)
                                Text('Plan adherence: ${(details.planAdherence! * 100).round()}%'),
                              if (details.planAdherence != null)
                                const SizedBox(height: 4),
                              if (details.avgIntensity != null)
                                Text('Avg intensity: ${details.avgIntensity!.toStringAsFixed(1)}'),
                              if (details.avgIntensity != null)
                                const SizedBox(height: 4),
                              if (details.avgEffort != null)
                                Text('Avg effort (RPE): ${details.avgEffort!.toStringAsFixed(1)}'),
                              if (details.avgEffort != null)
                                const SizedBox(height: 4),
                              if (details.lastWorkoutAt != null)
                                Text('Last workout: ${df.format(details.lastWorkoutAt!)}'),
                              const SizedBox(height: 4),
                              if (details.daysSinceLastWorkout != null)
                                Text('Days since last workout: ${details.daysSinceLastWorkout}'),
                              const SizedBox(height: 8),
                              if (details.activePlanName != null)
                                Text('Active plan: ${details.activePlanName}'),
                              const SizedBox(height: 16),
                              const Text('Trend by week'),
                              const SizedBox(height: 8),
                              SizedBox(
                                height: 220,
                                child: _TrendChart(details: details),
                              ),
                              const SizedBox(height: 16),
                              if (details.rpeDistribution != null && details.rpeDistribution!.isNotEmpty) ...[
                                const Text('RPE distribution'),
                                SizedBox(height: 8),
                                SizedBox(
                                  height: 140,
                                  child: _RpeMiniChart(distribution: details.rpeDistribution),
                                ),
                                SizedBox(height: 16),
                              ],
                              ListView.separated(
                                shrinkWrap: true,
                                physics: const NeverScrollableScrollPhysics(),
                                itemCount: details.trend.length,
                                separatorBuilder: (_, __) => const Divider(height: 1),
                                itemBuilder: (context, index) {
                                  final t = details.trend[index];
                                  return ListTile(
                                    title: Text(df.format(t.periodStart)),
                                    subtitle: Text('Sessions: ${t.sessionsCount}'),
                                    trailing: Text('Vol: ${t.totalVolume.toStringAsFixed(1)}'),
                                  );
                                },
                              ),
                            ],
                          ),
                        ),
                      ],
                    ),
                  ),
                );
              },
            ),
            Align(
              alignment: Alignment.topCenter,
              child: FloatingHeaderBar(
                title: headerTitle,
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
    );
  }
}

class _TrendChart extends StatelessWidget {
  final AthleteDetailedAnalyticsModel details;

  const _TrendChart({required this.details});

  @override
  Widget build(BuildContext context) {
    if (details.trend.isEmpty) {
      return const Center(child: Text('No trend data'));
    }

    final df = DateFormat('dd.MM');
    final points = <PlanAnalyticsPoint>[];
    for (var i = 0; i < details.trend.length; i++) {
      final t = details.trend[i];
      points.add(
        PlanAnalyticsPoint(
          order: i,
          label: df.format(t.periodStart),
          values: {
            'total_volume': t.totalVolume,
            'sessions_count': t.sessionsCount.toDouble(),
          },
        ),
      );
    }

    return PlanAnalyticsChart(
      points: points,
      metricX: 'total_volume',
      metricY: 'total_volume',
      bottomLabelModulo: 2,
      emptyText: 'No trend data',
    );
  }
}

class _RpeMiniChart extends StatelessWidget {
  final Map<String, double>? distribution;

  const _RpeMiniChart({required this.distribution});

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
            BarChartRodData(
              toY: entries[i].value * 100,
              color: Theme.of(context).colorScheme.primary,
              width: 6,
            ),
          ],
        ),
      );
    }

    return SizedBox(
      height: 140,
      child: BarChart(
        BarChartData(
          barTouchData: BarTouchData(enabled: false),
          titlesData: FlTitlesData(
            leftTitles: AxisTitles(
              sideTitles: SideTitles(
                showTitles: true,
                reservedSize: 32,
                interval: 20,
                getTitlesWidget: (value, meta) => Text('${value.toInt()}%'),
              ),
            ),
            rightTitles: const AxisTitles(sideTitles: SideTitles(showTitles: false)),
            topTitles: const AxisTitles(sideTitles: SideTitles(showTitles: false)),
            bottomTitles: AxisTitles(
              sideTitles: SideTitles(
                showTitles: true,
                reservedSize: 22,
                getTitlesWidget: (value, meta) => Text(
                  value.toInt().toString(),
                  style: const TextStyle(fontSize: 10),
                ),
              ),
            ),
          ),
          gridData: FlGridData(show: false),
          borderData: FlBorderData(show: false),
          barGroups: barGroups,
        ),
      ),
    );
  }
}
