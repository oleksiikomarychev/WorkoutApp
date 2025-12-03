import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/intl.dart';
import 'package:table_calendar/table_calendar.dart';
import 'package:workout_app/config/constants/theme_constants.dart';
import 'package:workout_app/models/applied_calendar_plan.dart';
import 'package:workout_app/models/workout.dart';
import 'package:workout_app/models/exercise_instance.dart';
import 'package:workout_app/models/plan_analytics.dart';
import 'package:workout_app/models/exercise_definition.dart';
import 'package:workout_app/models/exercise_set_dto.dart';
import 'package:workout_app/providers/coach_plan_providers.dart';
import 'package:workout_app/services/service_locator.dart';
import 'package:workout_app/services/crm_coach_mass_edit_service.dart';
import 'package:workout_app/widgets/primary_app_bar.dart';
import 'package:workout_app/widgets/assistant_chat_host.dart';
import 'package:workout_app/widgets/plan_analytics_chart.dart';

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

  final List<String> _metrics = const ['sets_count', 'volume_sum', 'intensity_avg', 'effort_avg'];
  String _metricX = 'effort_avg';
  String _metricY = 'effort_avg';

  @override
  Widget build(BuildContext context) {
    final planAsync = ref.watch(coachActivePlanProvider(widget.athleteId));
    final workoutsAsync = ref.watch(coachActivePlanWorkoutsProvider(widget.athleteId));
    final eventsByDay = ref.watch(coachWorkoutsByDayProvider(widget.athleteId));
    final analyticsAsync = ref.watch(coachActivePlanAnalyticsProvider(widget.athleteId));

    return AssistantChatHost(
      initialMessage:
          'Открываю ассистента из CoachAthletePlanScreen. Используй контекст v1, чтобы понимать текущего атлета, его активный план и выбранный день.',
      contextBuilder: _buildChatContext,
      builder: (context, openChat) {
        return Scaffold(
          appBar: PrimaryAppBar(
            title: widget.athleteName ?? 'Athlete ${widget.athleteId}',
            onTitleTap: openChat,
            actions: [
              PopupMenuButton<String>(
                tooltip: 'Массовые правки плана атлета',
                onSelected: (value) async {
                  if (value == 'mass_edit') {
                    await _openCoachMassEditDialog();
                  }
                },
                itemBuilder: (ctx) => const [
                  PopupMenuItem(
                    value: 'mass_edit',
                    child: Text('Mass edit (notes/day)'),
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
                    _buildAnalyticsSection(analyticsAsync),
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
      },
    );
  }

  Widget _buildAnalyticsSection(AsyncValue<PlanAnalyticsResponse?> analyticsAsync) {
    return analyticsAsync.when(
      loading: () => const SizedBox(
        height: 240,
        child: Center(child: CircularProgressIndicator()),
      ),
      error: (err, _) => SizedBox(
        height: 240,
        child: Center(child: Text('Не удалось загрузить аналитику плана: $err')),
      ),
      data: (resp) {
        final points = _mapAnalyticsResponse(resp);
        final totals = resp?.totals;
        return _buildActiveAnalyticsSection(points, totals: totals);
      },
    );
  }

  String _metricLabel(String m) {
    switch (m) {
      case 'sets_count':
        return 'Сеты';
      case 'volume_sum':
        return 'Повторения';
      case 'intensity_avg':
        return 'Интенсивность (ср.)';
      case 'effort_avg':
        return 'Усилие (RPE ср.)';
      default:
        return m;
    }
  }

  List<PlanAnalyticsPoint> _mapAnalyticsResponse(PlanAnalyticsResponse? resp) {
    if (resp == null) return const [];
    final items = List.of(resp.items);
    items.sort((a, b) {
      final ao = a.orderIndex ?? 1 << 30;
      final bo = b.orderIndex ?? 1 << 30;
      if (ao != bo) return ao.compareTo(bo);
      return a.workoutId.compareTo(b.workoutId);
    });
    int order = 0;
    return items.map((item) {
      final label = item.date != null
          ? DateFormat('MMM d').format(item.date!.toLocal())
          : (item.orderIndex != null ? 'Day ${item.orderIndex}' : '#${order + 1}');
      return PlanAnalyticsPoint(
        order: order++,
        label: label,
        values: item.metrics,
        actualValues: item.actualMetrics,
      );
    }).toList(growable: false);
  }

  Widget _buildActiveAnalyticsSection(List<PlanAnalyticsPoint> analytics, {Map<String, double>? totals}) {
    return Card(
      elevation: 1,
      color: Colors.white,
      margin: const EdgeInsets.symmetric(horizontal: 16),
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
      child: Padding(
        padding: const EdgeInsets.fromLTRB(12, 10, 12, 10),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Expanded(
                  child: DropdownButtonFormField<String>(
                    value: _metricX,
                    decoration: const InputDecoration(labelText: 'Ось X'),
                    items: _metrics
                        .map((m) => DropdownMenuItem<String>(value: m, child: Text(_metricLabel(m))))
                        .toList(),
                    onChanged: (v) => setState(() => _metricX = v ?? _metricX),
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: DropdownButtonFormField<String>(
                    value: _metricY,
                    decoration: const InputDecoration(labelText: 'Ось Y'),
                    items: _metrics
                        .map((m) => DropdownMenuItem<String>(value: m, child: Text(_metricLabel(m))))
                        .toList(),
                    onChanged: (v) => setState(() => _metricY = v ?? _metricY),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 10),
            if (totals != null && totals.isNotEmpty)
              Padding(
                padding: const EdgeInsets.only(bottom: 12),
                child: Wrap(
                  spacing: 8,
                  runSpacing: 8,
                  children: totals.entries.map((entry) {
                    final label = _metricLabel(entry.key);
                    final value = entry.value;
                    return Chip(
                      label: Text('$label: ${value.toStringAsFixed(2)}'),
                    );
                  }).toList(),
                ),
              ),
            SizedBox(
              height: 240,
              child: PlanAnalyticsChart(
                points: analytics,
                metricX: _metricX,
                metricY: _metricY,
                emptyText: 'Нет аналитики по плану',
                showScatterAxisTitles: false,
              ),
            ),
          ],
        ),
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

  Future<Map<String, dynamic>> _buildChatContext() async {
    try {
      final plan = await ref.read(coachActivePlanProvider(widget.athleteId).future);
      final nowIso = DateTime.now().toUtc().toIso8601String();
      final selectionDate = _selectedDay.toIso8601String().split('T').first;

      final base = <String, dynamic>{
        'v': 1,
        'app': 'WorkoutApp',
        'screen': 'coach_athlete_plan',
        'role': 'coach',
        'timestamp': nowIso,
        'default_mass_edit_target': 'applied',
        'entities': <String, dynamic>{},
        'selection': <String, dynamic>{
          'athlete_id': widget.athleteId,
          'athlete_name': widget.athleteName,
          'date': selectionDate,
        },
      };

      final entities = base['entities'] as Map<String, dynamic>;
      if (plan != null) {
        entities['active_applied_plan'] = {
          'id': plan.id,
          'calendar_plan_id': plan.calendarPlanId,
          'name': plan.calendarPlan.name,
          'status': plan.status ?? 'active',
          'start_date': plan.startDate?.toIso8601String(),
          'end_date': plan.endDate.toIso8601String(),
          'adherence_pct': plan.adherencePct,
          'planned_sessions_total': plan.plannedSessionsTotal,
          'actual_sessions_completed': plan.actualSessionsCompleted,
        };

        entities['calendar_plan'] = {
          'id': plan.calendarPlan.id,
          'name': plan.calendarPlan.name,
          'primary_goal': plan.calendarPlan.primaryGoal,
          'intended_experience_level':
              plan.calendarPlan.intendedExperienceLevel,
          'intended_frequency_per_week':
              plan.calendarPlan.intendedFrequencyPerWeek,
        };
      }

      return base;
    } catch (e) {
      return <String, dynamic>{
        'v': 1,
        'app': 'WorkoutApp',
        'screen': 'coach_athlete_plan',
        'role': 'coach',
        'timestamp': DateTime.now().toUtc().toIso8601String(),
        'error': e.toString(),
      };
    }
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
                Row(
                  children: [
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(workout.name, style: AppTextStyles.titleMedium),
                          Text(_timeOrDate(workout), style: AppTextStyles.bodySmall),
                        ],
                      ),
                    ),
                    IconButton(
                      icon: const Icon(Icons.add_circle_outline),
                      tooltip: 'Добавить упражнение',
                      onPressed: workout.id == null ? null : () => _addExerciseInstance(workout),
                    ),
                  ],
                ),
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
                          contentPadding: EdgeInsets.zero,
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
                          trailing: Row(
                            mainAxisSize: MainAxisSize.min,
                            children: [
                              IconButton(
                                icon: const Icon(Icons.edit),
                                onPressed: ex.id == null ? null : () => _editExerciseInstance(ex),
                                tooltip: 'Редактировать',
                              ),
                              IconButton(
                                icon: const Icon(Icons.delete_outline, color: Colors.redAccent),
                                onPressed: ex.id == null ? null : () => _deleteExerciseInstance(ex),
                                tooltip: 'Удалить',
                              ),
                            ],
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

  Future<void> _addExerciseInstance(Workout workout) async {
    await _showExerciseEditor(workout: workout);
  }

  Future<void> _deleteExerciseInstance(ExerciseInstance instance) async {
    if (instance.id == null) return;
    final confirm = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Удалить упражнение?'),
        content: Text('Вы уверены, что хотите удалить ${instance.exerciseDefinition?.name ?? 'упражнение'} из тренировки?'),
        actions: [
          TextButton(onPressed: () => Navigator.of(ctx).pop(false), child: const Text('Отмена')),
          FilledButton(
            style: FilledButton.styleFrom(backgroundColor: Colors.redAccent),
            onPressed: () => Navigator.of(ctx).pop(true),
            child: const Text('Удалить'),
          ),
        ],
      ),
    );

    if (confirm != true) return;

    try {
      final svc = ref.read(crmCoachServiceProvider);
      await svc.deleteExerciseInstance(
        athleteId: widget.athleteId,
        instanceId: instance.id!,
      );
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Упражнение удалено')));
        Navigator.of(context).pop(); // Close bottom sheet if needed
        ref.invalidate(coachActivePlanWorkoutsProvider(widget.athleteId));
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('Ошибка при удалении: $e')));
      }
    }
  }

  Future<void> _editExerciseInstance(ExerciseInstance instance) async {
    await _showExerciseEditor(instance: instance);
  }

  Future<void> _showExerciseEditor({Workout? workout, ExerciseInstance? instance}) async {
    final isEdit = instance != null;
    final workoutId = workout?.id ?? instance?.workoutId;
    if (workoutId == null) return;

    // Fetch definitions
    List<ExerciseDefinition> definitions = [];
    try {
      definitions = await ref.read(exerciseServiceProvider).getExerciseDefinitions();
    } catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('Error loading exercises: $e')));
      return;
    }
    
    // Sort definitions by name
    definitions.sort((a, b) => a.name.compareTo(b.name));

    // Initial state
    int? selectedExerciseId = instance?.exerciseListId ?? (definitions.isNotEmpty ? definitions.first.id : null);
    String notes = instance?.notes ?? '';
    int? order = instance?.order;
    // Create mutable copy of sets
    List<ExerciseSetDto> sets = List.from(instance?.sets ?? []);
    // Ensure at least one set for new exercise
    if (!isEdit && sets.isEmpty) {
      sets.add(const ExerciseSetDto(reps: 10, weight: 20, rpe: 8));
    }

    if (!mounted) return;

    await showDialog(
      context: context,
      builder: (ctx) {
        return StatefulBuilder(
          builder: (context, setState) {
            return AlertDialog(
              title: Text(isEdit ? 'Редактировать упражнение' : 'Добавить упражнение'),
              content: SizedBox(
                width: double.maxFinite,
                child: SingleChildScrollView(
                  child: Column(
                    mainAxisSize: MainAxisSize.min,
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      // Exercise Selector
                      DropdownButtonFormField<int>(
                        value: selectedExerciseId,
                        isExpanded: true,
                        items: definitions.map((d) => DropdownMenuItem(
                          value: d.id,
                          child: Text(d.name, overflow: TextOverflow.ellipsis),
                        )).toList(),
                        onChanged: (val) => setState(() => selectedExerciseId = val),
                        decoration: const InputDecoration(labelText: 'Упражнение'),
                      ),
                      const SizedBox(height: 12),
                      TextFormField(
                        initialValue: notes,
                        decoration: const InputDecoration(labelText: 'Заметки'),
                        onChanged: (val) => notes = val,
                        maxLines: 2,
                      ),
                      const SizedBox(height: 12),
                      TextFormField(
                        initialValue: order?.toString() ?? '',
                        decoration: const InputDecoration(labelText: 'Порядок (Order)'),
                        keyboardType: TextInputType.number,
                        onChanged: (val) => order = int.tryParse(val),
                      ),
                      const SizedBox(height: 16),
                      Row(
                        mainAxisAlignment: MainAxisAlignment.spaceBetween,
                        children: [
                          const Text('Сеты', style: TextStyle(fontWeight: FontWeight.bold)),
                          IconButton(
                            icon: const Icon(Icons.add_circle_outline),
                            onPressed: () => setState(() {
                              // Copy previous set values if exists
                              final last = sets.isNotEmpty ? sets.last : const ExerciseSetDto(reps: 10, weight: 20, rpe: 8);
                              sets.add(last.copyWith(id: null)); 
                            }),
                            tooltip: 'Добавить сет',
                          )
                        ],
                      ),
                      if (sets.isEmpty)
                        const Text('Нет сетов', style: TextStyle(color: Colors.grey)),
                        
                      ...sets.asMap().entries.map((entry) {
                        final index = entry.key;
                        final set = entry.value;
                        return Card(
                          margin: const EdgeInsets.symmetric(vertical: 4),
                          child: Padding(
                            padding: const EdgeInsets.all(8.0),
                            child: Row(
                              children: [
                                SizedBox(width: 20, child: Text('${index + 1}')),
                                Expanded(
                                  child: TextFormField(
                                    initialValue: set.reps.toString(),
                                    decoration: const InputDecoration(labelText: 'Reps', isDense: true, contentPadding: EdgeInsets.all(8)),
                                    keyboardType: TextInputType.number,
                                    onChanged: (v) {
                                      sets[index] = set.copyWith(reps: int.tryParse(v) ?? 0);
                                    },
                                  ),
                                ),
                                const SizedBox(width: 8),
                                Expanded(
                                  child: TextFormField(
                                    initialValue: set.weight.toString(),
                                    decoration: const InputDecoration(labelText: 'Kg', isDense: true, contentPadding: EdgeInsets.all(8)),
                                    keyboardType: const TextInputType.numberWithOptions(decimal: true),
                                    onChanged: (v) {
                                      sets[index] = set.copyWith(weight: double.tryParse(v) ?? 0.0);
                                    },
                                  ),
                                ),
                                const SizedBox(width: 8),
                                Expanded(
                                  child: TextFormField(
                                    initialValue: set.rpe?.toString() ?? '',
                                    decoration: const InputDecoration(labelText: 'RPE', isDense: true, contentPadding: EdgeInsets.all(8)),
                                    keyboardType: const TextInputType.numberWithOptions(decimal: true),
                                    onChanged: (v) {
                                      sets[index] = set.copyWith(rpe: double.tryParse(v));
                                    },
                                  ),
                                ),
                                IconButton(
                                  icon: const Icon(Icons.close, size: 16, color: Colors.redAccent),
                                  padding: EdgeInsets.zero,
                                  constraints: const BoxConstraints(),
                                  onPressed: () => setState(() => sets.removeAt(index)),
                                )
                              ],
                            ),
                          ),
                        );
                      }).toList(),
                    ],
                  ),
                ),
              ),
              actions: [
                TextButton(onPressed: () => Navigator.of(ctx).pop(), child: const Text('Отмена')),
                FilledButton(
                  onPressed: () async {
                    if (selectedExerciseId == null) {
                      ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Выберите упражнение')));
                      return;
                    }
                    
                    try {
                      final svc = ref.read(crmCoachServiceProvider);
                      final payload = {
                        'exercise_list_id': selectedExerciseId,
                        'notes': notes.isEmpty ? null : notes,
                        if (order != null) 'order': order,
                        'sets': sets.map((s) => s.toFormData()).toList(),
                      };

                      if (isEdit) {
                        await svc.updateExerciseInstance(
                          athleteId: widget.athleteId,
                          instanceId: instance.id!,
                          payload: payload,
                        );
                      } else {
                        await svc.createExerciseInstance(
                          athleteId: widget.athleteId,
                          workoutId: workoutId,
                          payload: payload,
                        );
                      }
                      if (mounted) {
                         Navigator.of(ctx).pop();
                         ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(isEdit ? 'Обновлено' : 'Создано')));
                         // Refresh data
                         ref.invalidate(coachActivePlanWorkoutsProvider(widget.athleteId));
                         // Close the bottom sheet to avoid showing stale data
                         Navigator.of(context).pop(); 
                      }
                    } catch (e) {
                      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('Ошибка: $e')));
                    }
                  },
                  child: const Text('Сохранить'),
                ),
              ],
            );
          },
        );
      },
    );
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
