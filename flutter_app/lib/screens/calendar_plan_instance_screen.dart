import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:workout_app/models/calendar_plan_instance.dart';
import 'package:workout_app/services/logger_service.dart';
import 'package:workout_app/services/service_locator.dart';
import 'package:workout_app/services/applied_calendar_plan_service.dart';
import 'package:workout_app/models/apply_plan_request.dart';
import 'package:workout_app/models/user_max.dart';

class CalendarPlanInstanceScreen extends ConsumerStatefulWidget {
  final int instanceId;
  const CalendarPlanInstanceScreen({super.key, required this.instanceId});

  @override
  ConsumerState<CalendarPlanInstanceScreen> createState() => _CalendarPlanInstanceScreenState();
}

class _CalendarPlanInstanceScreenState extends ConsumerState<CalendarPlanInstanceScreen> {
  final LoggerService _logger = LoggerService('CalendarPlanInstanceScreen');
  bool _isLoading = true;
  String? _errorMessage;
  CalendarPlanInstance? _instance;
  Map<int, String> _exerciseNames = {};

  // Apply Plan state
  bool _isApplying = false;
  List<UserMax> _userMaxes = [];
  final Set<int> _selectedUserMaxIds = {};
  bool _computeWeights = true;
  double _roundingStep = 2.5;
  String _roundingMode = 'nearest'; // 'nearest' | 'floor' | 'ceil'
  bool _generateWorkouts = true;
  DateTime? _startDate;

  late final TextEditingController _nameCtrl;
  late final TextEditingController _durationCtrl;

  @override
  void initState() {
    super.initState();
    _nameCtrl = TextEditingController();
    _durationCtrl = TextEditingController();
    _load();
  }

