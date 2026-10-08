import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:workout_app/l10n/app_localizations.dart';
import 'package:workout_app/providers/target_data_providers.dart';

class TriggerBuilder extends ConsumerStatefulWidget {
  final Map<String, dynamic> initial;
  final ValueChanged<Map<String, dynamic>> onChanged;
  const TriggerBuilder({super.key, required this.initial, required this.onChanged});

  @override
  ConsumerState<TriggerBuilder> createState() => _TriggerBuilderState();
}

class _TriggerBuilderState extends ConsumerState<TriggerBuilder> {
  late String _metric;

  final Set<int> _selectedExerciseIds = {};

  @override
  void initState() {
    super.initState();
    _metric = (widget.initial['metric'] ?? '').toString();

    if (widget.initial['exercise_id'] is int) {
      _selectedExerciseIds.add(widget.initial['exercise_id'] as int);
    }
    if (widget.initial['exercise_ids'] is List) {
      for (final e in (widget.initial['exercise_ids'] as List)) {
        final id = int.tryParse(e.toString());
        if (id != null) _selectedExerciseIds.add(id);
      }
    }
  }

  void _emit() {
    final map = <String, dynamic>{'metric': _metric};
    if (_selectedExerciseIds.isNotEmpty) {
      map['exercise_ids'] = _selectedExerciseIds.toList();
    }
    widget.onChanged(map);
  }

  String? _metricTooltip(String metric) {
    switch (metric) {
      case 'Readiness_Score':
        return 'Оценка готовности 1–10 (опционально). По умолчанию null; пользователь может указывать её после тренировки для применения коэффициентов к весам и правил.';
      case 'RPE_Session':
        return 'Оценка воспринимаемой нагрузки всей сессии (Session RPE). Полезно для авто-коррекции нагрузки.';
      case 'Total_Reps':
        return 'Суммарное количество повторений за выбранный период. Используйте с фильтром упражнений.';
      case 'e1RM':
        return 'Оценка одно-повторного максимума по производительности (estimated 1RM). Полезно для прогресса.';
      case 'Performance_Trend':
        return 'Тренд изменения показателей (рост/падение) за последние N окон.';
      case 'RPE_Delta_From_Plan':
        return 'Отклонение RPE от планового по сетам (факт − план). Используется для авторегулировки.';
      case 'Reps_Delta_From_Plan':
        return 'Отклонение повторов от плановых по сетам (факт − план). Для правил по недовыполнению/перевыполнению.';
    }
    return null;
  }

  String _metricHelp(String metric) {
    switch (metric) {
      case 'Readiness_Score':
        return 'Числовая оценка готовности (1–10). По умолчанию отсутствует (null); заполняется пользователем после тренировки. Кейс: значение < 6 держится 5 тренировок подряд — делоад мезоцикл. Для правил “подряд” используйте оператор holds_for.';
      case 'RPE_Session':
        return 'RPE сессии: число 1–10. Для правил “подряд” используйте оператор holds_for.';
      case 'Total_Reps':
        return 'Общее число повторений (целое). Можно ограничить конкретными упражнениями через выбор ниже.';
      case 'e1RM':
        return 'Оценка 1ПМ (кг). Сравнивайте числом или используйте тренд-операторы в условиях.';
      case 'Performance_Trend':
        return 'Для трендов используйте операторы: stagnates_for (n, epsilon_percent) или deviates_from_avg (n, value_percent, direction).';
      case 'RPE_Delta_From_Plan':
        return 'ΔRPE = факт − план (может быть отрицательным). Для “подряд тренировок” — holds_for, для “подряд подходов” — holds_for_sets.';
      case 'Reps_Delta_From_Plan':
        return 'Δповторов = факт − план (целое, может быть отрицательным). Для проверки внутри тренировки используйте holds_for_sets.';
    }
    return '';
  }

  bool get _metricNeedsExercises => _metric == 'Total_Reps' || _metric == 'e1RM' || _metric == 'Performance_Trend' || _metric == 'RPE_Delta_From_Plan' || _metric == 'Reps_Delta_From_Plan';

