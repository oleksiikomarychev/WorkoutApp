import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:table_calendar/table_calendar.dart';
import 'package:fl_chart/fl_chart.dart';
import 'package:intl/intl.dart';
import 'package:workout_app/services/analytics_service.dart';
import 'package:workout_app/services/plan_service.dart';
import 'package:workout_app/services/service_locator.dart';

class AnalyticsScreen extends ConsumerStatefulWidget {
  const AnalyticsScreen({super.key});

  @override
  ConsumerState<AnalyticsScreen> createState() => _AnalyticsScreenState();
}

class _AnalyticsScreenState extends ConsumerState<AnalyticsScreen> {
  DateTime _focusedDay = DateTime.now();
  DateTime? _rangeStart;
  DateTime? _rangeEnd;
  RangeSelectionMode _rangeSelectionMode = RangeSelectionMode.toggledOn;

  final List<String> _metrics = const [
    'volume',
    'effort',
    'kpsh',
    'reps',
    '1rm',
  ];
  String? _metricX = 'volume';
  String? _metricY = 'effort';

  bool _loadingPlan = true;
  bool _loading = false;
  String? _error;
  int? _planId;
  String? _planName;

  Map<String, dynamic>? _data; // Response JSON

  @override
  void initState() {
    super.initState();
    _loadActivePlan();
  }

  Future<void> _loadActivePlan() async {
    setState(() {
      _loadingPlan = true;
      _error = null;
    });
    try {
      final planService = ref.read(mesocycleServiceProvider) /* placeholder to ensure provider tree */;
      final ps = PlanService(apiClient: ref.read(apiClientProvider));
      final ap = await ps.getActivePlan();
      if (!mounted) return;
      setState(() {
        _planId = ap?.id;
        _planName = ap?.calendarPlan.name;
        _loadingPlan = false;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _loadingPlan = false;
        _error = 'Не удалось получить активный план';
      });
    }
  }

  Future<void> _fetch() async {
    if (_metricX == null || _metricY == null) {
      setState(() => _error = 'Выберите две метрики');
      return;
    }
    if (_planId == null) {
      setState(() => _error = 'Активный план не найден');
      return;
    }
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final svc = ref.read(analyticsServiceProvider);
      final res = await svc.fetchMetrics(
        planId: _planId!,
        metricX: _metricX!,
        metricY: _metricY!,
        dateFrom: _rangeStart,
        dateTo: _rangeEnd,
      );
      if (!mounted) return;
      setState(() {
        _data = res;
        _loading = false;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _loading = false;
        _error = 'Ошибка загрузки данных';
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    final df = DateFormat('dd.MM.yyyy');

    return Scaffold(
      appBar: AppBar(
        title: Text('Аналитика плана ${_planName ?? ''}'.trim()),
      ),
      body: _loadingPlan
          ? const Center(child: CircularProgressIndicator())
          : Padding(
              padding: const EdgeInsets.all(12.0),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  // Calendar range selector
                  TableCalendar(
                    firstDay: DateTime.utc(2020, 1, 1),
                    lastDay: DateTime.utc(2100, 12, 31),
                    focusedDay: _focusedDay,
                    calendarFormat: CalendarFormat.month,
                    rangeSelectionMode: _rangeSelectionMode,
                    rangeStartDay: _rangeStart,
                    rangeEndDay: _rangeEnd,
                    onRangeSelected: (start, end, focusedDay) {
                      setState(() {
                        _focusedDay = focusedDay;
                        _rangeStart = start;
                        _rangeEnd = end;
                        _rangeSelectionMode = RangeSelectionMode.toggledOn;
                      });
                    },
                    onPageChanged: (fd) => _focusedDay = fd,
                  ),
                  const SizedBox(height: 8),
                  Row(
                    children: [
                      Expanded(child: _buildMetricPicker('Ось X', true)),
                      const SizedBox(width: 12),
                      Expanded(child: _buildMetricPicker('Ось Y', false)),
                    ],
                  ),
                  const SizedBox(height: 8),
                  Row(
                    children: [
                      ElevatedButton(
                        onPressed: _loading ? null : _fetch,
                        child: const Text('Показать график'),
                      ),
                      const SizedBox(width: 12),
                      if (_rangeStart != null && _rangeEnd != null)
                        Text('${df.format(_rangeStart!)} — ${df.format(_rangeEnd!)}'),
                    ],
                  ),
                  const SizedBox(height: 12),
                  if (_loading) const LinearProgressIndicator(),
                  if (_error != null) Text(_error!, style: const TextStyle(color: Colors.red)),
                  const SizedBox(height: 8),
                  Expanded(
                    child: _buildChartArea(),
                  ),
                ],
              ),
            ),
    );
  }

