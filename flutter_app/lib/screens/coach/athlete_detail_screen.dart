import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/intl.dart';
import 'package:fl_chart/fl_chart.dart';
import 'package:workout_app/config/constants/theme_constants.dart';
import 'package:workout_app/models/crm_analytics.dart';
import 'package:workout_app/services/service_locator.dart' as sl;
import 'package:workout_app/widgets/floating_header_bar.dart';

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

    final spots = <FlSpot>[];
    final labels = <String>[];
    final df = DateFormat('dd.MM');

    for (var i = 0; i < details.trend.length; i++) {
      final t = details.trend[i];
      spots.add(FlSpot(i.toDouble(), t.totalVolume));
      labels.add(df.format(t.periodStart));
    }

    if (spots.isEmpty) {
      return const Center(child: Text('No trend data'));
    }

    final yValues = spots.map((e) => e.y).toList();
    final minY = yValues.reduce((a, b) => a < b ? a : b);
    final maxY = yValues.reduce((a, b) => a > b ? a : b);
    final span = (maxY - minY).abs();
    final double minBound = span == 0 ? (minY - 1) : (minY - span * 0.1);
    final double maxBound = span == 0 ? (maxY + 1) : (maxY + span * 0.1);

    return LineChart(
      LineChartData(
        minY: minBound,
        maxY: maxBound,
        titlesData: FlTitlesData(
          bottomTitles: AxisTitles(
            sideTitles: SideTitles(
              showTitles: true,
              interval: 1,
              getTitlesWidget: (value, meta) {
                final idx = value.toInt();
                if (idx < 0 || idx >= labels.length) {
                  return const SizedBox.shrink();
                }
                return SideTitleWidget(
                  meta: meta,
                  child: Text(labels[idx], style: const TextStyle(fontSize: 10)),
                );
              },
            ),
          ),
          leftTitles: AxisTitles(
            sideTitles: SideTitles(showTitles: true),
          ),
          topTitles: const AxisTitles(sideTitles: SideTitles(showTitles: false)),
          rightTitles: const AxisTitles(sideTitles: SideTitles(showTitles: false)),
        ),
        lineBarsData: [
          LineChartBarData(
            spots: spots,
            isCurved: true,
            color: Theme.of(context).colorScheme.primary,
            dotData: const FlDotData(show: false),
          ),
        ],
      ),
    );
  }
}
