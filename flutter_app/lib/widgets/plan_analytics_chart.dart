import 'dart:math' as math;

import 'package:fl_chart/fl_chart.dart';
import 'package:flutter/material.dart';

class PlanAnalyticsPoint {
  final int order;
  final String label;
  final Map<String, double> values;
  final Map<String, double>? actualValues;

  const PlanAnalyticsPoint({
    required this.order,
    required this.label,
    required this.values,
    this.actualValues,
  });
}

class PlanAnalyticsLineSeries {
  final String metric;
  final String? name;
  final Color color;
  final bool useActual;

  const PlanAnalyticsLineSeries({
    required this.metric,
    this.name,
    required this.color,
    this.useActual = false,
  });
}

class PlanAnalyticsScatterSeries {
  final String metricX;
  final String metricY;
  final String? name;
  final Color color;
  final bool useActual;

  const PlanAnalyticsScatterSeries({
    required this.metricX,
    required this.metricY,
    this.name,
    required this.color,
    this.useActual = false,
  });
}

class PlanAnalyticsChart extends StatelessWidget {
  final List<PlanAnalyticsPoint> points;
  final String metricX;
  final String metricY;
  final List<PlanAnalyticsLineSeries>? lineSeries;
  final List<PlanAnalyticsScatterSeries>? scatterSeries;
  final int? bottomLabelModulo;
  final bool showScatterAxisTitles;
  final String emptyText;

  const PlanAnalyticsChart({
    super.key,
    required this.points,
    required this.metricX,
    required this.metricY,
    this.lineSeries,
    this.scatterSeries,
    this.bottomLabelModulo,
    this.showScatterAxisTitles = true,
    this.emptyText = 'Нет данных для плана',
  });

  @override
  Widget build(BuildContext context) {
    if (points.isEmpty) {
      return Center(child: Text(emptyText));
    }

    final multi = lineSeries != null && lineSeries!.isNotEmpty;
    if (multi) {
      return _buildMultiLineChart();
    }

    final multiScatter = scatterSeries != null && scatterSeries!.isNotEmpty;
    if (multiScatter) {
      return _buildMultiScatterChart();
    }

    if (metricX == metricY) {
      return _buildLineChart();
    }
    return _buildScatterChart();
  }