  Future<void> _loadUserMaxes() async {
    try {
      final maxes = await context.userMaxService.getUserMaxes();
      if (!mounted) return;
      setState(() { _userMaxes = maxes; });
    } catch (e, st) {
      _logger.e('Failed to load user maxes: $e\n$st');
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Не удалось загрузить максимумы')),
      );
    }
  }

  Future<void> _openApplyPlanSheet() async {
    if (_userMaxes.isEmpty) {
      await _loadUserMaxes();
    }
    if (!mounted) return;

    bool localSubmitting = false;

    await showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      builder: (ctx) {
        return StatefulBuilder(
          builder: (context, setModalState) {
            Future<void> submit() async {
              if (_selectedUserMaxIds.isEmpty) {
                ScaffoldMessenger.of(context).showSnackBar(
                  const SnackBar(content: Text('Выберите хотя бы один максимум')),
                );
                return;
              }
              setModalState(() { localSubmitting = true; });
              try {
                final svc = ref.read(appliedCalendarPlanServiceProvider);
                final req = ApplyPlanRequest(
                  userMaxIds: _selectedUserMaxIds.toList(),
                  compute: ComputeSettings(
                    computeWeights: _computeWeights,
                    roundingStep: _roundingStep,
                    roundingMode: _roundingMode,
                    generateWorkouts: _generateWorkouts,
                    startDate: _startDate,
                  ),
                );
                await svc.applyPlanFromInstance(instanceId: _instance!.id, request: req);
                if (!mounted) return;
                Navigator.of(context).pop();
                ScaffoldMessenger.of(context).showSnackBar(
                  const SnackBar(content: Text('План применён')),
                );
              } catch (e, st) {
                _logger.e('Failed to apply plan: $e\n$st');
                if (!mounted) return;
                ScaffoldMessenger.of(context).showSnackBar(
                  const SnackBar(content: Text('Ошибка при применении плана')),
                );
              } finally {
                setModalState(() { localSubmitting = false; });
              }
            }

            return Padding(
              padding: EdgeInsets.only(
                bottom: MediaQuery.of(context).viewInsets.bottom,
                left: 16,
                right: 16,
                top: 16,
              ),
              child: SafeArea(
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      children: [
                        const Text('Применить план', style: TextStyle(fontSize: 18, fontWeight: FontWeight.w600)),
                        IconButton(
                          icon: const Icon(Icons.close),
                          onPressed: () => Navigator.of(context).pop(),
                        ),
                      ],
                    ),
                    const SizedBox(height: 8),
                    Text('Выберите максимумы', style: Theme.of(context).textTheme.titleSmall),
                    const SizedBox(height: 8),
                    if (_userMaxes.isEmpty)
                      const Padding(
                        padding: EdgeInsets.symmetric(vertical: 8.0),
                        child: Text('Максимумы не найдены. Создайте их на экране профиля.'),
                      )
                    else
                      SizedBox(
                        height: 200,
                        child: ListView.builder(
                          itemCount: _userMaxes.length,
                          itemBuilder: (context, index) {
                            final um = _userMaxes[index];
                            final exerciseName = _exerciseNames[um.exerciseId] ?? 'Упражнение #${um.exerciseId}';
                            final uid = um.id;
                            final selected = uid != null && _selectedUserMaxIds.contains(uid);
                            return CheckboxListTile(
                              value: selected,
                              onChanged: (val) {
                                setModalState(() {
                                  if (uid == null) return;
                                  if (val == true) {
                                    _selectedUserMaxIds.add(uid);
                                  } else {
                                    _selectedUserMaxIds.remove(uid);
                                  }
                                });
                              },
                              title: Text(exerciseName),
                              subtitle: Text('RM${um.repMax}: ${um.maxWeight} кг'),
                            );
                          },
                        ),
                      ),
                    const SizedBox(height: 12),
                    SwitchListTile(
                      title: const Text('Вычислять веса'),
                      value: _computeWeights,
                      onChanged: (v) => setModalState(() { _computeWeights = v; }),
                    ),
                    if (_computeWeights) ...[
                      Row(
                        children: [
                          Expanded(
                            child: DropdownButtonFormField<double>(
                              decoration: const InputDecoration(labelText: 'Шаг округления'),
                              value: _roundingStep,
                              items: const [0.5, 1.25, 2.5, 5.0]
                                  .map((v) => DropdownMenuItem(value: v, child: Text(v.toString())))
                                  .toList(),
                              onChanged: (v) => setModalState(() { if (v != null) _roundingStep = v; }),
                            ),
                          ),
                          const SizedBox(width: 12),
                          Expanded(
                            child: DropdownButtonFormField<String>(
                              decoration: const InputDecoration(labelText: 'Режим округления'),
                              value: _roundingMode,
                              items: const [
                                DropdownMenuItem(value: 'nearest', child: Text('Ближайшее')),
                                DropdownMenuItem(value: 'floor', child: Text('Вниз')),
                                DropdownMenuItem(value: 'ceil', child: Text('Вверх')),
                              ],
                              onChanged: (v) => setModalState(() { if (v != null) _roundingMode = v; }),
                            ),
                          ),
                        ],
                      ),
                    ],
                    SwitchListTile(
                      title: const Text('Сгенерировать тренировки'),
                      value: _generateWorkouts,
                      onChanged: (v) => setModalState(() { _generateWorkouts = v; }),
                    ),
                    ListTile(
                      contentPadding: EdgeInsets.zero,
                      title: const Text('Дата начала'),
                      subtitle: Text(_startDate != null ? _startDate!.toLocal().toString().split(' ').first : 'Не выбрана'),
                      trailing: IconButton(
                        icon: const Icon(Icons.calendar_today),
                        onPressed: () async {
                          final now = DateTime.now();
                          final picked = await showDatePicker(
                            context: context,
                            initialDate: _startDate ?? now,
                            firstDate: DateTime(now.year - 1),
                            lastDate: DateTime(now.year + 2),
                          );
                          if (picked != null) {
                            setModalState(() { _startDate = picked; });
                          }
                        },
                      ),
                    ),
                    const SizedBox(height: 8),
                    Row(
                      children: [
                        Expanded(
                          child: OutlinedButton(
                            onPressed: localSubmitting ? null : () => Navigator.of(context).pop(),
                            child: const Text('Отмена'),
                          ),
                        ),
                        const SizedBox(width: 12),
                        Expanded(
                          child: ElevatedButton.icon(
                            onPressed: localSubmitting ? null : submit,
                            icon: localSubmitting
                                ? const SizedBox(width: 16, height: 16, child: CircularProgressIndicator(strokeWidth: 2))
                                : const Icon(Icons.check),
                            label: const Text('Применить'),
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 12),
                  ],
                ),
              ),
            );
          },
        );
      },
    );
  }

  @override
  void dispose() {
    _nameCtrl.dispose();
    _durationCtrl.dispose();
    super.dispose();
  }

  Future<void> _load() async {
    setState(() {
      _isLoading = true;
      _errorMessage = null;
    });
    try {
      final service = ref.read(calendarPlanInstanceServiceProvider);
      final data = await service.getInstance(widget.instanceId);
      if (!mounted) return;
      setState(() {
        _instance = data;
        _nameCtrl.text = data.name;
        _durationCtrl.text = data.durationWeeks.toString();
      });
      await _loadExerciseNamesForInstance(data);
    } catch (e, st) {
      _logger.e('Failed to load instance: $e\n$st');
      if (!mounted) return;
      setState(() {
        _errorMessage = 'Не удалось загрузить экземпляр плана';
      });
    } finally {
      if (mounted) setState(() => _isLoading = false);
    }
  }

  Future<void> _loadExerciseNamesForInstance(CalendarPlanInstance inst) async {
    try {
      final ids = <int>{};
      inst.schedule.forEach((_, items) {
        for (final it in items) {
          if (it.exerciseId != null) ids.add(it.exerciseId);
        }
      });
      if (ids.isEmpty) return;
      final svc = ref.read(exerciseServiceProvider);
      final defs = await svc.getExercisesByIds(ids.toList());
      if (!mounted) return;
      setState(() {
        _exerciseNames = {for (final d in defs) if (d.id != null) d.id!: d.name};
      });
    } catch (e, st) {
      _logger.w('Failed to load exercise names: $e\n$st');
    }
  }

  Future<void> _saveMeta() async {
    if (_instance == null) return;
    final name = _nameCtrl.text.trim();
    final weeks = int.tryParse(_durationCtrl.text.trim());
    if (weeks == null || weeks <= 0) {
      ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Введите корректную длительность')));
      return;
    }
    try {
      final service = ref.read(calendarPlanInstanceServiceProvider);
      final updated = await service.updateInstance(_instance!.id, {
        'name': name,
        'duration_weeks': weeks,
      });
      if (!mounted) return;
      setState(() => _instance = updated);
      ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Сохранено')));
    } catch (e, st) {
      _logger.e('Failed to save instance: $e\n$st');
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Ошибка сохранения')));
    }
  }

  Future<void> _editSet(String dayKey, int itemIndex, int setIndex) async {
    if (_instance == null) return;
    final item = _instance!.schedule[dayKey]![itemIndex];
    final set = item.sets[setIndex];

    final intensityCtrl = TextEditingController(text: (set.intensity ?? '').toString());
    final volumeCtrl = TextEditingController(text: (set.volume ?? '').toString());
    final effortCtrl = TextEditingController(text: (set.effort ?? '').toString());

    final result = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: Text('Редактировать сет #${set.id}'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            TextField(
              controller: intensityCtrl,
              decoration: const InputDecoration(labelText: 'Intensity (1-100)'),
              keyboardType: TextInputType.number,
            ),
            TextField(
              controller: volumeCtrl,
              decoration: const InputDecoration(labelText: 'Volume (>=1)'),
              keyboardType: TextInputType.number,
            ),
            TextField(
              controller: effortCtrl,
              decoration: const InputDecoration(labelText: 'Effort (1-10)'),
              keyboardType: TextInputType.number,
            ),
            const SizedBox(height: 8),
            Align(
              alignment: Alignment.centerRight,
              child: OutlinedButton.icon(
                icon: const Icon(Icons.calculate_outlined),
                label: const Text('Рассчитать по RPE'),
                onPressed: () async {
                  int? intensity = int.tryParse(intensityCtrl.text.trim());
                  int? volume = int.tryParse(volumeCtrl.text.trim());
                  double? effort = double.tryParse(effortCtrl.text.trim());

                  int provided = 0;
                  if (intensity != null) provided++;
                  if (volume != null) provided++;
                  if (effort != null) provided++;

                  if (provided < 2) {
                    if (mounted) {
                      ScaffoldMessenger.of(context).showSnackBar(
                        const SnackBar(content: Text('Введите минимум два параметра для расчёта')),
                      );
                    }
                    return;
                  }

                  try {
                    final rpeSvc = ref.read(rpeServiceProvider);
                    final resp = await rpeSvc.compute(
                      intensity: intensity,
                      volume: volume,
                      effort: effort,
                    );
                    final newIntensity = resp['intensity'];
                    final newVolume = resp['volume'];
                    final newEffort = resp['effort'];
                    if (newIntensity != null) intensityCtrl.text = newIntensity.toString();
                    if (newVolume != null) volumeCtrl.text = newVolume.toString();
                    if (newEffort != null) effortCtrl.text = newEffort.toString();
                    if (mounted) {
                      ScaffoldMessenger.of(context).showSnackBar(
                        const SnackBar(content: Text('Параметры рассчитаны')),
                      );
                    }
                  } catch (e, st) {
                    _logger.e('RPE compute failed: $e\n$st');
                    if (mounted) {
                      ScaffoldMessenger.of(context).showSnackBar(
                        const SnackBar(content: Text('Не удалось выполнить расчёт')),
                      );
                    }
                  }
                },
              ),
            ),
          ],
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('Отмена')),
          TextButton(onPressed: () => Navigator.pop(ctx, true), child: const Text('Сохранить')),
        ],
      ),
    );

    if (result != true) return;

    int? intensity = int.tryParse(intensityCtrl.text.trim());
    int? volume = int.tryParse(volumeCtrl.text.trim());
    int? effort = int.tryParse(effortCtrl.text.trim());

    // Clamp to valid ranges where applicable
    if (intensity != null) intensity = intensity.clamp(1, 100);
    if (effort != null) effort = effort.clamp(1, 10);
    if (volume != null && volume < 1) volume = 1;

    // Update local state
    setState(() {
      final newSets = List<ParamsSetInstance>.from(item.sets);
      newSets[setIndex] = ParamsSetInstance(
        id: set.id,
        intensity: intensity,
        effort: effort,
        volume: volume,
      );
      final newItem = ExerciseScheduleItemInstance(id: item.id, exerciseId: item.exerciseId, sets: newSets);
      final newItems = List<ExerciseScheduleItemInstance>.from(_instance!.schedule[dayKey]!);
      newItems[itemIndex] = newItem;
      final newSchedule = Map<String, List<ExerciseScheduleItemInstance>>.from(_instance!.schedule);
      newSchedule[dayKey] = newItems;
      _instance = CalendarPlanInstance(
        id: _instance!.id,
        sourcePlanId: _instance!.sourcePlanId,
        name: _instance!.name,
        schedule: newSchedule,
        durationWeeks: _instance!.durationWeeks,
      );
    });

    // Persist to backend
    try {
      final service = ref.read(calendarPlanInstanceServiceProvider);
      final payload = {
        'name': _instance!.name,
        'duration_weeks': _instance!.durationWeeks,
        'schedule': _scheduleToJson(_instance!.schedule),
      };
      _logger.d('Updating instance ${_instance!.id} with payload: $payload');
      await service.updateInstance(_instance!.id, payload);
    } catch (e, st) {
      _logger.e('Failed to persist set: $e\n$st');
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Ошибка сохранения сета')));
      }
    }
  }

  Map<String, dynamic> _scheduleToJson(Map<String, List<ExerciseScheduleItemInstance>> schedule) {
    return schedule.map((day, items) => MapEntry(day, items.map((it) => it.toJson()).toList()));
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Редактор плана'),
        actions: [
          IconButton(onPressed: _saveMeta, icon: const Icon(Icons.save)),
          IconButton(
            onPressed: _openApplyPlanSheet,
            tooltip: 'Применить план',
            icon: const Icon(Icons.playlist_add_check_circle),
          ),
        ],
      ),
      body: _isLoading
          ? const Center(child: CircularProgressIndicator())
          : _errorMessage != null
              ? Center(child: Text(_errorMessage!))
              : _instance == null
                  ? const SizedBox.shrink()
                  : Padding(
                      padding: const EdgeInsets.all(16.0),
                      child: SingleChildScrollView(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            TextField(
                              controller: _nameCtrl,
                              decoration: const InputDecoration(labelText: 'Название плана'),
                            ),
                            const SizedBox(height: 12),
                            TextField(
                              controller: _durationCtrl,
                              decoration: const InputDecoration(labelText: 'Длительность (недели)'),
                              keyboardType: TextInputType.number,
                            ),
                            const SizedBox(height: 16),
                            Text('Расписание', style: Theme.of(context).textTheme.titleMedium),
                            const SizedBox(height: 8),
                            _buildSchedule(_instance!),
                          ],
                        ),
                      ),
                    ),
    );
  }

  Widget _buildSchedule(CalendarPlanInstance inst) {
    if (inst.schedule.isEmpty) return const Text('Пусто');
    final entries = inst.schedule.entries.toList();
    return ListView.builder(
      shrinkWrap: true,
      physics: const NeverScrollableScrollPhysics(),
      itemCount: entries.length,
      itemBuilder: (context, idx) {
        final day = entries[idx].key;
        final items = entries[idx].value;
        return Card(
          margin: const EdgeInsets.only(bottom: 12),
          child: Padding(
            padding: const EdgeInsets.all(12.0),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Text(day, style: Theme.of(context).textTheme.titleSmall),
                    Text('${items.length} упражн.', style: Theme.of(context).textTheme.bodySmall),
                  ],
                ),
                const SizedBox(height: 8),
                if (items.isEmpty) const Text('Нет упражнений')
                else ...items.asMap().entries.map((e) => _buildExerciseCard(day, e.key, e.value)).toList(),
              ],
            ),
          ),
        );
      },
    );
  }

  Widget _buildExerciseCard(String dayKey, int itemIndex, ExerciseScheduleItemInstance item) {
    final theme = Theme.of(context);
    final title = (item.exerciseId != null && _exerciseNames.containsKey(item.exerciseId))
        ? _exerciseNames[item.exerciseId]!
        : 'Упражнение #${item.exerciseId}';
    return Card(
      margin: const EdgeInsets.symmetric(vertical: 6),
      elevation: 0,
      shape: RoundedRectangleBorder(
        side: BorderSide(color: theme.dividerColor),
        borderRadius: BorderRadius.circular(8),
      ),
      child: Padding(
        padding: const EdgeInsets.all(12.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Text(title, style: theme.textTheme.titleSmall),
                Text('${item.sets.length} сет(ов)', style: theme.textTheme.bodySmall),
              ],
            ),
            const SizedBox(height: 8),
            ...item.sets.asMap().entries.map((entry) {
              final setIdx = entry.key;
              final s = entry.value;
              return Container(
                margin: const EdgeInsets.symmetric(vertical: 4),
                padding: const EdgeInsets.all(10),
                decoration: BoxDecoration(
                  border: Border.all(color: theme.dividerColor),
                  borderRadius: BorderRadius.circular(8),
                ),
                child: Row(
                  children: [
                    Container(
                      width: 28,
                      height: 28,
                      alignment: Alignment.center,
                      decoration: BoxDecoration(
                        color: theme.colorScheme.primary.withOpacity(0.1),
                        shape: BoxShape.circle,
                      ),
                      child: Text('${s.id}', style: theme.textTheme.labelLarge?.copyWith(color: theme.colorScheme.primary)),
                    ),
                    const SizedBox(width: 12),
                    Expanded(
                      child: Wrap(
                        spacing: 8,
                        runSpacing: 8,
                        children: [
                          _chip('Intensity', s.intensity?.toString() ?? '-'),
                          _chip('Volume', s.volume?.toString() ?? '-'),
                          _chip('Effort', s.effort?.toString() ?? '-'),
                        ],
                      ),
                    ),
                    IconButton(
                      icon: const Icon(Icons.edit_outlined),
                      tooltip: 'Редактировать сет',
                      onPressed: () => _editSet(dayKey, itemIndex, setIdx),
                    ),
                  ],
                ),
              );
            }),
          ],
        ),
      ),
    );
  }

  Widget _chip(String label, String value) {
    final theme = Theme.of(context);
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
      decoration: BoxDecoration(
        color: theme.colorScheme.surfaceVariant,
        borderRadius: BorderRadius.circular(16),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Text('$label: ', style: theme.textTheme.bodySmall?.copyWith(fontWeight: FontWeight.w600)),
          Text(value, style: theme.textTheme.bodySmall),
        ],
      ),
    );
  }
}
