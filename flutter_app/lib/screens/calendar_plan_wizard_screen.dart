import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:workout_app/providers/plan_draft_provider.dart';
import 'package:workout_app/services/service_locator.dart';
import 'package:workout_app/models/mesocycle.dart';
import 'package:workout_app/models/microcycle.dart';
import 'package:workout_app/screens/calendar_plan_screen.dart';

class CalendarPlanWizardScreen extends ConsumerStatefulWidget {
  const CalendarPlanWizardScreen({super.key});

  @override
  ConsumerState<CalendarPlanWizardScreen> createState() => _CalendarPlanWizardScreenState();
}

class _NormDragData {
  final int fromWeekIndex;
  const _NormDragData(this.fromWeekIndex);
}

class _NormalizationSlot extends ConsumerStatefulWidget {
  final int weekIndex;
  const _NormalizationSlot({super.key, required this.weekIndex});

  @override
  ConsumerState<_NormalizationSlot> createState() => _NormalizationSlotState();
}

class _NormalizationSlotState extends ConsumerState<_NormalizationSlot> {
  bool _hover = false;

  @override
  Widget build(BuildContext context) {
    final draft = ref.watch(planDraftProvider);
    final notifier = ref.read(planDraftProvider.notifier);
    final theme = Theme.of(context);

    final week = (widget.weekIndex >= 0 && widget.weekIndex < draft.weeks.length) ? draft.weeks[widget.weekIndex] : null;
    final hasNorm = week?.normValue != null && (week?.normUnit != null);

    Widget chipOrButton;
    if (hasNorm) {
      final label = _formatNorm(week!.normValue!, week.normUnit!);
      chipOrButton = LongPressDraggable<_NormDragData>(
        data: _NormDragData(widget.weekIndex),
        feedback: Material(
          color: Colors.transparent,
          child: Chip(label: Text(label), backgroundColor: theme.colorScheme.secondaryContainer),
        ),
        childWhenDragging: Opacity(opacity: 0.4, child: _normChip(label, onClear: () => notifier.clearNormalizationAfterWeek(widget.weekIndex), onEdit: () => _openEditDialog(context, week.normValue!, week.normUnit!))),
        child: _normChip(label, onClear: () => notifier.clearNormalizationAfterWeek(widget.weekIndex), onEdit: () => _openEditDialog(context, week.normValue!, week.normUnit!)),
      );
    } else {
      chipOrButton = OutlinedButton.icon(
        icon: const Icon(Icons.add),
        label: const Text('Добавить нормировку'),
        onPressed: () => _openEditDialog(context, null, '%'),
      );
    }

    return DragTarget<_NormDragData>(
      onWillAccept: (data) {
        setState(() => _hover = true);
        return data != null && data.fromWeekIndex != widget.weekIndex;
      },
      onLeave: (_) => setState(() => _hover = false),
      onAccept: (data) {
        setState(() => _hover = false);
        notifier.moveNormalization(data.fromWeekIndex, widget.weekIndex);
      },
      builder: (context, candidateData, rejected) {
        return Container(
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(8),
            border: Border.all(color: _hover ? theme.colorScheme.primary : theme.dividerColor, style: BorderStyle.solid),
          ),
          padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 8),
          child: Row(
            children: [
              Expanded(child: Text('После недели ${widget.weekIndex + 1}', style: theme.textTheme.bodyMedium)),
              const SizedBox(width: 8),
              chipOrButton,
            ],
          ),
        );
      },
    );
  }

  Widget _normChip(String label, {required VoidCallback onClear, required VoidCallback onEdit}) {
    return InputChip(
      label: Text(label),
      onPressed: onEdit,
      onDeleted: onClear,
      deleteIcon: const Icon(Icons.close),
      deleteButtonTooltipMessage: 'Убрать',
    );
  }

  String _formatNorm(double value, String unit) {
    final v = value.toStringAsFixed(unit == '%' ? 0 : 1);
    return unit == '%' ? '$v%' : '$v кг';
  }

  Future<void> _openEditDialog(BuildContext context, double? initialValue, String initialUnit) async {
    final notifier = ref.read(planDraftProvider.notifier);
    final formKey = GlobalKey<FormState>();
    final valueCtrl = TextEditingController(text: initialValue?.toString() ?? '');
    String unit = initialUnit;
    await showDialog(
      context: context,
      builder: (_) {
        return AlertDialog(
          title: const Text('Нормировка после недели'),
          content: Form(
            key: formKey,
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                TextFormField(
                  controller: valueCtrl,
                  keyboardType: const TextInputType.numberWithOptions(decimal: true),
                  decoration: const InputDecoration(labelText: 'Значение'),
                  validator: (v) {
                    if (v == null || v.trim().isEmpty) return 'Введите значение';
                    final d = double.tryParse(v.replaceAll(',', '.'));
                    if (d == null) return 'Некорректное число';
                    return null;
                  },
                ),
                const SizedBox(height: 12),
                DropdownButtonFormField<String>(
                  value: (unit == 'kg' || unit == '%') ? unit : '%',
                  items: const [
                    DropdownMenuItem(value: '%', child: Text('%')),
                    DropdownMenuItem(value: 'kg', child: Text('кг')),
                  ],
                  onChanged: (v) => unit = v ?? '%',
                  decoration: const InputDecoration(labelText: 'Единица'),
                ),
              ],
            ),
          ),
          actions: [
            TextButton(onPressed: () => Navigator.of(context).pop(), child: const Text('Отмена')),
            ElevatedButton(
              onPressed: () {
                if (!formKey.currentState!.validate()) return;
                final val = double.parse(valueCtrl.text.replaceAll(',', '.'));
                notifier.setNormalizationAfterWeek(widget.weekIndex, val, unit);
                Navigator.of(context).pop();
              },
              child: const Text('Сохранить'),
            ),
          ],
        );
      },
    );
  }
}

