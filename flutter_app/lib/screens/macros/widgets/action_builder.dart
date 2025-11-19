import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:workout_app/providers/target_data_providers.dart';
import 'package:workout_app/providers/plan_providers.dart';
import 'package:workout_app/screens/macros/widgets/target_selector.dart';
import 'package:workout_app/providers/template_providers.dart';
import 'package:workout_app/screens/macros/widgets/workout_picker.dart';

class ActionBuilder extends ConsumerStatefulWidget {
  final Map<String, dynamic> initial;
  final ValueChanged<Map<String, dynamic>> onChanged;
  const ActionBuilder({super.key, required this.initial, required this.onChanged});

  @override
  ConsumerState<ActionBuilder> createState() => _ActionBuilderState();
}

class _ActionBuilderState extends ConsumerState<ActionBuilder> {
  String _type = '';
  String _mode = '';
  String _value = '';
  Map<String, dynamic>? _target;

  String _mesoMode = '';
  String _templateId = '';
  String _sourceMesocycleId = '';
  String _weeks = '';
  String _daysInMicro = '';
  final Set<int> _restDays = {};
  final Set<String> _mt = {};
  final Set<String> _rg = {};
  final Set<String> _mg = {};
  final Set<String> _eq = {};
  String _placement = 'Append_To_End';
  int? _anchorWorkoutId;
  String? _anchorWorkoutName;
  int? _anchorPlanOrderIndex;
  String _mesocycleIndex = '1';
  String _conflict = 'Shift_Forward';

  @override
  void initState() {
    super.initState();
    _type = (widget.initial['type'] ?? '').toString();
    final params = (widget.initial['params'] as Map?) ?? {};
    _mode = (params['mode'] ?? '').toString();
    if (params['value'] != null) _value = params['value'].toString();
    _target = (widget.initial['target'] as Map?)?.cast<String, dynamic>();
    _mesoMode = (params['mode'] ?? '').toString();
    if (params['template_id'] != null) _templateId = params['template_id'].toString();
    if (params['source_mesocycle_id'] != null) _sourceMesocycleId = params['source_mesocycle_id'].toString();
    if (params['duration_weeks'] != null) _weeks = params['duration_weeks'].toString();
    if (params['days_in_microcycle'] != null) _daysInMicro = params['days_in_microcycle'].toString();
    if (params['rest_days'] is List) {
      for (final e in (params['rest_days'] as List)) {
        final n = int.tryParse(e.toString());
        if (n != null) _restDays.add(n);
      }
    }
    final focus = (params['default_focus_tags'] as Map?)?.cast<String, dynamic>() ?? const {};
    void fill(Set<String> s, dynamic v) {
      if (v is String && v.isNotEmpty) s.add(v.toLowerCase());
      if (v is List) {
        for (final e in v) {
          final t = e?.toString();
          if (t != null && t.isNotEmpty) s.add(t.toLowerCase());
        }
      }
    }
    fill(_mt, focus['movement_type']);
    fill(_rg, focus['region']);
    fill(_mg, focus['muscle_group']);
    fill(_eq, focus['equipment']);
    final placement = (params['placement'] as Map?)?.cast<String, dynamic>() ?? const {};
    _placement = (placement['mode'] ?? _placement).toString();
    if (placement['plan_order_index'] != null) {
      try {
        _anchorPlanOrderIndex = placement['plan_order_index'] is int
            ? placement['plan_order_index'] as int
            : int.tryParse(placement['plan_order_index'].toString());
      } catch (_) {}
    }
    if (placement['mesocycle_index'] != null) {
      final idx0 = int.tryParse(placement['mesocycle_index'].toString());
      if (idx0 != null) _mesocycleIndex = (idx0 + 1).toString(); // convert 0-based -> 1-based for UI
    }
    _conflict = (params['on_conflict'] ?? _conflict).toString();
  }

