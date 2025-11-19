import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:workout_app/providers/target_data_providers.dart';

class TriggerBuilder extends ConsumerStatefulWidget {
  final Map<String, dynamic> initial;
  final ValueChanged<Map<String, dynamic>> onChanged;
  const TriggerBuilder({super.key, required this.initial, required this.onChanged});

  @override
  ConsumerState<TriggerBuilder> createState() => _TriggerBuilderState();
}

class _TriggerBuilderState extends ConsumerState<TriggerBuilder> {
  final _formKey = GlobalKey<FormState>();
  late String _metric;
  // Selected exercises
  final Set<int> _selectedExerciseIds = {};

  @override
  void initState() {
    super.initState();
    _metric = (widget.initial['metric'] ?? '').toString();
    // Backward-compat: init from exercise_id or exercise_ids
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
    final defs = await ref.read(exerciseDefinitionsProvider.future);

    final temp = <int>{..._selectedExerciseIds};
    if (!mounted) return;
    await showDialog(
      context: context,
      builder: (ctx) {
        return StatefulBuilder(
          builder: (ctx, setLocal) {
            return AlertDialog(
              title: const Text('Выбор упражнений'),
              content: SizedBox(
                width: 420,
                height: 480,
                child: defs.isEmpty
                    ? const Center(child: CircularProgressIndicator())
                    : ListView.builder(
                        itemCount: defs.length,
                        itemBuilder: (_, i) {
                          final d = defs[i];
                          final int? id = d.id;
                          if (id == null) return const SizedBox.shrink();
                          final selected = temp.contains(id);
                          final subtitle = [
                            if ((d.movementType ?? '').isNotEmpty) d.movementType,
                            if ((d.region ?? '').isNotEmpty) d.region,
                            if ((d.muscleGroup ?? '').isNotEmpty) d.muscleGroup,
                            if ((d.equipment ?? '').isNotEmpty) d.equipment,
                          ].whereType<String>().join(' • ');
                          return CheckboxListTile(
                            value: selected,
                            onChanged: (v) => setLocal(() {
                              if (v == true) {
                                temp.add(id);
                              } else {
                                temp.remove(id);
                              }
                            }),
                            title: Text(d.name ?? 'Exercise #$id'),
                            subtitle: subtitle.isEmpty ? null : Text(subtitle),
                          );
                        },
                      ),
              ),
              actions: [
                TextButton(onPressed: () => Navigator.of(ctx).pop(), child: const Text('Отмена')),
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
                  child: const Text('Готово'),
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
    final defsAsync = ref.watch(exerciseDefinitionsProvider);
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        DropdownButtonFormField<String>(
          value: _metric.isEmpty ? null : _metric,
          items: const [
            DropdownMenuItem(value: 'Readiness_Score', child: Text('Готовность (тренировка)')),
            DropdownMenuItem(value: 'RPE_Session', child: Text('RPE сессии')),
            DropdownMenuItem(value: 'Total_Reps', child: Text('Количество повторений')),
            DropdownMenuItem(value: 'e1RM', child: Text('Оценка 1ПМ (e1RM)')),
            DropdownMenuItem(value: 'Performance_Trend', child: Text('Тренд прогресса')),
            DropdownMenuItem(value: 'RPE_Delta_From_Plan', child: Text('RPE — отклонение от плана')),
            DropdownMenuItem(value: 'Reps_Delta_From_Plan', child: Text('Повторы — отклонение от плана')),
          ],
          decoration: const InputDecoration(labelText: 'Метрика', border: OutlineInputBorder()),
          onChanged: (v) {
            setState(() => _metric = v ?? '');
            _emit();
          },
          validator: (v) => (v == null || v.isEmpty) ? 'Required' : null,
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
                        label: Text('ID $id'),
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