class _Step3Schedule extends ConsumerWidget {
  const _Step3Schedule();

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final draft = ref.watch(planDraftProvider);
    final notifier = ref.read(planDraftProvider.notifier);
    final theme = Theme.of(context);

    if (draft.weeks.isEmpty) {
      return const Card(
        child: ListTile(
          title: Text('Нет микроциклов'),
          subtitle: Text('Добавьте микроциклы в мезоциклах на шаге 2'),
        ),
      );
    }

    return ListView.builder(
      shrinkWrap: true,
      physics: const NeverScrollableScrollPhysics(),
      itemCount: draft.weeks.length,
      itemBuilder: (context, wIndex) {
        final w = draft.weeks[wIndex];
        return Card(
          margin: const EdgeInsets.only(bottom: 8),
          child: ExpansionTile(
            initiallyExpanded: w.expanded,
            title: Text(w.name, style: theme.textTheme.titleMedium),
            children: [
              Padding(
                padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                child: Column(
                  children: [
                    for (int day = 1; day <= w.daysCount; day++)
                      ListTile(
                        contentPadding: EdgeInsets.zero,
                        title: Text('День $day', style: theme.textTheme.bodyMedium),
                        subtitle: TextFormField(
                          initialValue: w.days[day]?.note ?? '',
                          maxLines: 2,
                          decoration: const InputDecoration(
                            labelText: 'Заметка',
                            hintText: 'Например: ЛС жим/спина',
                            border: InputBorder.none,
                            isDense: true,
                            contentPadding: EdgeInsets.only(top: 4, bottom: 4),
                          ),
                          onChanged: (v) => notifier.setDayNote(wIndex, day, v.isEmpty ? null : v),
                        ),
                      ),
                  ],
                ),
              ),
            ],
          ),
        );
      },
    );
  }
}