  Future<void> _openExercisePicker() async {
    final l10n = AppLocalizations.of(context);
    final defs = await ref.read(exerciseDefinitionsProvider.future);

    final temp = <int>{..._selectedExerciseIds};
    if (!mounted) return;
    String searchQuery = '';
    await showDialog(
      context: context,
      builder: (ctx) {
        return StatefulBuilder(
          builder: (ctx, setLocal) {
            final filtered = defs.where((d) => d.name.toLowerCase().contains(searchQuery.toLowerCase())).toList();
            return AlertDialog(
              title: const Text('Выбор упражнений'),
              content: SizedBox(
                width: 420,
                height: 480,
                child: Column(
                  children: [
                    TextField(
                      decoration: InputDecoration(
                        hintText: l10n.search,
                        prefixIcon: const Icon(Icons.search),
                      ),
                      onChanged: (v) => setLocal(() => searchQuery = v),
                    ),
                    const SizedBox(height: 12),
                    Expanded(
                      child: ListView.builder(
                        itemCount: filtered.length,
                        itemBuilder: (ctx, idx) {
                          final def = filtered[idx];
                          if (def.id == null) return const SizedBox.shrink();
                          final sel = temp.contains(def.id!);
                          return CheckboxListTile(
                            value: sel,
                            title: Text(def.name),
                            subtitle: Text(l10n.idPrefix(def.id.toString())),
                            onChanged: (v) {
                              setLocal(() {
                                if (v == true) {
                                  temp.add(def.id!);
                                } else {
                                  temp.remove(def.id!);
                                }
                              });
                            },
                          );
                        },
                      ),
                    ),
                  ],
                ),
              ),
              actions: [
                TextButton(onPressed: () => Navigator.of(ctx).pop(), child: Text(l10n.cancel)),
                FilledButton(
                  onPressed: () {
                    setState(() {
                      _selectedExerciseIds
                        ..clear()
                        ..addAll(temp);
                    });
                    _emit();
                    Navigator.of(ctx).pop();
                  },
                  child: Text(l10n.done),
                ),
              ],
            );
          },
        );
      },
    );
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    final defsAsync = ref.watch(exerciseDefinitionsProvider);

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        DropdownButtonFormField<String>(
          value: _metric.isEmpty ? null : _metric,
          items: [
            DropdownMenuItem(value: 'Readiness_Score', child: Text(l10n.macroTriggerMetricReadiness)),
            DropdownMenuItem(value: 'RPE_Session', child: Text(l10n.macroTriggerMetricRpeSession)),
            DropdownMenuItem(value: 'Total_Reps', child: Text(l10n.macroTriggerMetricTotalReps)),
            DropdownMenuItem(value: 'e1RM', child: Text(l10n.macroTriggerMetricE1rm)),
            DropdownMenuItem(value: 'Performance_Trend', child: Text(l10n.macroTriggerMetricPerformanceTrend)),
            DropdownMenuItem(value: 'RPE_Delta_From_Plan', child: Text(l10n.macroTriggerMetricRpeDelta)),
            DropdownMenuItem(value: 'Reps_Delta_From_Plan', child: Text(l10n.macroTriggerMetricRepsDelta)),
          ],
          decoration: InputDecoration(labelText: l10n.macroTriggerMetricLabel, border: const OutlineInputBorder()),
          onChanged: (v) {
            setState(() => _metric = v ?? '');
            _emit();
          },
          validator: (v) => (v == null || v.isEmpty) ? l10n.fieldRequired : null,
        ),
        if (_metric.isNotEmpty) ...[
          const SizedBox(height: 6),
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Icon(Icons.info_outline, size: 16, color: Colors.grey),
              const SizedBox(width: 6),
              Expanded(
                child: Text(
                  _metricTooltip(_metric) ?? '',
                  style: Theme.of(context).textTheme.bodySmall,
                ),
              ),
            ],
          ),
          const SizedBox(height: 6),
          Text(_metricHelp(_metric), style: Theme.of(context).textTheme.bodySmall),
        ],
        const SizedBox(height: 8),
        if (_metricNeedsExercises) ...[
          Text('Эта метрика применяется к выбранным упражнениям. Выберите одно или несколько.', style: Theme.of(context).textTheme.bodySmall),
          const SizedBox(height: 6),
          Row(
            children: [
              FilledButton.icon(
                onPressed: defsAsync.isLoading ? null : _openExercisePicker,
                icon: const Icon(Icons.list_alt),
                label: const Text('Выбрать упражнения'),
              ),
              const SizedBox(width: 12),
              defsAsync.isLoading ? const SizedBox(width: 18, height: 18, child: CircularProgressIndicator(strokeWidth: 2)) : const SizedBox.shrink(),
            ],
          ),
          const SizedBox(height: 8),
          if (_selectedExerciseIds.isNotEmpty)
            Wrap(
              spacing: 6,
              runSpacing: 6,
              children: _selectedExerciseIds
                  .map((id) => Chip(
                        label: Text(l10n.idPrefix(id.toString())),
                        onDeleted: () {
                          setState(() => _selectedExerciseIds.remove(id));
                          _emit();
                        },
                      ))
                  .toList(),
            ),
        ],
      ],
    );
  }
}