  Widget _buildMultiLineChart() {
    final series = lineSeries ?? const <PlanAnalyticsLineSeries>[];
    final labels = <String>[];

    final bars = <LineChartBarData>[];
    final barLabels = <String>[];
    final allY = <double>[];

    for (var i = 0; i < points.length; i++) {
      labels.add(points[i].label);
    }

    for (final s in series) {
      final spots = <FlSpot>[];
      for (var i = 0; i < points.length; i++) {
        final p = points[i];
        final source = s.useActual ? (p.actualValues ?? const {}) : p.values;
        final v = source[s.metric];
        if (v != null && v != 0.0) {
          spots.add(FlSpot(i.toDouble(), v));
          allY.add(v);
        }
      }
      if (spots.isEmpty) continue;
      barLabels.add(s.name ?? s.metric);
      bars.add(
        LineChartBarData(
          spots: spots,
          isCurved: spots.length >= 3,
          color: s.color,
          dotData: FlDotData(show: spots.length < 2),
          belowBarData: BarAreaData(show: false),
        ),
      );
    }

    if (bars.isEmpty) {
      return Center(child: Text(emptyText));
    }

    final minY = allY.reduce(math.min);
    final maxY = allY.reduce(math.max);
    final span = maxY - minY;
    final yInterval = _computeYInterval(span);
    final minBound = span == 0
        ? minY - yInterval
        : (minY / yInterval).floor() * yInterval - yInterval;
    final maxBound = span == 0
        ? maxY + yInterval
        : (maxY / yInterval).ceil() * yInterval + yInterval;
    final adjustedMin = minBound == maxBound
        ? minBound
        : math.min(minBound, maxBound);
    final adjustedMax = minBound == maxBound
        ? minBound + yInterval
        : math.max(minBound, maxBound);

    final maxLabels = 6;
    final effectiveModulo = math.max(
      1,
      bottomLabelModulo ?? (labels.length / maxLabels).ceil(),
    );

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
                if (idx < 0 || idx >= labels.length)
                  return const SizedBox.shrink();
                if (idx % effectiveModulo != 0) return const SizedBox.shrink();
                return SideTitleWidget(
                  meta: meta,
                  child: Text(
                    labels[idx],
                    style: const TextStyle(fontSize: 10),
                  ),
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
                child: Text(
                  value.toStringAsFixed(0),
                  style: const TextStyle(fontSize: 10),
                ),
              ),
            ),
          ),
          topTitles: const AxisTitles(
            sideTitles: SideTitles(showTitles: false),
          ),
          rightTitles: const AxisTitles(
            sideTitles: SideTitles(showTitles: false),
          ),
        ),
        lineTouchData: LineTouchData(
          touchTooltipData: LineTouchTooltipData(
            getTooltipColor: (touchedSpot) => Colors.black.withOpacity(0.75),
            getTooltipItems: (touchedSpots) {
              return touchedSpots.map((spot) {
                final name =
                    (spot.barIndex >= 0 && spot.barIndex < barLabels.length)
                    ? barLabels[spot.barIndex]
                    : '';
                return LineTooltipItem(
                  '$name: ${spot.y.toStringAsFixed(2)}',
                  TextStyle(color: Colors.white, fontWeight: FontWeight.w600),
                );
              }).toList();
            },
          ),
        ),
        lineBarsData: bars,
      ),
    );
  }

  Widget _buildMultiScatterChart() {
    final series = scatterSeries ?? const <PlanAnalyticsScatterSeries>[];
    final scatterSpots = <ScatterSpot>[];

    for (final s in series) {
      final xs = <double>[];
      final ys = <double>[];
      for (final point in points) {
        final source = s.useActual
            ? (point.actualValues ?? const {})
            : point.values;
        final vx = source[s.metricX];
        final vy = source[s.metricY];
        if (vx != null && vx != 0.0) xs.add(vx);
        if (vy != null && vy != 0.0) ys.add(vy);
      }
      final n = math.min(xs.length, ys.length);
      for (var i = 0; i < n; i++) {
        scatterSpots.add(
          ScatterSpot(
            xs[i],
            ys[i],
            dotPainter: FlDotCirclePainter(color: s.color, radius: 4),
          ),
        );
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
                      child: Text(
                        value.toStringAsFixed(2),
                        style: const TextStyle(fontSize: 10),
                      ),
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
                      child: Text(
                        value.toStringAsFixed(2),
                        style: const TextStyle(fontSize: 10),
                      ),
                    ),
            ),
          ),
          topTitles: const AxisTitles(
            sideTitles: SideTitles(showTitles: false),
          ),
          rightTitles: const AxisTitles(
            sideTitles: SideTitles(showTitles: false),
          ),
        ),
      ),
    );
  }

  Widget _buildLineChart() {
    final spots = <FlSpot>[];
    final actualSpots = <FlSpot>[];
    final labels = <String>[];
    final allY = <double>[];

    for (var i = 0; i < points.length; i++) {
      final point = points[i];
      labels.add(point.label);

      final value = point.values[metricX];
      if (value != null && value != 0.0) {
        spots.add(FlSpot(i.toDouble(), value));
        allY.add(value);
      }

      final actualValue = point.actualValues?[metricX];
      if (actualValue != null && actualValue != 0.0) {
        actualSpots.add(FlSpot(i.toDouble(), actualValue));
        allY.add(actualValue);
      }
    }

    if (spots.isEmpty && actualSpots.isEmpty) {
      return Center(child: Text(emptyText));
    }

    final minY = allY.reduce(math.min);
    final maxY = allY.reduce(math.max);
    final span = maxY - minY;
    final yInterval = _computeYInterval(span);
    final minBound = span == 0
        ? minY - yInterval
        : (minY / yInterval).floor() * yInterval - yInterval;
    final maxBound = span == 0
        ? maxY + yInterval
        : (maxY / yInterval).ceil() * yInterval + yInterval;
    final adjustedMin = minBound == maxBound
        ? minBound
        : math.min(minBound, maxBound);
    final adjustedMax = minBound == maxBound
        ? minBound + yInterval
        : math.max(minBound, maxBound);

    final maxLabels = 6;
    final effectiveModulo = math.max(
      1,
      bottomLabelModulo ?? (labels.length / maxLabels).ceil(),
    );

    final bars = <LineChartBarData>[];
    if (spots.isNotEmpty) {
      bars.add(
        LineChartBarData(
          spots: spots,
          isCurved: spots.length >= 3,
          color: Colors.blue,
          dotData: FlDotData(show: spots.length < 2),
          belowBarData: BarAreaData(show: false),
        ),
      );
    }
    if (actualSpots.isNotEmpty) {
      bars.add(
        LineChartBarData(
          spots: actualSpots,
          isCurved: actualSpots.length >= 3,
          color: Colors.green,
          dotData: FlDotData(show: actualSpots.length < 2),
          belowBarData: BarAreaData(show: false),
        ),
      );
    }

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
                if (idx < 0 || idx >= labels.length)
                  return const SizedBox.shrink();
                if (idx % effectiveModulo != 0) return const SizedBox.shrink();
                return SideTitleWidget(
                  meta: meta,
                  child: Text(
                    labels[idx],
                    style: const TextStyle(fontSize: 10),
                  ),
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
                child: Text(
                  value.toStringAsFixed(0),
                  style: const TextStyle(fontSize: 10),
                ),
              ),
            ),
          ),
          topTitles: const AxisTitles(
            sideTitles: SideTitles(showTitles: false),
          ),
          rightTitles: const AxisTitles(
            sideTitles: SideTitles(showTitles: false),
          ),
        ),
        lineBarsData: bars,
      ),
    );
  }

  Widget _buildScatterChart() {
    final spots = <ScatterSpot>[];
    final actualSpots = <ScatterSpot>[];
    final allX = <double>[];
    final allY = <double>[];

    final xs = <double>[];
    final ys = <double>[];
    final axs = <double>[];
    final ays = <double>[];

    for (final point in points) {
      final xValue = point.values[metricX];
      if (xValue != null && xValue != 0.0) xs.add(xValue);
      final yValue = point.values[metricY];
      if (yValue != null && yValue != 0.0) ys.add(yValue);

      final ax = point.actualValues?[metricX];
      if (ax != null && ax != 0.0) axs.add(ax);
      final ay = point.actualValues?[metricY];
      if (ay != null && ay != 0.0) ays.add(ay);
    }

    final n = math.min(xs.length, ys.length);
    for (var i = 0; i < n; i++) {
      spots.add(ScatterSpot(xs[i], ys[i]));
      allX.add(xs[i]);
      allY.add(ys[i]);
    }

    final an = math.min(axs.length, ays.length);
    for (var i = 0; i < an; i++) {
      actualSpots.add(
        ScatterSpot(
          axs[i],
          ays[i],
          dotPainter: FlDotCirclePainter(color: Colors.redAccent, radius: 4),
        ),
      );
      allX.add(axs[i]);
      allY.add(ays[i]);
    }

    if (spots.isEmpty && actualSpots.isEmpty) {
      return Center(child: Text(emptyText));
    }

    final minX = allX.reduce(math.min);
    final maxX = allX.reduce(math.max);
    final minY = allY.reduce(math.min);
    final maxY = allY.reduce(math.max);
    final spanX = maxX - minX;
    final spanY = maxY - minY;
    final xInterval = _computeYInterval(spanX);
    final yInterval = _computeYInterval(spanY);

    return ScatterChart(
      ScatterChartData(
        scatterSpots: [...spots, ...actualSpots],
        minX: minX - xInterval,
        maxX: maxX + xInterval,
        minY: minY - yInterval,
        maxY: maxY + yInterval,
        titlesData: FlTitlesData(
          bottomTitles: AxisTitles(
            sideTitles: SideTitles(
              showTitles: showScatterAxisTitles,
              reservedSize: showScatterAxisTitles ? 28 : 10,
              getTitlesWidget: (value, meta) => !showScatterAxisTitles
                  ? const SizedBox.shrink()
                  : SideTitleWidget(
                      meta: meta,
                      child: Text(
                        value.toStringAsFixed(2),
                        style: const TextStyle(fontSize: 10),
                      ),
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
                      child: Text(
                        value.toStringAsFixed(2),
                        style: const TextStyle(fontSize: 10),
                      ),
                    ),
            ),
          ),
          topTitles: const AxisTitles(
            sideTitles: SideTitles(showTitles: false),
          ),
          rightTitles: const AxisTitles(
            sideTitles: SideTitles(showTitles: false),
          ),
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
