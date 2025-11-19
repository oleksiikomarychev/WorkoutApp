import 'dart:math' as math;

import 'package:fl_chart/fl_chart.dart';
import 'package:flutter/material.dart';

class PlanAnalyticsPoint {
  final int order;
  final String label;
  final Map<String, double> values;

  const PlanAnalyticsPoint({
    required this.order,
    required this.label,
    required this.values,
  });
}

class PlanAnalyticsChart extends StatelessWidget {
  final List<PlanAnalyticsPoint> points;
  final String metricX;
  final String metricY;
  final int bottomLabelModulo;
  final bool showScatterAxisTitles;
  final String emptyText;

  const PlanAnalyticsChart({
    super.key,
    required this.points,
    required this.metricX,
    required this.metricY,
    this.bottomLabelModulo = 2,
    this.showScatterAxisTitles = true,
    this.emptyText = 'Нет данных для плана',
  });

  @override
  Widget build(BuildContext context) {
    if (points.isEmpty) {
      return Center(child: Text(emptyText));
    }
    if (metricX == metricY) {
      return _buildLineChart();
    }
    return _buildScatterChart();
  }

  Widget _buildLineChart() {
    final spots = <FlSpot>[];
    final labels = <String>[];
    for (var i = 0; i < points.length; i++) {
      final point = points[i];
      final value = point.values[metricX] ?? 0;
      spots.add(FlSpot(i.toDouble(), value));
      labels.add(point.label);
    }
    if (spots.isEmpty) {
      return Center(child: Text(emptyText));
    }

    final yValues = spots.map((e) => e.y).toList();
    final minY = yValues.reduce(math.min);
    final maxY = yValues.reduce(math.max);
    final span = maxY - minY;
    final yInterval = _computeYInterval(span);
    final minBound = span == 0
        ? minY - yInterval
        : (minY / yInterval).floor() * yInterval - yInterval;
    final maxBound = span == 0
        ? maxY + yInterval
        : (maxY / yInterval).ceil() * yInterval + yInterval;
    final adjustedMin = minBound == maxBound ? minBound : math.min(minBound, maxBound);
    final adjustedMax = minBound == maxBound ? minBound + yInterval : math.max(minBound, maxBound);

    return LineChart(
      LineChartData(
        minY: adjustedMin,
        maxY: adjustedMax,
        titlesData: FlTitlesData(
          bottomTitles: AxisTitles(
            sideTitles: SideTitles(
              showTitles: true,
              interval: 1,
              getTitlesWidget: (value, meta) {
                final idx = value.toInt();
                if (idx < 0 || idx >= labels.length) return const SizedBox.shrink();
                if (idx % bottomLabelModulo != 0) return const SizedBox.shrink();
                return SideTitleWidget(
                  meta: meta,
                  child: Text(labels[idx], style: const TextStyle(fontSize: 10)),
                );
              },
            ),
          ),
          leftTitles: AxisTitles(
            sideTitles: SideTitles(
              showTitles: true,
              interval: yInterval,
              reservedSize: 44,
              getTitlesWidget: (value, meta) => SideTitleWidget(
                meta: meta,
                child: Text(value.toStringAsFixed(0), style: const TextStyle(fontSize: 10)),
              ),
            ),
          ),
          topTitles: const AxisTitles(sideTitles: SideTitles(showTitles: false)),
          rightTitles: const AxisTitles(sideTitles: SideTitles(showTitles: false)),
        ),
        lineTouchData: LineTouchData(
          touchTooltipData: LineTouchTooltipData(
            getTooltipColor: (touchedSpot) => Colors.black.withOpacity(0.75),
            getTooltipItems: (touchedSpots) => touchedSpots
                .map(
                  (spot) => LineTooltipItem(
                    spot.y.toStringAsFixed(2),
                    const TextStyle(color: Colors.white, fontWeight: FontWeight.w600),
                  ),
                )
                .toList(),
          ),
        ),
        lineBarsData: [
          LineChartBarData(
            spots: spots,
            isCurved: true,
            color: Colors.blue,
            dotData: const FlDotData(show: false),
          ),
        ],
      ),
    );
  }

  Widget _buildScatterChart() {
    final scatterSpots = <ScatterSpot>[];
    for (final point in points) {
      final vx = point.values[metricX];
      final vy = point.values[metricY];
      if (vx != null && vy != null) {
        scatterSpots.add(ScatterSpot(vx, vy));
      }
    }
    if (scatterSpots.isEmpty) {
      return Center(child: Text(emptyText));
    }

    return ScatterChart(
      ScatterChartData(
        scatterSpots: scatterSpots,
        titlesData: FlTitlesData(
          bottomTitles: AxisTitles(
            sideTitles: SideTitles(
              showTitles: showScatterAxisTitles,
              reservedSize: showScatterAxisTitles ? 28 : 10,
              getTitlesWidget: (value, meta) => !showScatterAxisTitles
                  ? const SizedBox.shrink()
                  : SideTitleWidget(
                      meta: meta,
                      child: Text(value.toStringAsFixed(2), style: const TextStyle(fontSize: 10)),
                    ),
            ),
          ),
          leftTitles: AxisTitles(
            sideTitles: SideTitles(
              showTitles: showScatterAxisTitles,
              reservedSize: showScatterAxisTitles ? 40 : 10,
              getTitlesWidget: (value, meta) => !showScatterAxisTitles
                  ? const SizedBox.shrink()
                  : SideTitleWidget(
                      meta: meta,
                      child: Text(value.toStringAsFixed(2), style: const TextStyle(fontSize: 10)),
                    ),
            ),
          ),
          topTitles: const AxisTitles(sideTitles: SideTitles(showTitles: false)),
          rightTitles: const AxisTitles(sideTitles: SideTitles(showTitles: false)),
        ),
      ),
    );
  }

  double _computeYInterval(double span) {
    if (span == 0) return 1.0;
    final rawInterval = span / 5;
    if (rawInterval < 1) return 1.0;
    final exponent = (math.log(rawInterval) / math.ln10).floor();
    final magnitude = math.pow(10, exponent).toDouble();
    final normalized = rawInterval / magnitude;
    double niceNormalized;
    if (normalized <= 1) {
      niceNormalized = 1;
    } else if (normalized <= 2) {
      niceNormalized = 2;
    } else if (normalized <= 5) {
      niceNormalized = 5;
    } else {
      niceNormalized = 10;
    }
    return niceNormalized * magnitude;
  }
}