class _Step4Review extends ConsumerWidget {
  const _Step4Review();

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final draft = ref.watch(planDraftProvider);
    final theme = Theme.of(context);
    final totalWeeks = draft.weeks.length;
    final allocated = draft.mesocycles.fold<int>(0, (acc, m) => acc + m.weeksCount);

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        ListTile(
          contentPadding: EdgeInsets.zero,
          title: const Text('Название'),
          subtitle: Text(draft.name.isEmpty ? 'Не указано' : draft.name),
        ),
        // Перемещено на уровень мезоциклов: длина микроцикла теперь задается для каждого мезоцикла
        ListTile(
          contentPadding: EdgeInsets.zero,
          title: const Text('Количество микроциклов'),
          subtitle: Text('$totalWeeks'),
        ),
        const SizedBox(height: 8),
        Text('Мезоциклы', style: theme.textTheme.titleMedium),
        const SizedBox(height: 8),
        if (draft.mesocycles.isEmpty)
          const Text('Нет мезоциклов')
        else
          ...List.generate(draft.mesocycles.length, (i) {
            final m = draft.mesocycles[i];
            return ListTile(
              contentPadding: EdgeInsets.zero,
              title: Text(m.name),
              subtitle: Text('Микроциклов: ${m.weeksCount} • Длина: ${m.microcycleLength} дн.${(m.notes?.isNotEmpty ?? false) ? ' • ${m.notes}' : ''}'),
            );
          }),
        const Divider(height: 24),
        Row(
          children: [
            Icon(
              allocated == totalWeeks ? Icons.check_circle : Icons.error_outline,
              color: allocated == totalWeeks ? Colors.green : Colors.orange,
            ),
            const SizedBox(width: 8),
            Text('Распределение недель: $allocated / $totalWeeks'),
          ],
        ),
        const SizedBox(height: 8),
        if (draft.name.isEmpty)
          const Row(children: [Icon(Icons.info_outline, color: Colors.orange), SizedBox(width: 8), Expanded(child: Text('Рекомендуется указать название плана'))]),
      ],
    );
  }
}

class _Step2Mesocycles extends ConsumerWidget {
  const _Step2Mesocycles();

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final draft = ref.watch(planDraftProvider);
    final notifier = ref.read(planDraftProvider.notifier);
    final theme = Theme.of(context);

    final totalWeeks = draft.weeks.length;
    final allocated = draft.mesocycles.fold<int>(0, (acc, m) => acc + m.weeksCount);

