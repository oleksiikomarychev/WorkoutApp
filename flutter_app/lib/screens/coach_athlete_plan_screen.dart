import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/intl.dart';
import 'package:table_calendar/table_calendar.dart';
import 'package:workout_app/config/constants/theme_constants.dart';
import 'package:workout_app/models/applied_calendar_plan.dart';
import 'package:workout_app/models/workout.dart';
import 'package:workout_app/models/exercise_instance.dart';
import 'package:workout_app/providers/coach_plan_providers.dart';
import 'package:workout_app/services/service_locator.dart';
import 'package:workout_app/services/crm_coach_mass_edit_service.dart';

class CoachAthletePlanScreen extends ConsumerStatefulWidget {
  final String athleteId;
  final String? athleteName;

  const CoachAthletePlanScreen({super.key, required this.athleteId, this.athleteName});

  @override
  ConsumerState<CoachAthletePlanScreen> createState() => _CoachAthletePlanScreenState();
}

class _CoachAthletePlanScreenState extends ConsumerState<CoachAthletePlanScreen> {
  DateTime _focusedDay = DateTime.now();
  DateTime _selectedDay = _dateOnly(DateTime.now());

  @override
  Widget build(BuildContext context) {
    final planAsync = ref.watch(coachActivePlanProvider(widget.athleteId));
    final workoutsAsync = ref.watch(coachActivePlanWorkoutsProvider(widget.athleteId));
    final eventsByDay = ref.watch(coachWorkoutsByDayProvider(widget.athleteId));

    return Scaffold(
      appBar: AppBar(
        title: Text(widget.athleteName ?? 'Athlete ${widget.athleteId}'),
        actions: [
          PopupMenuButton<String>(
            tooltip: 'Массовые правки плана атлета',
            onSelected: (value) async {
              if (value == 'mass_edit') {
                await _openCoachMassEditDialog();
              } else if (value == 'ai_mass_edit') {
                await _openCoachAiMassEditDialog(context);
              }
            },
            itemBuilder: (ctx) => [
              const PopupMenuItem(
                value: 'mass_edit',
                child: Text('Mass edit (notes/day)'),
              ),
              const PopupMenuItem(
                value: 'ai_mass_edit',
                child: Text('AI mass edit плана'),
              ),
            ],
          ),
        ],
      ),
      body: planAsync.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (err, _) => Center(child: Text('Failed to load plan: $err')),
        data: (plan) {
          if (plan == null) {
            return const Center(child: Text('У атлета нет активного плана'));
          }
          return RefreshIndicator(
            onRefresh: () async {
              ref.invalidate(coachActivePlanProvider(widget.athleteId));
              ref.invalidate(coachActivePlanWorkoutsProvider(widget.athleteId));
              await Future.delayed(const Duration(milliseconds: 200));
            },
            child: ListView(
              padding: const EdgeInsets.only(bottom: 24),
              children: [
                _buildPlanSummary(plan),
                const SizedBox(height: 12),
                _buildCalendar(eventsByDay),
                const SizedBox(height: 12),
                _buildWorkoutsSection(workoutsAsync, eventsByDay),
              ],
            ),
          );
        },
      ),
    );
  }

  Widget _buildPlanSummary(AppliedCalendarPlan plan) {
    final adherence = plan.adherencePct;
    final completed = plan.actualSessionsCompleted ?? 0;
    final planned = plan.plannedSessionsTotal ?? 0;
    final status = (plan.status ?? 'active').toLowerCase();

    Color statusColor;
    switch (status) {
      case 'completed':
        statusColor = Colors.green;
        break;
      case 'dropped':
      case 'cancelled':
        statusColor = Colors.redAccent;
        break;
      default:
        statusColor = AppColors.primary;
    }

    String statusLabel = status.isNotEmpty ? status[0].toUpperCase() + status.substring(1) : 'Active';

    return Card(
      margin: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Container(
                  width: 10,
                  height: 10,
                  decoration: BoxDecoration(color: statusColor, shape: BoxShape.circle),
                ),
                const SizedBox(width: 8),
                Text(statusLabel, style: AppTextStyles.titleSmall),
                const Spacer(),
                if (planned > 0)
                  Text('$completed / $planned sessions', style: AppTextStyles.bodySmall),
              ],
            ),
            const SizedBox(height: 8),
            Text(plan.calendarPlan.name, style: AppTextStyles.titleMedium),
            const SizedBox(height: 4),
            Text('Period: ${_formatDate(plan.startDate)} – ${_formatDate(plan.endDate)}', style: AppTextStyles.bodySmall),
            if (planned > 0) ...[
              const SizedBox(height: 12),
              ClipRRect(
                borderRadius: BorderRadius.circular(999),
                child: LinearProgressIndicator(
                  minHeight: 6,
                  backgroundColor: Colors.grey.shade200,
                  valueColor: AlwaysStoppedAnimation<Color>(statusColor),
                  value: (completed / planned).clamp(0, 1).toDouble(),
                ),
              ),
            ],
            if (adherence != null) ...[
              const SizedBox(height: 6),
              Text('Adherence: ${adherence.toStringAsFixed(1)}%', style: AppTextStyles.bodySmall),
            ],
            if (plan.notes?.isNotEmpty == true) ...[
              const SizedBox(height: 6),
              Text('Notes: ${plan.notes}', style: AppTextStyles.bodySmall),
            ],
          ],
        ),
      ),
    );
  }

  Widget _buildCalendar(Map<DateTime, List<Workout>> eventsByDay) {
    return Container(
      color: Colors.white,
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 8),
      child: TableCalendar<Workout>(
        firstDay: DateTime.utc(2020, 1, 1),
        lastDay: DateTime.utc(2100, 12, 31),
        focusedDay: _focusedDay,
        startingDayOfWeek: StartingDayOfWeek.monday,
        calendarFormat: CalendarFormat.month,
        selectedDayPredicate: (day) => isSameDay(_selectedDay, day),
        eventLoader: (day) => eventsByDay[_dateOnly(day)] ?? const <Workout>[],
        onDaySelected: (selectedDay, focusedDay) {
          setState(() {
            _selectedDay = _dateOnly(selectedDay);
            _focusedDay = focusedDay;
          });
        },
        calendarBuilders: CalendarBuilders(
          markerBuilder: (context, date, events) {
            if (events.isEmpty) return const SizedBox.shrink();
            final list = events.cast<Workout>();
            final counts = _statusCounts(list);
            return Padding(
              padding: const EdgeInsets.only(top: 30),
              child: Row(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  if (counts.completed > 0) _dot(Colors.green),
                  if (counts.inProgress > 0) _dot(AppColors.primary),
                  if (counts.planned > 0) _dot(Colors.redAccent),
                ],
              ),
            );
          },
        ),
      ),
    );
  }

  Widget _buildWorkoutsSection(AsyncValue<List<Workout>> workoutsAsync, Map<DateTime, List<Workout>> eventsByDay) {
    final selectedList = eventsByDay[_selectedDay] ?? const <Workout>[];
    final title = DateFormat('EEEE, MMM d, yyyy').format(_selectedDay);

    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Text(title, style: AppTextStyles.titleMedium),
              const Spacer(),
              IconButton(
                icon: const Icon(Icons.refresh),
                onPressed: () {
                  ref.invalidate(coachActivePlanWorkoutsProvider(widget.athleteId));
                },
              ),
            ],
          ),
          const SizedBox(height: 8),
          workoutsAsync.when(
            loading: () => const Center(child: Padding(padding: EdgeInsets.all(16), child: CircularProgressIndicator())),
            error: (err, _) => Padding(
              padding: const EdgeInsets.all(16),
              child: Text('Не удалось загрузить тренировки: $err'),
            ),
            data: (_) {
              if (selectedList.isEmpty) {
                return const Padding(
                  padding: EdgeInsets.all(16),
                  child: Text('Нет тренировок в выбранный день'),
                );
              }
              return Column(
                children: selectedList
                    .map(
                      (w) => Padding(
                        padding: const EdgeInsets.only(bottom: 12),
                        child: _buildWorkoutTile(w),
                      ),
                    )
                    .toList(),
              );
            },
          ),
        ],
      ),
    );
  }

  Widget _buildWorkoutTile(Workout workout) {
    final statusView = _statusView(workout);
    return Card(
      child: ListTile(
        title: Text(workout.name, style: AppTextStyles.titleSmall),
        subtitle: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(_timeOrDate(workout)),
            if (workout.notes?.isNotEmpty == true)
              Padding(
                padding: const EdgeInsets.only(top: 4),
                child: Text(workout.notes!, maxLines: 2, overflow: TextOverflow.ellipsis),
              ),
          ],
        ),
        trailing: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.end,
          children: [
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
              decoration: BoxDecoration(color: statusView.background, borderRadius: BorderRadius.circular(14)),
              child: Text(statusView.label, style: TextStyle(color: statusView.textColor, fontWeight: FontWeight.w600)),
            ),
            Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                IconButton(
                  icon: const Icon(Icons.event),
                  tooltip: 'Перепланировать',
                  onPressed: workout.id == null ? null : () => _rescheduleWorkout(workout),
                ),
                IconButton(
                  icon: const Icon(Icons.edit_note),
                  tooltip: 'Редактировать заметку',
                  onPressed: workout.id == null ? null : () => _editWorkoutNotes(workout),
                ),
              ],
            ),
          ],
        ),
        onTap: () => _openWorkoutDetails(workout),
      ),
    );
  }

  Future<void> _editWorkoutNotes(Workout workout) async {
    if (workout.id == null) return;
    final controller = TextEditingController(text: workout.notes ?? '');
    String? newNotes = await showDialog<String>(
      context: context,
      builder: (ctx) {
        return AlertDialog(
          title: Text('Заметка к ${workout.name}'),
          content: TextField(
            controller: controller,
            maxLines: 4,
            decoration: const InputDecoration(hintText: 'Введите заметку для атлета'),
          ),
          actions: [
            TextButton(onPressed: () => Navigator.of(ctx).pop(), child: const Text('Отмена')),
            FilledButton(onPressed: () => Navigator.of(ctx).pop(controller.text.trim()), child: const Text('Сохранить')),
          ],
        );
      },
    );
    if (newNotes == null) return;
    try {
      final svc = ref.read(crmCoachServiceProvider);
      await svc.updateAthleteWorkout(
        athleteId: widget.athleteId,
        workoutId: workout.id!,
        payload: {'notes': newNotes.isEmpty ? null : newNotes},
      );
      if (context.mounted) {
        ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Заметка обновлена')));
      }
      ref.invalidate(coachActivePlanWorkoutsProvider(widget.athleteId));
    } catch (e) {
      if (context.mounted) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('Ошибка: $e')));
      }
    }
  }

  Future<void> _rescheduleWorkout(Workout workout) async {
    if (workout.id == null) return;
    final DateTime initial = workout.scheduledFor ?? DateTime.now();
    final pickedDate = await showDatePicker(
      context: context,
      initialDate: initial,
      firstDate: DateTime.now().subtract(const Duration(days: 1)),
      lastDate: DateTime.now().add(const Duration(days: 365)),
    );
    if (pickedDate == null) return;
    final pickedTime = await showTimePicker(
      context: context,
      initialTime: TimeOfDay.fromDateTime(initial),
    );
    if (pickedTime == null) return;
    final scheduled = DateTime(
      pickedDate.year,
      pickedDate.month,
      pickedDate.day,
      pickedTime.hour,
      pickedTime.minute,
    );
    try {
      final svc = ref.read(crmCoachServiceProvider);
      await svc.updateAthleteWorkout(
        athleteId: widget.athleteId,
        workoutId: workout.id!,
        payload: {'scheduled_for': scheduled.toIso8601String()},
      );
      if (context.mounted) {
        ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Тренировка перепланирована')));
      }
      ref.invalidate(coachActivePlanWorkoutsProvider(widget.athleteId));
    } catch (e) {
      if (context.mounted) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('Ошибка: $e')));
      }
    }
  }

  void _openWorkoutDetails(Workout workout) {
    showModalBottomSheet(
      context: context,
      showDragHandle: true,
      isScrollControlled: true,
      builder: (ctx) {
        final exercises = workout.exerciseInstances;
        return SafeArea(
          child: Padding(
            padding: const EdgeInsets.fromLTRB(16, 12, 16, 24),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(workout.name, style: AppTextStyles.titleMedium),
                Text(_timeOrDate(workout), style: AppTextStyles.bodySmall),
                const SizedBox(height: 12),
                if (exercises.isEmpty)
                  const Text('Нет данных по упражнениям в этой тренировке')
                else
                  Flexible(
                    child: ListView.separated(
                      shrinkWrap: true,
                      itemCount: exercises.length,
                      separatorBuilder: (_, __) => const Divider(height: 1),
                      itemBuilder: (_, index) {
                        final ex = exercises[index];
                        return ListTile(
                          title: Text(ex.exerciseDefinition?.name ?? 'Exercise ${ex.exerciseListId}'),
                          subtitle: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              if (ex.notes?.isNotEmpty == true)
                                Text('Notes: ${ex.notes}', maxLines: 2, overflow: TextOverflow.ellipsis),
                              Text('Order: ${ex.order ?? '-'}'),
                              Text('Sets: ${ex.sets.length}'),
                            ],
                          ),
                          trailing: IconButton(
                            icon: const Icon(Icons.edit),
                            onPressed: ex.id == null ? null : () => _editExerciseInstance(ex),
                            tooltip: 'Редактировать упражнение',
                          ),
                        );
                      },
                    ),
                  ),
              ],
            ),
          ),
        );
      },
    );
  }

  Future<void> _editExerciseInstance(ExerciseInstance instance) async {
    if (instance.id == null) return;
    final notesCtrl = TextEditingController(text: instance.notes ?? '');
    final orderCtrl = TextEditingController(text: instance.order?.toString() ?? '');
    final result = await showDialog<Map<String, dynamic>>(
      context: context,
      builder: (ctx) {
        return AlertDialog(
          title: Text('Упражнение ${instance.exerciseDefinition?.name ?? instance.exerciseListId}'),
          content: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              TextField(
                controller: notesCtrl,
                decoration: const InputDecoration(labelText: 'Заметка для упражнения'),
                maxLines: 3,
              ),
              TextField(
                controller: orderCtrl,
                keyboardType: TextInputType.number,
                decoration: const InputDecoration(labelText: 'Порядок'),
              ),
            ],
          ),
          actions: [
            TextButton(onPressed: () => Navigator.of(ctx).pop(), child: const Text('Отмена')),
            FilledButton(
              onPressed: () {
                final payload = <String, dynamic>{};
                final trimmedNotes = notesCtrl.text.trim();
                if (trimmedNotes.isNotEmpty) {
                  payload['notes'] = trimmedNotes;
                } else {
                  payload['notes'] = null;
                }
                final parsedOrder = int.tryParse(orderCtrl.text.trim());
                if (parsedOrder != null) {
                  payload['order'] = parsedOrder;
                }
                Navigator.of(ctx).pop(payload);
              },
              child: const Text('Сохранить'),
            ),
          ],
        );
      },
    );
    if (result == null || result.isEmpty) return;
    try {
      final svc = ref.read(crmCoachServiceProvider);
      await svc.updateExerciseInstance(
        athleteId: widget.athleteId,
        instanceId: instance.id!,
        payload: result,
      );
      if (context.mounted) {
        ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Упражнение обновлено')));
      }
      ref.invalidate(coachActivePlanWorkoutsProvider(widget.athleteId));
    } catch (e) {
      if (context.mounted) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('Ошибка: $e')));
      }
    }
  }

  Future<void> _openCoachMassEditDialog() async {
    final allWorkouts = await ref.read(coachActivePlanWorkoutsProvider(widget.athleteId).future);
    if (allWorkouts.isEmpty) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Нет тренировок для массовых правок')),
        );
      }
      return;
    }

    final dayWorkouts = allWorkouts.where((w) {
      final dt = w.scheduledFor;
      if (dt == null) return false;
      return _dateOnly(dt) == _selectedDay;
    }).toList();

    if (dayWorkouts.isEmpty) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('В выбранный день нет тренировок')),
        );
      }
      return;
    }

    final workoutNotesCtrl = TextEditingController();
    final exerciseNotesCtrl = TextEditingController();
    bool applyToWorkouts = true;
    bool applyToExercises = false;

    final confirmed = await showDialog<bool>(
      context: context,
      builder: (ctx) {
        return StatefulBuilder(
          builder: (ctx, setState) {
            return AlertDialog(
              title: Text('Mass edit (${DateFormat('dd MMM yyyy').format(_selectedDay)})'),
              content: SingleChildScrollView(
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    CheckboxListTile(
                      value: applyToWorkouts,
                      onChanged: (v) => setState(() => applyToWorkouts = v ?? false),
                      title: const Text('Обновить заметки тренировок (workouts)'),
                      controlAffinity: ListTileControlAffinity.leading,
                    ),
                    TextField(
                      controller: workoutNotesCtrl,
                      maxLines: 2,
                      decoration: const InputDecoration(
                        border: OutlineInputBorder(),
                        hintText: 'Новая заметка для всех тренировок этого дня',
                      ),
                    ),
                    const SizedBox(height: 12),
                    CheckboxListTile(
                      value: applyToExercises,
                      onChanged: (v) => setState(() => applyToExercises = v ?? false),
                      title: const Text('Обновить заметки упражнений (exercise instances)'),
                      controlAffinity: ListTileControlAffinity.leading,
                    ),
                    TextField(
                      controller: exerciseNotesCtrl,
                      maxLines: 2,
                      decoration: const InputDecoration(
                        border: OutlineInputBorder(),
                        hintText: 'Новая заметка для всех упражнений этого дня',
                      ),
                    ),
                  ],
                ),
              ),
              actions: [
                TextButton(
                  onPressed: () => Navigator.of(ctx).pop(false),
                  child: const Text('Отмена'),
                ),
                FilledButton(
                  onPressed: () => Navigator.of(ctx).pop(true),
                  child: const Text('Применить'),
                ),
              ],
            );
          },
        );
      },
    );

    if (confirmed != true) return;

    final workoutNotes = workoutNotesCtrl.text.trim();
    final exerciseNotes = exerciseNotesCtrl.text.trim();

    final workoutsPayload = <Map<String, dynamic>>[];
    if (applyToWorkouts && workoutNotes.isNotEmpty) {
      for (final w in dayWorkouts) {
        if (w.id == null) continue;
        workoutsPayload.add({
          'workout_id': w.id!,
          'update': {'notes': workoutNotes},
        });
      }
    }

    final exercisePayload = <Map<String, dynamic>>[];
    if (applyToExercises && exerciseNotes.isNotEmpty) {
      for (final w in dayWorkouts) {
        for (final ex in w.exerciseInstances) {
          if (ex.id == null) continue;
          exercisePayload.add({
            'instance_id': ex.id!,
            'update': {'notes': exerciseNotes},
          });
        }
      }
    }

    if (workoutsPayload.isEmpty && exercisePayload.isEmpty) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Нет изменений для применения')),
        );
      }
      return;
    }

    try {
      final svc = ref.read(crmCoachMassEditServiceProvider);
      await svc.massEditWorkouts(
        athleteId: widget.athleteId,
        workouts: workoutsPayload.isEmpty ? null : workoutsPayload,
        exerciseInstances: exercisePayload.isEmpty ? null : exercisePayload,
      );
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Mass edit применён для выбранного дня')),
        );
      }
      ref.invalidate(coachActivePlanWorkoutsProvider(widget.athleteId));
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Ошибка mass edit: $e')),
        );
      }
    }
  }

  Future<void> _openCoachAiMassEditDialog(BuildContext context) async {
    final plan = await ref.read(coachActivePlanProvider(widget.athleteId).future);
    if (plan == null) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('У атлета нет активного плана')),
        );
      }
      return;
    }

    final promptController = TextEditingController();
    bool isLoading = false;
    String? summary;

    final confirmed = await showDialog<bool>(
      context: context,
      barrierDismissible: false,
      builder: (ctx) {
        return StatefulBuilder(
          builder: (ctx, setState) {
            return AlertDialog(
              title: const Text('AI mass edit плана атлета'),
              content: Column(
                mainAxisSize: MainAxisSize.min,
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text('Опишите, что нужно изменить в плане этого атлета.'),
                  const SizedBox(height: 8),
                  TextField(
                    controller: promptController,
                    maxLines: 4,
                    decoration: const InputDecoration(
                      border: OutlineInputBorder(),
                      hintText:
                          'Например: снизь объём ног на 20% и увеличь интенсивность жимов на 5%',
                    ),
                  ),
                  const SizedBox(height: 12),
                  if (isLoading) ...[
                    const Center(child: CircularProgressIndicator()),
                  ] else if (summary != null) ...[
                    const Text('Предлагаемые изменения:',
                        style: TextStyle(fontWeight: FontWeight.w600)),
                    const SizedBox(height: 4),
                    Text(summary!),
                  ],
                ],
              ),
              actions: [
                TextButton(
                  onPressed: () => Navigator.of(ctx).pop(false),
                  child: const Text('Отмена'),
                ),
                TextButton(
                  onPressed: isLoading
                      ? null
                      : () async {
                          final text = promptController.text.trim();
                          if (text.isEmpty) return;
                          setState(() {
                            isLoading = true;
                            summary = null;
                          });

                          try {
                            final svc = ref.read(crmCoachMassEditServiceProvider);
                            final resp = await svc.aiMassEditPlan(
                              athleteId: widget.athleteId,
                              prompt: text,
                              mode: 'preview',
                            );

                            final cmd = resp.massEditCommand;
                            final operation = cmd['operation'];
                            final filter = cmd['filter'] as Map<String, dynamic>?;
                            final actions = cmd['actions'] as Map<String, dynamic>?;

                            final parts = <String>[];
                            if (operation != null) {
                              parts.add('operation: $operation');
                            }
                            if (filter != null && filter.isNotEmpty) {
                              parts.add('filter: ${filter.keys.join(', ')}');
                            }
                            if (actions != null && actions.isNotEmpty) {
                              parts.add('actions: ${actions.keys.join(', ')}');
                            }

                            setState(() {
                              summary = parts.isEmpty
                                  ? 'Команда сформирована, но не удалось построить краткое описание.'
                                  : parts.join(' · ');
                              isLoading = false;
                            });
                          } catch (e) {
                            setState(() {
                              isLoading = false;
                              summary = 'Ошибка: $e';
                            });
                          }
                        },
                  child: const Text('Сгенерировать'),
                ),
                FilledButton(
                  onPressed: (isLoading || summary == null)
                      ? null
                      : () => Navigator.of(ctx).pop(true),
                  child: const Text('Применить'),
                ),
              ],
            );
          },
        );
      },
    );

    if (confirmed == true) {
      try {
        final svc = ref.read(crmCoachMassEditServiceProvider);
        await svc.aiMassEditPlan(
          athleteId: widget.athleteId,
          prompt: promptController.text.trim(),
          mode: 'apply',
        );

        ref.invalidate(coachActivePlanProvider(widget.athleteId));
        ref.invalidate(coachActivePlanWorkoutsProvider(widget.athleteId));

        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(content: Text('AI mass edit применён к плану атлета')),
          );
        }
      } catch (e) {
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(content: Text('Ошибка применения AI mass edit: $e')),
          );
        }
      }
    }
  }

  String _formatDate(DateTime? date) {
    if (date == null) return '—';
    return DateFormat('dd MMM yyyy').format(date);
  }

  String _timeOrDate(Workout w) {
    final dt = w.scheduledFor;
    if (dt == null) return 'Без даты';
    return DateFormat('MMM d, HH:mm').format(dt.toLocal());
  }

  _StatusView _statusView(Workout w) {
    final completed =
        (w.status?.toLowerCase() == 'completed') || (w.completedAt != null);
    final inProgress = (w.startedAt != null) && (w.completedAt == null);
    if (completed) {
      return const _StatusView(
          'Завершена', Color(0xFFEFF8F2), Colors.green, Colors.green);
    } else if (inProgress) {
      return const _StatusView('В процессе', Color(0xFFEAEFFF),
          AppColors.primary, AppColors.primary);
    } else {
      return const _StatusView('Запланирована', Color(0xFFFFEBEE),
          Colors.redAccent, Colors.redAccent);
    }
  }

  ({int planned, int inProgress, int completed}) _statusCounts(
      List<Workout> list) {
    int p = 0, i = 0, c = 0;
    for (final w in list) {
      final completedB =
          (w.status?.toLowerCase() == 'completed') || (w.completedAt != null);
      final inProgressB =
          (w.startedAt != null) && (w.completedAt == null);
      if (completedB) {
        c++;
      } else if (inProgressB) {
        i++;
      } else {
        p++;
      }
    }
    return (planned: p, inProgress: i, completed: c);
  }

  Widget _dot(Color color) {
    return Container(
      margin: const EdgeInsets.symmetric(horizontal: 1.5),
      width: 6,
      height: 6,
      decoration: BoxDecoration(color: color, shape: BoxShape.circle),
    );
  }
}

DateTime _dateOnly(DateTime dt) => DateTime(dt.year, dt.month, dt.day);

class _StatusView {
  final String label;
  final Color background;
  final Color textColor;
  final Color dotColor;

  const _StatusView(this.label, this.background, this.textColor, this.dotColor);
}