  Widget _buildMetricPicker(String label, bool isX) {
    return InputDecorator(
      decoration: InputDecoration(
        labelText: label,
        border: const OutlineInputBorder(),
        isDense: true,
      ),
      child: DropdownButtonHideUnderline(
        child: DropdownButton<String>(
          value: isX ? _metricX : _metricY,
          items: _metrics.map((m) => DropdownMenuItem(value: m, child: Text(_metricLabel(m)))).toList(),
          onChanged: (v) {
            setState(() {
              if (isX) {
                _metricX = v;
              } else {
                _metricY = v;
              }
            });
          },
        ),
      ),
    );
  }

  String _metricLabel(String m) {
    switch (m) {
      case 'volume':
        return 'Объем (кг)';
      case 'effort':
        return 'Усилие (RPE)';
      case 'kpsh':
        return 'КПШ';
      case 'reps':
        return 'Повторы';
      case '1rm':
        return '1RM';
      default:
        return m;
    }
  }

  Widget _buildChartArea() {
    if (_data == null) {
      return const Center(child: Text('Выберите диапазон и метрики'));
    }
    final items = List<Map<String, dynamic>>.from(_data!["items"] ?? const []);
    final oneRm = List<Map<String, dynamic>>.from(_data!["one_rm"] ?? const []);
    final mx = _metricX;
    final my = _metricY;

    if (mx == null || my == null) {
      return const SizedBox();
    }

    // If the same metric selected for X and Y -> time series line chart of that metric
    if (mx == my) {
      // Build date -> value series for the chosen metric (or 1rm series)
      final is1rm = mx == '1rm';
      final points = <FlSpot>[];
      final List<DateTime> dates = [];
      final Map<String, double> dayValues = {};

      if (is1rm) {
        for (final e in oneRm) {
          final dstr = e['date'] as String?;
          final v = (e['value'] as num?)?.toDouble();
          if (dstr == null || v == null) continue;
          dayValues[dstr] = v;
        }
      } else {
        for (final it in items) {
          final dstr = it['date'] as String?;
          if (dstr == null) continue;
          final val = (it['values']?[mx] as num?)?.toDouble();
          if (val == null) continue;
          dayValues[dstr] = val;
        }
      }

      final sorted = dayValues.entries.toList()
        ..sort((a, b) => a.key.compareTo(b.key));
      for (var i = 0; i < sorted.length; i++) {
        dates.add(DateTime.parse(sorted[i].key));
        points.add(FlSpot(i.toDouble(), sorted[i].value));
      }
      if (points.isEmpty) {
        return const Center(child: Text('Нет данных для выбранных метрик'));
      }
      return LineChart(
        LineChartData(
          titlesData: FlTitlesData(
            bottomTitles: AxisTitles(
              sideTitles: SideTitles(
                showTitles: true,
                interval: 1,
                getTitlesWidget: (value, meta) {
                  final idx = value.toInt();
                  if (idx < 0 || idx >= dates.length) return const SizedBox();
                  final d = dates[idx];
                  return SideTitleWidget(
                    meta: meta,
                    child: Text(DateFormat('dd.MM').format(d), style: const TextStyle(fontSize: 10)),
                  );
                },
              ),
            ),
            leftTitles: AxisTitles(sideTitles: SideTitles(showTitles: true)),
          ),
          lineBarsData: [
            LineChartBarData(
              spots: points,
              isCurved: true,
              color: Colors.blue,
              dotData: FlDotData(show: false),
            ),
          ],
        ),
      );
    }

    // Otherwise: scatter chart of correlation (X vs Y)
    final scatters = <ScatterSpot>[];
    for (final it in items) {
      final vx = (it['values']?[mx] as num?)?.toDouble();
      double? vy;
      if (my == '1rm') {
        // Join by date
        final dstr = it['date'] as String?;
        if (dstr != null) {
          final match = oneRm.firstWhere(
            (e) => e['date'] == dstr,
            orElse: () => const {},
          );
          vy = (match['value'] as num?)?.toDouble();
        }
      } else {
        vy = (it['values']?[my] as num?)?.toDouble();
      }
      if (vx != null && vy != null) {
        scatters.add(ScatterSpot(vx, vy));
      }
    }
    if (scatters.isEmpty) {
      return const Center(child: Text('Нет данных для выбранных метрик'));
    }

    return ScatterChart(
      ScatterChartData(
        scatterSpots: scatters,
        titlesData: FlTitlesData(
          bottomTitles: AxisTitles(sideTitles: SideTitles(showTitles: true, reservedSize: 28)),
          leftTitles: AxisTitles(sideTitles: SideTitles(showTitles: true, reservedSize: 28)),
        ),
      ),
    );
  }
}