    return SingleChildScrollView(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text('Мезоциклы', style: theme.textTheme.titleMedium),
              TextButton.icon(
                onPressed: notifier.addMesocycle,
                icon: const Icon(Icons.add),
                label: const Text('Добавить мезоцикл'),
              ),
            ],
          ),
          const SizedBox(height: 8),
          if (totalWeeks > 0)
            Row(
              children: [
                Expanded(
                  child: LinearProgressIndicator(
                    value: totalWeeks == 0 ? 0 : (allocated / totalWeeks).clamp(0.0, 1.0),
                    minHeight: 8,
                  ),
                ),
                const SizedBox(width: 12),
                Text('$allocated / $totalWeeks'),
              ],
            ),
          const SizedBox(height: 8),
          if (draft.mesocycles.isEmpty)
            Card(
              child: ListTile(
                title: const Text('Нет мезоциклов'),
                subtitle: const Text('Добавьте хотя бы один мезоцикл'),
                trailing: IconButton(icon: const Icon(Icons.add), onPressed: notifier.addMesocycle),
              ),
            )
          else
            ReorderableListView.builder(
              shrinkWrap: true,
              physics: const NeverScrollableScrollPhysics(),
              itemCount: draft.mesocycles.length,
              onReorder: notifier.reorderMesocycles,
              itemBuilder: (context, index) {
                final m = draft.mesocycles[index];
                return Card(
                  key: ObjectKey(m),
                  margin: const EdgeInsets.only(bottom: 8),
                  child: Padding(
                    padding: const EdgeInsets.all(12.0),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Row(
                          children: [
                            Expanded(
                              child: TextFormField(
                                initialValue: m.name,
                                decoration: const InputDecoration(labelText: 'Название мезоцикла'),
                                onChanged: (v) => notifier.setMesocycleName(index, v),
                              ),
                            ),
                            const SizedBox(width: 8),
                            IconButton(
                              tooltip: 'Удалить',
                              onPressed: () => notifier.removeMesocycle(index),
                              icon: const Icon(Icons.delete_outline, color: Colors.redAccent),
                            ),
                          ],
                        ),
                        const SizedBox(height: 8),
                        // Notes for mesocycle
                        TextFormField(
                          initialValue: m.notes ?? '',
                          decoration: const InputDecoration(labelText: 'Заметки (до 100 символов)'),
                          maxLength: 100,
                          onChanged: (v) => notifier.setMesocycleNotes(index, v),
                        ),
                        const SizedBox(height: 8),
                        // Количество микроциклов per mesocycle with +/- controls
                        Row(
                          children: [
                            Expanded(child: Text('Количество микроциклов', style: theme.textTheme.bodyMedium)),
                            IconButton(
                              tooltip: 'Уменьшить',
                              onPressed: m.weeksCount > 0 ? () => notifier.removeWeekFromMesocycleEnd(index) : null,
                              icon: const Icon(Icons.remove_circle_outline),
                            ),
                            Text('${m.weeksCount}', style: theme.textTheme.titleMedium),
                            IconButton(
                              tooltip: 'Добавить',
                              onPressed: () => notifier.addWeekToMesocycle(index),
                              icon: const Icon(Icons.add_circle_outline),
                            ),
                          ],
                        ),
                        const SizedBox(height: 8),
                        // Длина микроциклов per mesocycle with +/- controls
                        Row(
                          children: [
                            Expanded(child: Text('Длина микроциклов (дней)', style: theme.textTheme.bodyMedium)),
                            IconButton(
                              tooltip: 'Сделать короче',
                              onPressed: m.microcycleLength > 1 ? () => notifier.setMesocycleMicrocycleLength(index, m.microcycleLength - 1) : null,
                              icon: const Icon(Icons.remove_circle_outline),
                            ),
                            Text('${m.microcycleLength}', style: theme.textTheme.titleMedium),
                            IconButton(
                              tooltip: 'Сделать длиннее',
                              onPressed: () => notifier.setMesocycleMicrocycleLength(index, m.microcycleLength + 1),
                              icon: const Icon(Icons.add_circle_outline),
                            ),
                          ],
                        ),
                        const SizedBox(height: 8),
                        // Preview days for this mesocycle
                        Text('Тренировки', style: theme.textTheme.bodySmall),
                        const SizedBox(height: 4),
                        Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            for (int d = 1; d <= m.microcycleLength; d++)
                              Padding(
                                padding: const EdgeInsets.only(bottom: 4.0),
                                child: Text('Тренировка $d', style: theme.textTheme.bodyMedium),
                              ),
                          ],
                        ),
                        const SizedBox(height: 8),
                        // Normalization chips per week (after each microcycle of this mesocycle)
                        Text('Нормировки (перетаскивайте между неделями)', style: theme.textTheme.bodySmall),
                        const SizedBox(height: 4),
                        Builder(builder: (context) {
                          // compute week index range that belongs to this mesocycle
                          int start = 0;
                          for (int i = 0; i < index; i++) start += draft.mesocycles[i].weeksCount;
                          final endExclusive = start + m.weeksCount;
                          return Column(
                            children: [
                              for (int local = 0; local < m.weeksCount; local++)
                                Padding(
                                  padding: const EdgeInsets.only(bottom: 6.0),
                                  child: _NormalizationSlot(
                                    weekIndex: start + local,
                                  ),
                                ),
                            ],
                          );
                        }),
                        const SizedBox(height: 4),
                        Align(
                          alignment: Alignment.centerRight,
                          child: ReorderableDragStartListener(index: index, child: const Icon(Icons.drag_indicator)),
                        ),
                      ],
                    ),
                  ),
                );
              },
            ),
        ],
      ),
    );
  }
}

class _CalendarPlanWizardScreenState extends ConsumerState<CalendarPlanWizardScreen> {
  int _currentStep = 0;
  late final TextEditingController _nameCtrl;
  bool _submitting = false;

  @override
  void initState() {
    super.initState();
    final draft = ref.read(planDraftProvider);
    _nameCtrl = TextEditingController(text: draft.name);
  }