  void _emit() {
    final map = <String, dynamic>{'type': _type, 'params': {}};
    if (_type == 'Inject_Mesocycle') {
      if (_mesoMode.isNotEmpty) map['params']['mode'] = _mesoMode;
      if (_mesoMode == 'by_Template') {
        if (_templateId.isNotEmpty) {
          final id = int.tryParse(_templateId);
          map['params']['template_id'] = id ?? _templateId;
        }
      } else if (_mesoMode == 'by_Existing') {
        if (_sourceMesocycleId.isNotEmpty) {
          final id = int.tryParse(_sourceMesocycleId);
          map['params']['source_mesocycle_id'] = id ?? _sourceMesocycleId;
        }
      } else if (_mesoMode == 'Create_Inline') {
        if (_weeks.isNotEmpty) map['params']['duration_weeks'] = int.tryParse(_weeks) ?? _weeks;
        if (_daysInMicro.isNotEmpty) map['params']['days_in_microcycle'] = int.tryParse(_daysInMicro) ?? _daysInMicro;
        if (_restDays.isNotEmpty) map['params']['rest_days'] = _restDays.toList()..sort();
        final focus = <String, dynamic>{};
        if (_mt.isNotEmpty) focus['movement_type'] = _mt.toList();
        if (_rg.isNotEmpty) focus['region'] = _rg.toList();
        if (_mg.isNotEmpty) focus['muscle_group'] = _mg.toList();
        if (_eq.isNotEmpty) focus['equipment'] = _eq.toList();
        if (focus.isNotEmpty) map['params']['default_focus_tags'] = focus;
      }
      // Emit placement; mesocycle_index must be 0-based in JSON
      final uiIdx = int.tryParse(_mesocycleIndex) ?? 1; // 1-based in UI
      final zeroIdx = (uiIdx - 1).clamp(0, 1000000);
      map['params']['placement'] = {
        'mode': _placement,
        if (_placement == 'Insert_After_Workout' && _anchorPlanOrderIndex != null) 'plan_order_index': _anchorPlanOrderIndex,
        if (_placement == 'Insert_After_Mesocycle') 'mesocycle_index': zeroIdx,
      };
      if (_placement != 'Append_To_End') {
        map['params']['on_conflict'] = _conflict;
      }
    } else {
      if (_mode.isNotEmpty) map['params']['mode'] = _mode;
      if (_value.isNotEmpty) {
        final numVal = double.tryParse(_value);
        map['params']['value'] = numVal ?? _value;
      }
      if (_target != null) map['target'] = _target;
    }
    widget.onChanged(map);
  }

  List<DropdownMenuItem<String>> _modeItemsFor(String type) {
    switch (type) {
      case 'Adjust_Load':
        return const [
          DropdownMenuItem(value: 'by_Percent', child: Text('По проценту')),
          DropdownMenuItem(value: 'to_Target', child: Text('К целевой (RPE)')),
        ];
      case 'Adjust_Reps':
        return const [
          DropdownMenuItem(value: 'by_Value', child: Text('На значение')),
          DropdownMenuItem(value: 'to_Target', child: Text('К целевой (RPE)')),
        ];
      case 'Adjust_Sets':
        return const [
          DropdownMenuItem(value: 'by_Value', child: Text('На значение (±N)')),
        ];
      case 'Inject_Mesocycle':
        return const [
          DropdownMenuItem(value: 'by_Template', child: Text('По ID шаблона')),
          DropdownMenuItem(value: 'by_Existing', child: Text('Из существующего (ID)')),
          DropdownMenuItem(value: 'Create_Inline', child: Text('Создать вручную')),
        ];
      default:
        return const [];
    }
  }

  String _valueHint() {
    if (_type == 'Adjust_Load' && _mode == 'by_Percent') return 'процент, напр. -5 или 2.5';
    if (_type == 'Adjust_Reps' && _mode == 'by_Value') return 'дельта повторений, напр. +1 или -1';
    if ((_type == 'Adjust_Load' || _type == 'Adjust_Reps') && _mode == 'to_Target') return 'целевой RPE, напр. 8';
    if (_type == 'Adjust_Sets' && _mode == 'by_Value') return '±N подходов, напр. 1 или -2';
    return 'значение';
  }

