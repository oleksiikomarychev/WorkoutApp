import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:workout_app/l10n/app_localizations.dart';
import 'package:table_calendar/table_calendar.dart';
import 'package:fl_chart/fl_chart.dart';
import 'package:intl/intl.dart';
import 'package:workout_app/services/analytics_service.dart';
import 'package:workout_app/services/plan_service.dart';
import 'package:workout_app/services/service_locator.dart';
import 'package:workout_app/widgets/loading_indicator.dart';
import 'package:workout_app/widgets/primary_app_bar.dart';
import 'package:workout_app/widgets/assistant_chat_host.dart';
import 'package:workout_app/widgets/error_message.dart';
import 'package:workout_app/widgets/empty_state.dart';

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

  Map<String, dynamic>? _data;

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
      final planService = ref.read(mesocycleServiceProvider);
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
        _error = AppLocalizations.of(context).errorLoadingActivePlan;
      });
    }
  }

  Future<Map<String, dynamic>> _buildChatContext() async {
    final nowIso = DateTime.now().toUtc().toIso8601String();
    return <String, dynamic>{
      'v': 1,
      'app': 'WorkoutApp',
      'screen': 'analytics',
      'role': 'athlete',
      'timestamp': nowIso,
      'entities': <String, dynamic>{
        'active_plan': _planId != null
            ? {'id': _planId, 'name': _planName}
            : null,
      },
    };
  }

  Future<void> _fetch() async {
    if (_metricX == null || _metricY == null) {
      setState(() => _error = AppLocalizations.of(context).selectTwoMetrics);
      return;
    }
    if (_planId == null) {
      setState(() => _error = AppLocalizations.of(context).activePlanNotFound);
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
        _error = AppLocalizations.of(context).errorLoadingData;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    final locale = Localizations.localeOf(context).languageCode;
    final df = DateFormat('dd.MM.yyyy', locale);

    return AssistantChatHost(
      contextBuilder: _buildChatContext,
      builder: (context, openChat) {
        return Scaffold(
          appBar: PrimaryAppBar(
            title: l10n.analyticsPlanTitle(_planName ?? ''),
            onTitleTap: openChat,
          ),
          body: RefreshIndicator(
            onRefresh: _loadActivePlan,
            child: _buildBody(l10n, locale, df),
          ),
        );
      },
    );
  }

  Widget _buildBody(AppLocalizations l10n, String locale, DateFormat df) {
    if (_loadingPlan) {
      return LoadingIndicator();
    }

    if (_error != null && _planId == null) {
      return ErrorMessage(message: _error!, onRetry: _loadActivePlan);
    }

    return SingleChildScrollView(
      physics: const AlwaysScrollableScrollPhysics(),
      padding: const EdgeInsets.all(12.0),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          TableCalendar(
            firstDay: DateTime.utc(2020, 1, 1),
            lastDay: DateTime.utc(2100, 12, 31),
            focusedDay: _focusedDay,
            calendarFormat: CalendarFormat.month,
            locale: locale,
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
          const SizedBox(height: 16),
          Row(
            children: [
              Expanded(child: _buildMetricPicker(l10n.axisX, true)),
              const SizedBox(width: 12),
              Expanded(child: _buildMetricPicker(l10n.axisY, false)),
            ],
          ),
          const SizedBox(height: 16),
          Row(
            children: [
              ElevatedButton(
                onPressed: _loading ? null : _fetch,
                child: Text(l10n.showChart),
              ),
              const SizedBox(width: 12),
              if (_rangeStart != null && _rangeEnd != null)
                Text('${df.format(_rangeStart!)} — ${df.format(_rangeEnd!)}'),
            ],
          ),
          const SizedBox(height: 16),
          if (_loading) LoadingIndicator(),
          if (_error != null && _data == null)
            ErrorMessage(message: _error!, onRetry: _fetch),
          const SizedBox(height: 8),
          SizedBox(height: 400, child: _buildChartArea()),
        ],
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
          items: _metrics
              .map(
                (m) => DropdownMenuItem(value: m, child: Text(_metricLabel(m))),
              )
              .toList(),
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
    final l10n = AppLocalizations.of(context);
    switch (m) {
      case 'volume':
        return l10n.metricVolumeKg;
      case 'effort':
        return l10n.metricEffortRpe;
      case 'kpsh':
        return l10n.metricKpsh;
      case 'reps':
        return l10n.metricReps;
      case '1rm':
        return l10n.metricOneRm;
      default:
        return m;
    }
  }

  Widget _buildChartArea() {
    final l10n = AppLocalizations.of(context);
    final locale = Localizations.localeOf(context).languageCode;
    if (_data == null) {
      return Center(child: Text(l10n.selectRangeAndMetrics));
    }
    final items = List<Map<String, dynamic>>.from(_data!["items"] ?? const []);
    final oneRm = List<Map<String, dynamic>>.from(_data!["one_rm"] ?? const []);
    final mx = _metricX;
    final my = _metricY;

    if (mx == null || my == null) {
      return const SizedBox();
    }

    if (mx == my) {
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
        return Center(child: Text(l10n.noDataForSelectedMetrics));
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
                    child: Text(
                      DateFormat('dd.MM', locale).format(d),
                      style: const TextStyle(fontSize: 10),
                    ),
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

    final scatters = <ScatterSpot>[];
    for (final it in items) {
      final vx = (it['values']?[mx] as num?)?.toDouble();
      double? vy;
      if (my == '1rm') {
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
      return Center(child: Text(l10n.noDataForSelectedMetrics));
    }

    return ScatterChart(
      ScatterChartData(
        scatterSpots: scatters,
        titlesData: FlTitlesData(
          bottomTitles: AxisTitles(
            sideTitles: SideTitles(showTitles: true, reservedSize: 28),
          ),
          leftTitles: AxisTitles(
            sideTitles: SideTitles(showTitles: true, reservedSize: 28),
          ),
        ),
      ),
    );
  }
}