  @override
  void dispose() {
    _nameCtrl.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final draft = ref.watch(planDraftProvider);
    final notifier = ref.read(planDraftProvider.notifier);

    return Scaffold(
      appBar: AppBar(
        leading: const BackButton(color: Colors.black),
        backgroundColor: Colors.transparent,
        elevation: 0,
        scrolledUnderElevation: 0,
        surfaceTintColor: Colors.transparent,
        iconTheme: const IconThemeData(color: Colors.black),
        foregroundColor: Colors.black,
      ),
      body: SafeArea(
        child: Column(
          children: [
            Expanded(
              child: Stepper(
                currentStep: _currentStep,
                onStepTapped: _submitting ? null : (i) => setState(() => _currentStep = i),
                onStepContinue: _submitting ? null : _onContinue,
                onStepCancel: _submitting ? null : _onBack,
                controlsBuilder: (context, details) {
                  return Row(
                    children: [
                      ElevatedButton(
                        onPressed: _submitting ? null : details.onStepContinue,
                        child: Text(_currentStep == 3 ? 'Готово' : 'Далее'),
                      ),
                      const SizedBox(width: 12),
                      if (_currentStep > 0)
                        TextButton(onPressed: _submitting ? null : details.onStepCancel, child: const Text('Назад')),
                      const SizedBox(width: 12),
                      if (_submitting) const SizedBox(width: 18, height: 18, child: CircularProgressIndicator(strokeWidth: 2)),
                    ],
                  );
                },
                steps: [
                  Step(
                    title: const Text('Основное'),
                    isActive: _currentStep >= 0,
                    state: _currentStep > 0 ? StepState.complete : StepState.indexed,
                    content: _Step1BasicMicro(
                      nameCtrl: _nameCtrl,
                      microcycleLength: draft.microcycleLength,
                      onNameChanged: notifier.setName,
                      onDecLength: draft.microcycleLength > 1 ? () => notifier.setMicrocycleLength(draft.microcycleLength - 1) : null,
                      onIncLength: () => notifier.setMicrocycleLength(draft.microcycleLength + 1),
                    ),
                  ),
                  Step(
                    title: const Text('Распределение по мезоциклам'),
                    isActive: _currentStep >= 1,
                    state: _currentStep > 1 ? StepState.complete : StepState.indexed,
                    content: const _Step2Mesocycles(),
                  ),
                  Step(
                    title: const Text('Редактор расписания'),
                    isActive: _currentStep >= 2,
                    state: _currentStep > 2 ? StepState.complete : StepState.indexed,
                    content: const _Step3Schedule(),
                  ),
                  Step(
                    title: const Text('Обзор и отправка'),
                    isActive: _currentStep >= 3,
                    state: StepState.indexed,
                    content: const _Step4Review(),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  void _onContinue() {
    final draft = ref.read(planDraftProvider);
    // Step 0 no longer requires microcycles; they are managed inside the mesocycles step
    if (_currentStep == 1) {
      final totalWeeks = draft.weeks.length;
      final allocated = draft.mesocycles.fold<int>(0, (acc, m) => acc + m.weeksCount);
      if (draft.mesocycles.isEmpty) {
        ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Добавьте хотя бы один мезоцикл')));
        return;
      }
      if (totalWeeks == 0) {
        ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Добавьте хотя бы один микроцикл')));
        return;
      }
      if (allocated != totalWeeks) {
        ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Сумма недель по мезоциклам должна равняться числу микроциклов')));
        return;
      }
    }

    if (_currentStep < 3) {
      setState(() => _currentStep += 1);
      return;
    }
    _submitDraft();
  }

  void _onBack() {
    if (_currentStep > 0) setState(() => _currentStep -= 1);
  }

    Future<void> _submitDraft() async {
    final draft = ref.read(planDraftProvider);
    final name = draft.name.trim();
    final weeks = draft.weeks.length;
    final totalAllocated = draft.mesocycles.fold<int>(0, (a, m) => a + m.weeksCount);

    print('Draft validation - Name: "$name", Weeks: $weeks, Mesocycles: ${draft.mesocycles.length}, Allocated: $totalAllocated');

    String? errorMessage;
    if (name.isEmpty) {
      errorMessage = 'Введите название плана';
      setState(() => _currentStep = 0);
    } else if (weeks <= 0) {
      errorMessage = 'Добавьте хотя бы один микроцикл в мезоциклах';
      setState(() => _currentStep = 1);
    } else if (draft.mesocycles.isEmpty) {
      errorMessage = 'Добавьте хотя бы один мезоцикл';
      setState(() => _currentStep = 1);
    } else if (totalAllocated != weeks) {
      errorMessage = 'Сумма недель по мезоциклам ($totalAllocated) должна равняться количеству микроциклов ($weeks)';
      setState(() => _currentStep = 1);
    }

    if (errorMessage != null) {
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(errorMessage)));
      return; // Stop execution if validation fails
    }

    // --- Submission logic ---
    final payload = {
      'name': name,
      'duration_weeks': weeks,
      'schedule': <String, dynamic>{}, // detailed exercise schedule can be added later
    };
    
    print('Payload being sent: $payload');

    setState(() => _submitting = true);
    try {
      final planService = ref.read(calendarPlanServiceProvider);
      final created = await planService.createCalendarPlan(payload);

      // Create mesocycles and microcycles based on allocation
      try {
        final mesoSvc = ref.read(mesocycleServiceProvider);
        int weekPointer = 0;
        for (int mi = 0; mi < draft.mesocycles.length; mi++) {
          final meso = draft.mesocycles[mi];
          final createdMeso = await mesoSvc.createMesocycle(
            created.id,
            MesocycleUpdateDto(
              name: meso.name,
              notes: meso.notes,
              orderIndex: mi,
              weeksCount: meso.weeksCount,
              microcycleLengthDays: meso.microcycleLength,
            ),
          );

// Create microcycles for this mesocycle
          for (int i = 0; i < meso.weeksCount; i++) {
            final weekDraft = draft.weeks[weekPointer + i];

            // Aggregate per-day notes into a single string for the microcycle
            final dayNotes = <String>[];
            for (var d = 1; d <= weekDraft.daysCount; d++) {
              final n = weekDraft.days[d]?.note?.trim();
              if (n != null && n.isNotEmpty) {
                dayNotes.add('День $d: $n');
              }
            }
            String? microNotes = dayNotes.isEmpty ? null : dayNotes.join('\n');
            if (microNotes != null && microNotes.length > 100) {
              microNotes = microNotes.substring(0, 100); // Truncate to avoid DB error
            }

            await mesoSvc.createMicrocycle(
              createdMeso.id,
              MicrocycleUpdateDto(
                orderIndex: i,
                daysCount: weekDraft.daysCount,
                notes: microNotes, // Correctly pass the aggregated string
                normalizationValue: weekDraft.normValue,
                normalizationUnit: weekDraft.normUnit,
              ),
            );
          }
          weekPointer += meso.weeksCount;
        }
      } catch (e) {
        // Handle meso/micro creation error
        if (!mounted) return;
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('Ошибка создания мезоциклов: $e')));
      }

      if (!mounted) return;
      Navigator.of(context).pushReplacement(
        MaterialPageRoute(builder: (_) => CalendarPlanScreen(planId: created.id)),
      );
    } catch (e) {
      if (!mounted) return;
      setState(() => _submitting = false);
      print('Calendar plan creation error: $e');
      if (e.toString().contains('422')) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('Ошибка валидации данных: $e')));
      } else {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('Ошибка создания плана: $e')));
      }
    }
  }
}

class _Step1BasicMicro extends ConsumerWidget {
  const _Step1BasicMicro({
    required this.nameCtrl,
    required this.microcycleLength,
    required this.onNameChanged,
    required this.onDecLength,
    required this.onIncLength,
  });

  final TextEditingController nameCtrl;
  final int microcycleLength;
  final void Function(String) onNameChanged;
  final VoidCallback? onDecLength;
  final VoidCallback onIncLength;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final draft = ref.watch(planDraftProvider);
    final notifier = ref.read(planDraftProvider.notifier);
    final theme = Theme.of(context);

    return SingleChildScrollView(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          TextField(
            controller: nameCtrl,
            decoration: const InputDecoration(labelText: 'Название плана'),
            onChanged: onNameChanged,
          ),
        ],
      ),
    );
  }
}