  String _modeHelp() {
    if (_type == 'Adjust_Load' && _mode == 'by_Percent') {
      return 'Изменяет вес и/или интенсивность на заданный %: положительное — увеличить, отрицательное — уменьшить. Пример: -2.5 снизит вес на 2.5%.';
    }
    if (_type == 'Adjust_Reps' && _mode == 'by_Value') {
      return 'Изменяет количество повторений на ±N: положительное — добавить повтор(ы), отрицательное — убрать.';
    }
    if (_type == 'Adjust_Load' && _mode == 'to_Target') {
      return 'Подгоняет интенсивность/вес к целевому RPE (1–10), сохраняя текущие повторы. Использует RPE-таблицу.';
    }
    if (_type == 'Adjust_Reps' && _mode == 'to_Target') {
      return 'Подбирает повторы под целевой RPE (1–10) при фиксированной интенсивности (если задана). Использует RPE-таблицу.';
    }
    if (_type == 'Adjust_Sets' && _mode == 'by_Value') {
      return 'Добавляет или удаляет подходы: положительное — добавить (клонируется последний сет), отрицательное — удалить с конца.';
    }
    if (_type == 'Inject_Mesocycle' && _mesoMode == 'by_Template') {
      return 'Внедряет мезоцикл из существующего шаблона по его ID. Можно указать размещение и стратегию разрешения конфликтов.';
    }
    if (_type == 'Inject_Mesocycle' && _mesoMode == 'by_Existing') {
      return 'Внедряет уже существующий мезоцикл по его ID из базы. Укажите идентификатор и размещение.';
    }
    if (_type == 'Inject_Mesocycle' && _mesoMode == 'Create_Inline') {
      return 'Создаёт мезоцикл вручную: продолжительность в неделях, длина микроцикла в днях, выходные дни и теги фокуса для тренировок. Можно задать размещение и стратегию конфликтов.';
    }
    return '';
  }

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        DropdownButtonFormField<String>(
          value: _type.isEmpty ? null : _type,
          items: const [
            DropdownMenuItem(value: 'Adjust_Load', child: Text('Корректировать вес')),
            DropdownMenuItem(value: 'Adjust_Reps', child: Text('Корректировать повторения')),
            DropdownMenuItem(value: 'Adjust_Sets', child: Text('Корректировать подходы')),
            DropdownMenuItem(value: 'Inject_Mesocycle', child: Text('Внедрить мезоцикл')),
          ],
          decoration: const InputDecoration(labelText: 'Тип действия', border: OutlineInputBorder()),
          onChanged: (v) {
            setState(() {
              _type = v ?? '';
              _mode = '';
              _value = '';
              _mesoMode = '';
            });
            _emit();
          },
          validator: (v) => (v == null || v.isEmpty) ? 'Required' : null,
        ),
        const SizedBox(height: 8),
        if (_type.isNotEmpty) ...[
          DropdownButtonFormField<String>(
            value: (_type == 'Inject_Mesocycle' ? (_mesoMode.isEmpty ? null : _mesoMode) : (_mode.isEmpty ? null : _mode)),
            items: _modeItemsFor(_type),
            decoration: const InputDecoration(labelText: 'Режим', border: OutlineInputBorder()),
            onChanged: (v) {
              setState(() {
                if (_type == 'Inject_Mesocycle') {
                  _mesoMode = v ?? '';
                } else {
                  _mode = v ?? '';
                  _value = '';
                }
              });
              _emit();
            },
            validator: (v) => (v == null || v.isEmpty) ? 'Required' : null,
          ),
          if (_mode.isNotEmpty || _mesoMode.isNotEmpty) ...[
            const SizedBox(height: 6),
            Text(_modeHelp(), style: Theme.of(context).textTheme.bodySmall),
          ],
          const SizedBox(height: 8),
          if (_type != 'Inject_Mesocycle' && _mode.isNotEmpty)
            TextFormField(
              initialValue: _value,
              decoration: InputDecoration(labelText: 'Значение', hintText: _valueHint(), border: const OutlineInputBorder()),
              keyboardType: TextInputType.number,
              onChanged: (v) {
                _value = v;
                _emit();
              },
              validator: (v) => (v == null || v.trim().isEmpty) ? 'Required' : null,
            ),
          if (_type == 'Inject_Mesocycle' && _mesoMode == 'by_Template') ...[
            Builder(builder: (context) {
              final asyncTpls = ref.watch(mesocycleTemplatesProvider);
              return asyncTpls.when(
                data: (items) {
                  if (items.isEmpty) {
                    return const Text('Нет шаблонов мезоциклов');
                  }
                  final selected = int.tryParse(_templateId);
                  return DropdownButtonFormField<int>(
                    value: selected,
                    items: items.map((e) => DropdownMenuItem(value: e.id, child: Text(e.name))).toList(),
                    decoration: const InputDecoration(labelText: 'Шаблон мезоцикла', border: OutlineInputBorder()),
                    onChanged: (v) {
                      setState(() => _templateId = (v?.toString() ?? ''));
                      _emit();
                    },
                    validator: (v) => (v == null) ? 'Required' : null,
                  );
                },
                loading: () => const Center(child: Padding(padding: EdgeInsets.all(8), child: CircularProgressIndicator(strokeWidth: 2))),
                error: (e, st) => Text('Ошибка загрузки шаблонов: $e'),
              );
            }),
          ] else if (_type == 'Inject_Mesocycle' && _mesoMode == 'by_Existing') ...[
            Builder(builder: (context) {
              final activePlan = ref.watch(activeAppliedPlanProvider);
              return activePlan.maybeWhen(
                data: (plan) {
                  final meso = plan?.calendarPlan.mesocycles ?? const [];
                  final items = <DropdownMenuItem<String>>[];
                  for (int i = 0; i < meso.length; i++) {
                    final m = meso[i];
                    final label = m.name.isNotEmpty ? m.name : 'Мезоцикл ${(i + 1)}';
                    items.add(DropdownMenuItem(value: m.id.toString(), child: Text('$label (ID ${m.id})')));
                  }
                  // add manual option always
                  items.add(const DropdownMenuItem(value: 'manual', child: Text('Другой (ввести ID)')));
                  final current = _sourceMesocycleId.isEmpty ? null : _sourceMesocycleId;
                  return Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      DropdownButtonFormField<String>(
                        value: current == null ? null : (items.any((e) => e.value == current) ? current : 'manual'),
                        items: items,
                        decoration: const InputDecoration(labelText: 'Выбрать мезоцикл', border: OutlineInputBorder()),
                        onChanged: (v) {
                          setState(() {
                            if (v == 'manual') {
                              // keep current manual value
                            } else {
                              _sourceMesocycleId = (v ?? '').trim();
                            }
                          });
                          _emit();
                        },
                        validator: (v) => (v == null || v.isEmpty) ? 'Required' : null,
                      ),
                      const SizedBox(height: 8),
                      if (_sourceMesocycleId.isEmpty || _sourceMesocycleId == 'manual')
                        TextFormField(
                          initialValue: _sourceMesocycleId == 'manual' ? '' : _sourceMesocycleId,
                          decoration: const InputDecoration(labelText: 'ID существующего мезоцикла', border: OutlineInputBorder()),
                          keyboardType: TextInputType.number,
                          onChanged: (v) {
                            setState(() => _sourceMesocycleId = v);
                            _emit();
                          },
                          validator: (v) => (v == null || v.trim().isEmpty || int.tryParse(v) == null) ? 'Введите число' : null,
                        ),
                    ],
                  );
                },
                orElse: () => TextFormField(
                  initialValue: _sourceMesocycleId,
                  decoration: const InputDecoration(labelText: 'ID существующего мезоцикла', border: OutlineInputBorder()),
                  keyboardType: TextInputType.number,
                  onChanged: (v) { setState(() => _sourceMesocycleId = v); _emit(); },
                  validator: (v) => (v == null || v.trim().isEmpty || int.tryParse(v) == null) ? 'Введите число' : null,
                ),
              );
            }),
          ] else if (_type == 'Inject_Mesocycle' && _mesoMode == 'Create_Inline') ...[
            Row(children: [
              Expanded(
                child: TextFormField(
                  initialValue: _weeks,
                  decoration: const InputDecoration(labelText: 'Длительность (недель)', border: OutlineInputBorder()),
                  keyboardType: TextInputType.number,
                  onChanged: (v) { setState(() => _weeks = v); _emit(); },
                  validator: (v) => (v == null || (int.tryParse(v) ?? 0) < 1) ? '>=1' : null,
                ),
              ),
              const SizedBox(width: 8),
              Expanded(
                child: TextFormField(
                  initialValue: _daysInMicro,
                  decoration: const InputDecoration(labelText: 'Дней в микроцикле', border: OutlineInputBorder()),
                  keyboardType: TextInputType.number,
                  onChanged: (v) { setState(() => _daysInMicro = v); _emit(); },
                  validator: (v) => (v == null || (int.tryParse(v) ?? 0) < 1) ? '>=1' : null,
                ),
              ),
            ]),
            const SizedBox(height: 8),
            Builder(builder: (context) {
              final n = int.tryParse(_daysInMicro);
              if (n == null || n < 1) return const SizedBox.shrink();
              return Wrap(
                spacing: 8,
                runSpacing: 8,
                children: List.generate(n, (i) {
                  final idx = i + 1;
                  final isRest = _restDays.contains(idx);
                  return FilterChip(
                    selected: isRest,
                    label: Text('День $idx: ${isRest ? 'выходной' : 'тренировка'}'),
                    onSelected: (sel) {
                      setState(() {
                        if (sel) _restDays.add(idx); else _restDays.remove(idx);
                      });
                      _emit();
                    },
                  );
                }),
              );
            }),
            const SizedBox(height: 8),
            Text('Теги фокуса', style: Theme.of(context).textTheme.labelLarge),
            const SizedBox(height: 6),
            Builder(builder: (context) {
              final tags = ref.watch(tagCatalogProvider);
              Widget group(String title, Set<String> values, Set<String> selected, void Function(Set<String>) onChanged) {
                return Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(title, style: Theme.of(context).textTheme.bodySmall),
                    Wrap(
                      spacing: 8,
                      children: values.map((v) {
                        final sel = selected.contains(v);
                        return FilterChip(
                          selected: sel,
                          label: Text(v),
                          onSelected: (s) {
                            final next = Set<String>.from(selected);
                            if (s) next.add(v); else next.remove(v);
                            onChanged(next);
                            _emit();
                          },
                        );
                      }).toList(),
                    ),
                  ],
                );
              }
              return Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  group('movement_type', tags.movementTypes, _mt, (s) => setState(() { _mt..clear()..addAll(s); })),
                  const SizedBox(height: 6),
                  group('region', tags.regions, _rg, (s) => setState(() { _rg..clear()..addAll(s); })),
                  const SizedBox(height: 6),
                  group('muscle_group', tags.muscleGroups, _mg, (s) => setState(() { _mg..clear()..addAll(s); })),
                  const SizedBox(height: 6),
                  group('equipment', tags.equipment, _eq, (s) => setState(() { _eq..clear()..addAll(s); })),
                ],
              );
            }),
          ],
          if (_type == 'Inject_Mesocycle' && (_mesoMode == 'by_Template' || _mesoMode == 'Create_Inline' || _mesoMode == 'by_Existing')) ...[
            const SizedBox(height: 12),
            Text('Размещение', style: Theme.of(context).textTheme.labelLarge),
            const SizedBox(height: 6),
            DropdownButtonFormField<String>(
              value: _placement,
              items: const [
                DropdownMenuItem(value: 'Append_To_End', child: Text('В конец плана')),
                DropdownMenuItem(value: 'Insert_After_Workout', child: Text('После тренировки')),
                DropdownMenuItem(value: 'Insert_After_Mesocycle', child: Text('После мезоцикла')),
              ],
              decoration: const InputDecoration(border: OutlineInputBorder()),
              onChanged: (v) {
                setState(() {
                  _placement = v ?? 'Append_To_End';
                  if (_placement != 'Insert_After_Workout') {
                    _anchorWorkoutId = null;
                    _anchorWorkoutName = null;
                    _anchorPlanOrderIndex = null;
                  }
                });
                _emit();
              },
              validator: (v) {
                final mode = v ?? _placement;
                if (mode == 'Insert_After_Workout' && _anchorPlanOrderIndex == null) {
                  return 'Нужно выбрать тренировку-якорь';
                }
                return null;
              },
            ),
            const SizedBox(height: 8),
            if (_placement == 'Insert_After_Workout') Row(
              children: [
                OutlinedButton.icon(
                  onPressed: () async {
                    final picked = await showWorkoutPickerBottomSheet(context, ref);
                    if (picked != null) {
                      setState(() {
                        _anchorWorkoutId = picked.id;
                        _anchorWorkoutName = picked.name;
                        _anchorPlanOrderIndex = picked.planOrderIndex;
                      });
                      _emit();
                    }
                  },
                  icon: const Icon(Icons.event),
                  label: const Text('Выбрать тренировку'),
                ),
                const SizedBox(width: 8),
                Expanded(child: Text(_anchorWorkoutId == null ? 'Не выбрано' : 'После: ${_anchorWorkoutName ?? '#'+_anchorWorkoutId.toString()}')),
              ],
            ),
            if (_placement == 'Insert_After_Mesocycle') Builder(
              builder: (context) {
                final activePlan = ref.watch(activeAppliedPlanProvider);
                return activePlan.maybeWhen(
                  data: (plan) {
                    final meso = plan?.calendarPlan.mesocycles ?? const [];
                    if (meso.isEmpty) {
                      return const Text('В плане нет мезоциклов');
                    }
                    final items = <DropdownMenuItem<String>>[];
                    for (int i = 0; i < meso.length; i++) {
                      final idx = (i + 1).toString();
                      final label = meso[i].name.isNotEmpty ? '$idx. ${meso[i].name}' : 'Мезоцикл $idx';
                      items.add(DropdownMenuItem(value: idx, child: Text(label)));
                    }
                    // normalize current selection into range
                    final currentIdx = int.tryParse(_mesocycleIndex) ?? 1;
                    final normalized = currentIdx.clamp(1, items.length).toString();
                    if (normalized != _mesocycleIndex) {
                      // keep state consistent without spamming emits
                      _mesocycleIndex = normalized;
                    }
                    return Row(
                      children: [
                        const Text('Мезоцикл: '),
                        const SizedBox(width: 8),
                        Expanded(
                          child: DropdownButtonFormField<String>(
                            value: _mesocycleIndex,
                            items: items,
                            decoration: const InputDecoration(border: OutlineInputBorder()),
                            onChanged: (v) {
                              setState(() { _mesocycleIndex = v ?? '1'; });
                              _emit();
                            },
                          ),
                        ),
                      ],
                    );
                  },
                  orElse: () => const SizedBox(height: 40, child: Center(child: CircularProgressIndicator(strokeWidth: 2))),
                );
              },
            ),
            const SizedBox(height: 12),
            if (_placement != 'Append_To_End') ...[
              Text('Конфликты', style: Theme.of(context).textTheme.labelLarge),
              const SizedBox(height: 6),
              DropdownButtonFormField<String>(
                value: _conflict,
                items: const [
                  DropdownMenuItem(value: 'Replace_Planned', child: Text('Заменять запланированное')),
                  DropdownMenuItem(value: 'Shift_Forward', child: Text('Сдвигать вперёд')),
                  DropdownMenuItem(value: 'Skip_On_Conflict', child: Text('Пропускать конфликтующие')),
                ],
                decoration: const InputDecoration(border: OutlineInputBorder()),
                onChanged: (v) { setState(() => _conflict = v ?? 'Shift_Forward'); _emit(); },
              ),
            ],
          ],
          const SizedBox(height: 16),
          if (_type != 'Inject_Mesocycle') ...[
            Text('Цель', style: Theme.of(context).textTheme.labelLarge),
            const SizedBox(height: 6),
            Text('Если цель не указана — действие применяется ко всем упражнениям выбранных воркаутов. Можно указать список exercise_ids или выбрать по тегам.', style: Theme.of(context).textTheme.bodySmall),
            const SizedBox(height: 8),
            TargetSelector(
              initial: _target,
              onChanged: (v) {
                setState(() => _target = v);
                _emit();
              },
            ),
          ]
        ]
      ],
    );
  }
}
