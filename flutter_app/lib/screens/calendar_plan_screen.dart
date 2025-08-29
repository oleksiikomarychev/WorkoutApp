import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:workout_app/services/logger_service.dart';
import 'package:workout_app/services/calendar_plan_service.dart';
import 'package:workout_app/models/calendar_plan.dart';
import 'package:workout_app/services/service_locator.dart';
import 'package:workout_app/screens/calendar_plan_instance_screen.dart';
import 'package:workout_app/models/apply_plan_request.dart';
import 'package:workout_app/models/user_max.dart';
import 'package:workout_app/screens/mesocycle_editor_screen.dart';
import 'package:workout_app/models/plan_schedule.dart';
import 'package:workout_app/models/mesocycle.dart';
import 'package:workout_app/models/microcycle.dart';


class CalendarPlanScreen extends ConsumerStatefulWidget {
  final int planId;
  const CalendarPlanScreen({super.key, required this.planId});

  @override
  ConsumerState<CalendarPlanScreen> createState() => _CalendarPlanScreenState();
}

class _CalendarPlanScreenState extends ConsumerState<CalendarPlanScreen> {
  final LoggerService _logger = LoggerService('CalendarPlanScreen');
  bool _isLoading = true;
  String? _errorMessage;
  CalendarPlan? _plan;
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
  // Nested structure loaded separately because /calendar-plans/:id may not embed them
  List<Mesocycle> _mesocycles = [];

  Future<void> _loadPlan() async {
    if (!mounted) return;
    
    setState(() {
      _isLoading = true;
      _errorMessage = null;
    });
    
    try {
      final service = ref.read(calendarPlanServiceProvider);
      final plan = await service.getCalendarPlan(widget.planId);
      if (!mounted) return;
      setState(() { _plan = plan; });
      // Load exercise names from legacy top-level schedule (if any)
      await _loadExerciseNamesForPlan(plan);
      // Load mesocycles and their microcycles to show nested schedule
      await _loadMesocyclesForPlan(plan.id);
      // After nested structure is loaded, also load exercise names referenced there
      await _loadExerciseNamesFromMesocycles(_mesocycles);
    } catch (e, stackTrace) {
      _logger.e('Error loading calendar data: $e\n$stackTrace');
      
      if (!mounted) return;
      
      setState(() {
        _errorMessage = 'Не удалось загрузить план. Пожалуйста, попробуйте позже.';
      });
    } finally {
      if (mounted) {
        setState(() => _isLoading = false);
      }
    }
  }

  // Build a section for a mesocycle with its microcycles
  Widget _buildMesocycleSection(Mesocycle meso) {
    return GestureDetector(
      onLongPress: () => _showMesocycleInfo(meso),
      child: Card(
        margin: const EdgeInsets.only(bottom: 12),
        child: ExpansionTile(
          key: PageStorageKey('meso-${meso.id}'),
          title: Text('Мезоцикл: ${meso.name}', style: Theme.of(context).textTheme.titleSmall),
          subtitle: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text('${meso.microcycles.length} микро.', style: Theme.of(context).textTheme.bodySmall),
              if (meso.normalizationValue != null && (meso.normalizationUnit ?? '').isNotEmpty)
                Padding(
                  padding: const EdgeInsets.only(top: 2),
                  child: Text('Нормировка: ${meso.normalizationValue} ${meso.normalizationUnit}', style: Theme.of(context).textTheme.bodySmall),
                ),
              if ((meso.notes ?? '').isNotEmpty)
                Padding(
                  padding: const EdgeInsets.only(top: 2),
                  child: Text(meso.notes!, style: Theme.of(context).textTheme.bodySmall),
                ),
            ],
          ),
          maintainState: true,
          childrenPadding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
          children: [
            if (meso.microcycles.isEmpty)
              const Padding(
                padding: EdgeInsets.only(bottom: 8),
                child: Text('Нет микроциклов'),
              )
            else
              ...meso.microcycles.map((m) => _buildMicrocycleCard(m)).toList(),
            const SizedBox(height: 4),
          ],
        ),
      ),
    );
  }

  void _showMesocycleInfo(Mesocycle meso) {
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      builder: (ctx) {
        final nameCtrl = TextEditingController(text: meso.name);
        final notesCtrl = TextEditingController(text: meso.notes ?? '');
        final orderCtrl = TextEditingController(text: meso.orderIndex.toString());
        final normValueCtrl = TextEditingController(text: (meso.normalizationValue != null) ? meso.normalizationValue!.toString() : '');
        String? normUnit = meso.normalizationUnit;
        final formKey = GlobalKey<FormState>();
        bool localSubmitting = false;

        return StatefulBuilder(
          builder: (context, setModalState) {
            Future<void> save() async {
              if (localSubmitting) return;
              if (!formKey.currentState!.validate()) return;
              setModalState(() => localSubmitting = true);
              try {
                final newName = nameCtrl.text.trim();
                final newNotes = notesCtrl.text.trim();
                final newOrder = int.tryParse(orderCtrl.text.trim());
                final newNormVal = normValueCtrl.text.trim().isEmpty ? null : double.tryParse(normValueCtrl.text.trim());
                final svc = ref.read(mesocycleServiceProvider);
                await svc.updateMesocycle(
                  meso.id,
                  MesocycleUpdateDto(
                    name: newName.isEmpty ? null : newName,
                    notes: newNotes.isEmpty ? '' : newNotes,
                    orderIndex: newOrder,
                    normalizationValue: newNormVal,
                    normalizationUnit: normUnit,
                  ),
                );
                if (!mounted) return;
                await _loadMesocyclesForPlan(widget.planId);
                Navigator.of(ctx).pop();
                ScaffoldMessenger.of(context).showSnackBar(
                  const SnackBar(content: Text('Мезоцикл обновлён')),
                );
              } catch (e, st) {
                _logger.e('Failed to update mesocycle: $e\n$st');
                if (!mounted) return;
                ScaffoldMessenger.of(context).showSnackBar(
                  const SnackBar(content: Text('Не удалось обновить мезоцикл')),
                );
              } finally {
                // Avoid setState after pop; do not reset localSubmitting here if sheet closed
              }
            }

            final bottomInset = MediaQuery.of(context).viewInsets.bottom;

            return SafeArea(
              child: Padding(
                padding: EdgeInsets.only(left: 16, right: 16, top: 16, bottom: bottomInset + 16),
                child: Form(
                  key: formKey,
                  child: Column(
                    mainAxisSize: MainAxisSize.min,
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        mainAxisAlignment: MainAxisAlignment.spaceBetween,
                        children: [
                          const Text('Мезоцикл', style: TextStyle(fontSize: 18, fontWeight: FontWeight.w600)),
                          IconButton(
                            icon: const Icon(Icons.close),
                            onPressed: () => Navigator.of(ctx).pop(),
                          ),
                        ],
                      ),
                      const SizedBox(height: 8),
                      TextFormField(
                        controller: nameCtrl,
                        decoration: const InputDecoration(labelText: 'Название'),
                        textInputAction: TextInputAction.next,
                        validator: (v) => (v == null || v.trim().isEmpty) ? 'Введите название' : null,
                      ),
                      const SizedBox(height: 8),
                      TextFormField(
                        controller: orderCtrl,
                        decoration: const InputDecoration(labelText: 'Порядок (целое)'),
                        keyboardType: TextInputType.number,
                        textInputAction: TextInputAction.next,
                        validator: (v) {
                          if (v == null || v.trim().isEmpty) return null; // можно оставить как есть
                          return int.tryParse(v.trim()) == null ? 'Введите число' : null;
                        },
                      ),
                      const SizedBox(height: 8),
                      TextFormField(
                        controller: notesCtrl,
                        decoration: const InputDecoration(labelText: 'Описание'),
                        minLines: 2,
                        maxLines: 5,
                      ),
                      const SizedBox(height: 8),
                      TextFormField(
                        controller: normValueCtrl,
                        decoration: const InputDecoration(labelText: 'Нормировка (значение)'),
                        keyboardType: const TextInputType.numberWithOptions(decimal: true),
                        validator: (v) {
                          if (v == null || v.trim().isEmpty) return null;
                          return double.tryParse(v.trim()) == null ? 'Введите число' : null;
                        },
                      ),
                      const SizedBox(height: 8),
                      DropdownButtonFormField<String>(
                        decoration: const InputDecoration(labelText: 'Ед. нормировки'),
                        value: normUnit,
                        items: const [
                          DropdownMenuItem(value: 'kg', child: Text('kg')),
                          DropdownMenuItem(value: '%', child: Text('%')),
                        ],
                        onChanged: (v) => setModalState(() { normUnit = v; }),
                      ),
                      const SizedBox(height: 12),
                      Row(
                        children: [
                          Expanded(
                            child: OutlinedButton(
                              onPressed: localSubmitting ? null : () => Navigator.of(ctx).pop(),
                              child: const Text('Отмена'),
                            ),
                          ),
                          const SizedBox(width: 12),
                          Expanded(
                            child: ElevatedButton.icon(
                              onPressed: localSubmitting ? null : save,
                              icon: localSubmitting
                                  ? const SizedBox(width: 16, height: 16, child: CircularProgressIndicator(strokeWidth: 2))
                                  : const Icon(Icons.save),
                              label: const Text('Сохранить'),
                            ),
                          ),
                        ],
                      ),
                    ],
                  ),
                ),
              ),
            );
          },
        );
      },
    );
  }

  Widget _buildMicrocycleCard(Microcycle micro) {
    return GestureDetector(
      onLongPress: () => _showMicrocycleInfo(micro),
      child: Card(
        margin: const EdgeInsets.only(bottom: 12),
        child: ExpansionTile(
          key: PageStorageKey('micro-${micro.id}'),
          title: Text('Микроцикл: ${micro.name}', style: Theme.of(context).textTheme.titleSmall),
          subtitle: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text('${micro.schedule.length} дн.', style: Theme.of(context).textTheme.bodySmall),
              if (micro.normalizationValue != null && (micro.normalizationUnit ?? '').isNotEmpty)
                Padding(
                  padding: const EdgeInsets.only(top: 2),
                  child: Text('Нормировка: ${micro.normalizationValue} ${micro.normalizationUnit}', style: Theme.of(context).textTheme.bodySmall),
                ),
              if ((micro.notes ?? '').isNotEmpty)
                Padding(
                  padding: const EdgeInsets.only(top: 2),
                  child: Text(micro.notes!, style: Theme.of(context).textTheme.bodySmall),
                ),
            ],
          ),
          maintainState: true,
          childrenPadding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
          children: [
            _buildMicrocycleSchedule(micro),
          ],
        ),
      ),
    );
  }

  void _showMicrocycleInfo(Microcycle micro) {
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      builder: (ctx) {
        final nameCtrl = TextEditingController(text: micro.name);
        final notesCtrl = TextEditingController(text: micro.notes ?? '');
        final orderCtrl = TextEditingController(text: micro.orderIndex.toString());
        final normValueCtrl = TextEditingController(text: (micro.normalizationValue != null) ? micro.normalizationValue!.toString() : '');
        String? normUnit = micro.normalizationUnit;
        final formKey = GlobalKey<FormState>();
        bool localSubmitting = false;

        return StatefulBuilder(
          builder: (context, setModalState) {
            Future<void> save() async {
              if (localSubmitting) return;
              if (!formKey.currentState!.validate()) return;
              setModalState(() => localSubmitting = true);
              try {
                final newName = nameCtrl.text.trim();
                final newNotes = notesCtrl.text.trim();
                final newOrder = int.tryParse(orderCtrl.text.trim());
                final newNormVal = normValueCtrl.text.trim().isEmpty ? null : double.tryParse(normValueCtrl.text.trim());
                final svc = ref.read(mesocycleServiceProvider);
                await svc.updateMicrocycle(
                  micro.id,
                  MicrocycleUpdateDto(
                    name: newName.isEmpty ? null : newName,
                    notes: newNotes.isEmpty ? '' : newNotes,
                    orderIndex: newOrder,
                    normalizationValue: newNormVal,
                    normalizationUnit: normUnit,
                  ),
                );
                if (!mounted) return;
                await _loadMesocyclesForPlan(widget.planId);
                Navigator.of(ctx).pop();
                ScaffoldMessenger.of(context).showSnackBar(
                  const SnackBar(content: Text('Микроцикл обновлён')),
                );
              } catch (e, st) {
                _logger.e('Failed to update microcycle: $e\n$st');
                if (!mounted) return;
                ScaffoldMessenger.of(context).showSnackBar(
                  const SnackBar(content: Text('Не удалось обновить микроцикл')),
                );
              } finally {
                // Avoid setState after pop; do not reset localSubmitting here if sheet closed
              }
            }

            final bottomInset = MediaQuery.of(context).viewInsets.bottom;

            return SafeArea(
              child: Padding(
                padding: EdgeInsets.only(left: 16, right: 16, top: 16, bottom: bottomInset + 16),
                child: Form(
                  key: formKey,
                  child: Column(
                    mainAxisSize: MainAxisSize.min,
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        mainAxisAlignment: MainAxisAlignment.spaceBetween,
                        children: [
                          const Text('Микроцикл', style: TextStyle(fontSize: 18, fontWeight: FontWeight.w600)),
                          IconButton(
                            icon: const Icon(Icons.close),
                            onPressed: () => Navigator.of(ctx).pop(),
                          ),
                        ],
                      ),
                      const SizedBox(height: 8),
                      TextFormField(
                        controller: nameCtrl,
                        decoration: const InputDecoration(labelText: 'Название'),
                        textInputAction: TextInputAction.next,
                        validator: (v) => (v == null || v.trim().isEmpty) ? 'Введите название' : null,
                      ),
                      const SizedBox(height: 8),
                      TextFormField(
                        controller: orderCtrl,
                        decoration: const InputDecoration(labelText: 'Порядок (целое)'),
                        keyboardType: TextInputType.number,
                        textInputAction: TextInputAction.next,
                        validator: (v) {
                          if (v == null || v.trim().isEmpty) return null;
                          return int.tryParse(v.trim()) == null ? 'Введите число' : null;
                        },
                      ),
                      const SizedBox(height: 8),
                      TextFormField(
                        controller: notesCtrl,
                        decoration: const InputDecoration(labelText: 'Описание'),
                        minLines: 2,
                        maxLines: 5,
                      ),
                      const SizedBox(height: 8),
                      TextFormField(
                        controller: normValueCtrl,
                        decoration: const InputDecoration(labelText: 'Нормировка (значение)'),
                        keyboardType: const TextInputType.numberWithOptions(decimal: true),
                        validator: (v) {
                          if (v == null || v.trim().isEmpty) return null;
                          return double.tryParse(v.trim()) == null ? 'Введите число' : null;
                        },
                      ),
                      const SizedBox(height: 8),
                      DropdownButtonFormField<String>(
                        decoration: const InputDecoration(labelText: 'Ед. нормировки'),
                        value: normUnit,
                        items: const [
                          DropdownMenuItem(value: 'kg', child: Text('kg')),
                          DropdownMenuItem(value: '%', child: Text('%')),
                        ],
                        onChanged: (v) => setModalState(() { normUnit = v; }),
                      ),
                      const SizedBox(height: 12),
                      Row(
                        children: [
                          Expanded(
                            child: OutlinedButton(
                              onPressed: localSubmitting ? null : () => Navigator.of(ctx).pop(),
                              child: const Text('Отмена'),
                            ),
                          ),
                          const SizedBox(width: 12),
                          Expanded(
                            child: ElevatedButton.icon(
                              onPressed: localSubmitting ? null : save,
                              icon: localSubmitting
                                  ? const SizedBox(width: 16, height: 16, child: CircularProgressIndicator(strokeWidth: 2))
                                  : const Icon(Icons.save),
                              label: const Text('Сохранить'),
                            ),
                          ),
                        ],
                      ),
                    ],
                  ),
                ),
              ),
            );
          },
        );
      },
    );
  }

  Widget _buildMicrocycleSchedule(Microcycle micro) {
    if (micro.schedule.isEmpty) return const Text('Пусто');
    final entries = micro.schedule.entries.toList();
    return Column(
      children: entries.map((entry) {
        final day = entry.key;
        final items = entry.value;
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
                else ...items.asMap().entries.map((e) => _buildExerciseCard(e.value)).toList(),
              ],
            ),
          ),
        );
      }).toList(),
    );
  }
  

  Future<void> _loadExerciseNamesForPlan(CalendarPlan plan) async {
    try {
      final ids = <int>{};
      // Legacy top-level schedule
      plan.schedule.forEach((_, items) {
        final list = (items as List?) ?? [];
        for (final it in list) {
          final id = it is Map<String, dynamic> ? it['exercise_id'] : null;
          if (id is int) ids.add(id);
        }
      });
      // Nested mesocycles/microcycles
      for (final meso in plan.mesocycles) {
        for (final micro in meso.microcycles) {
          micro.schedule.forEach((_, items) {
            for (final it in items) {
              ids.add(it.exerciseId);
            }
          });
        }
      }
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

  Future<void> _loadExerciseNamesFromMesocycles(List<Mesocycle> mesocycles) async {
    try {
      final ids = <int>{};
      for (final meso in mesocycles) {
        for (final micro in meso.microcycles) {
          micro.schedule.forEach((_, items) {
            for (final it in items) {
              ids.add(it.exerciseId);
            }
          });
        }
      }
      if (ids.isEmpty) return;
      final svc = ref.read(exerciseServiceProvider);
      final defs = await svc.getExercisesByIds(ids.toList());
      if (!mounted) return;
      setState(() {
        // Merge with existing names
        _exerciseNames.addAll({for (final d in defs) if (d.id != null) d.id!: d.name});
      });
    } catch (e, st) {
      _logger.w('Failed to load exercise names (nested): $e\n$st');
    }
  }

  Future<void> _loadMesocyclesForPlan(int planId) async {
    try {
      final svc = ref.read(mesocycleServiceProvider);
      final mesos = await svc.listMesocycles(planId);
      mesos.sort((a, b) => a.orderIndex.compareTo(b.orderIndex));

      final List<Mesocycle> withMicros = [];
      for (final m in mesos) {
        final micros = await svc.listMicrocycles(m.id);
        micros.sort((a, b) => a.orderIndex.compareTo(b.orderIndex));
        withMicros.add(Mesocycle(
          id: m.id,
          name: m.name,
          notes: m.notes,
          orderIndex: m.orderIndex,
          microcycles: micros,
        ));
      }
      if (!mounted) return;
      setState(() { _mesocycles = withMicros; });
    } catch (e, st) {
      _logger.w('Failed to load meso/micro structure: $e\n$st');
    }
  }

  Future<void> _createInstance() async {
    if (_plan == null) return;
    try {
      final instanceService = ref.read(calendarPlanInstanceServiceProvider);
      final instance = await instanceService.createFromPlan(_plan!.id);
      if (!mounted) return;
      Navigator.of(context).push(
        MaterialPageRoute(
          builder: (_) => CalendarPlanInstanceScreen(instanceId: instance.id),
        ),
      );
    } catch (e, st) {
      _logger.e('Failed to create instance: $e\n$st');
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Не удалось создать копию')),
      );
    }
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
                await svc.applyPlan(planId: widget.planId, request: req);
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
                            return ListTile(
                              contentPadding: EdgeInsets.zero,
                              title: Text(exerciseName),
                              subtitle: Text('RM${um.repMax}: ${um.maxWeight} кг'),
                              trailing: Checkbox(
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
                              ),
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

  Future<void> _openAddMesocycleSheet() async {
    bool localSubmitting = false;

    await showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      builder: (ctx) {
        final nameCtrl = TextEditingController();
        final notesCtrl = TextEditingController();
        final orderCtrl = TextEditingController();
        final formKey = GlobalKey<FormState>();

        return StatefulBuilder(
          builder: (context, setModalState) {
            Future<void> save() async {
              if (localSubmitting) return;
              if (!formKey.currentState!.validate()) return;
              setModalState(() => localSubmitting = true);
              try {
                final newName = nameCtrl.text.trim();
                final newNotes = notesCtrl.text.trim();
                final newOrder = orderCtrl.text.trim().isEmpty ? null : int.tryParse(orderCtrl.text.trim());
                final svc = ref.read(mesocycleServiceProvider);
                await svc.createMesocycle(
                  widget.planId,
                  MesocycleUpdateDto(
                    name: newName.isEmpty ? null : newName,
                    notes: newNotes.isEmpty ? '' : newNotes,
                    orderIndex: newOrder,
                  ),
                );
                if (!mounted) return;
                await _loadMesocyclesForPlan(widget.planId);
                Navigator.of(ctx).pop();
                ScaffoldMessenger.of(context).showSnackBar(
                  const SnackBar(content: Text('Мезоцикл добавлен')),
                );
              } catch (e, st) {
                _logger.e('Failed to add mesocycle: $e\n$st');
                if (!mounted) return;
                ScaffoldMessenger.of(context).showSnackBar(
                  const SnackBar(content: Text('Не удалось добавить мезоцикл')),
                );
              } finally {
                // Avoid setState after pop; do not reset localSubmitting here if sheet closed
              }
            }

            final bottomInset = MediaQuery.of(context).viewInsets.bottom;

            return SafeArea(
              child: Padding(
                padding: EdgeInsets.only(left: 16, right: 16, top: 16, bottom: bottomInset + 16),
                child: Form(
                  key: formKey,
                  child: Column(
                    mainAxisSize: MainAxisSize.min,
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        mainAxisAlignment: MainAxisAlignment.spaceBetween,
                        children: [
                          const Text('Новый мезоцикл', style: TextStyle(fontSize: 18, fontWeight: FontWeight.w600)),
                          IconButton(
                            icon: const Icon(Icons.close),
                            onPressed: () => Navigator.of(ctx).pop(),
                          ),
                        ],
                      ),
                      const SizedBox(height: 8),
                      TextFormField(
                        controller: nameCtrl,
                        decoration: const InputDecoration(labelText: 'Название'),
                        textInputAction: TextInputAction.next,
                        validator: (v) => (v == null || v.trim().isEmpty) ? 'Введите название' : null,
                      ),
                      const SizedBox(height: 8),
                      TextFormField(
                        controller: orderCtrl,
                        decoration: const InputDecoration(labelText: 'Порядок (целое, необязательно)'),
                        keyboardType: TextInputType.number,
                        textInputAction: TextInputAction.next,
                        validator: (v) {
                          if (v == null || v.trim().isEmpty) return null;
                          return int.tryParse(v.trim()) == null ? 'Введите число' : null;
                        },
                      ),
                      const SizedBox(height: 8),
                      TextFormField(
                        controller: notesCtrl,
                        decoration: const InputDecoration(labelText: 'Описание (необязательно)'),
                        minLines: 2,
                        maxLines: 5,
                      ),
                      const SizedBox(height: 12),
                      Row(
                        children: [
                          Expanded(
                            child: OutlinedButton(
                              onPressed: localSubmitting ? null : () => Navigator.of(ctx).pop(),
                              child: const Text('Отмена'),
                            ),
                          ),
                          const SizedBox(width: 12),
                          Expanded(
                            child: ElevatedButton.icon(
                              onPressed: localSubmitting ? null : save,
                              icon: localSubmitting
                                  ? const SizedBox(width: 16, height: 16, child: CircularProgressIndicator(strokeWidth: 2))
                                  : const Icon(Icons.add),
                              label: const Text('Добавить'),
                            ),
                          ),
                        ],
                      ),
                    ],
                  ),
                ),
              ),
            );
          },
        );
      },
    );
  }

  @override
  void initState() {
    super.initState();
    _loadPlan();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        leading: const BackButton(color: Colors.black),
        backgroundColor: Colors.transparent,
        elevation: 0,
        scrolledUnderElevation: 0,
        surfaceTintColor: Colors.transparent,
        iconTheme: const IconThemeData(color: Colors.black),
        foregroundColor: Colors.black,
        actions: [
          PopupMenuButton<String>(
            onSelected: (value) {
              if (value == 'edit') {
                _createInstance();
              } else if (value == 'apply') {
                _openApplyPlanSheet();
              } else if (value == 'add_meso') {
                _openAddMesocycleSheet();
              }
            },
            itemBuilder: (BuildContext context) => <PopupMenuEntry<String>>[
              const PopupMenuItem<String>(
                value: 'edit',
                child: Text('Редактировать копию'),
              ),
              const PopupMenuItem<String>(
                value: 'apply',
                child: Text('Применить план'),
              ),
              const PopupMenuItem<String>(
                value: 'add_meso',
                child: Text('Добавить мезоцикл'),
              ),
            ],
          ),
        ],
      ),
      body: RefreshIndicator(
        onRefresh: _loadPlan,
        child: _isLoading
            ? const Center(child: CircularProgressIndicator())
            : _errorMessage != null
                ? Center(child: Text(_errorMessage!))
                : _plan == null
                    ? const Center(child: Text('План не найден'))
                    : _buildPlanDetails(),
      ),
    );
  }

  Widget _buildPlanDetails() {
    return Column(
      children: [
        const SizedBox(height: 16),
        Text('Активен: ${_plan!.isActive ? 'Да' : 'Нет'}'),
        const SizedBox(height: 16),
        SizedBox(
          width: double.infinity,
          child: ElevatedButton.icon(
            onPressed: _createInstance,
            icon: const Icon(Icons.copy_all),
            label: const Text('Создать редактируемую копию'),
          ),
        ),
        const SizedBox(height: 8),
        SizedBox(
          width: double.infinity,
          child: ElevatedButton.icon(
            onPressed: _openApplyPlanSheet,
            icon: const Icon(Icons.playlist_add_check_circle),
            label: const Text('Применить план'),
          ),
        ),
        // Removed explicit "Редактировать мезоциклы" button; long-press on mesocycle card opens editor
        const SizedBox(height: 16),
        Text('Расписание', style: Theme.of(context).textTheme.titleMedium),
        const SizedBox(height: 8),
        if (_mesocycles.isNotEmpty)
          ..._mesocycles.map((meso) => _buildMesocycleSection(meso)).toList()
        else
          _buildSchedule(_plan!.schedule),
      ],
    );
  }

  Widget _buildSchedule(Map<String, dynamic> schedule) {
    if (schedule.isEmpty) {
      return const Text('Пусто');
    }
    final entries = schedule.entries.toList();
    return ListView.builder(
      shrinkWrap: true,
      physics: const NeverScrollableScrollPhysics(),
      itemCount: entries.length,
      itemBuilder: (context, index) {
        final day = entries[index].key;
        final items = entries[index].value as List<dynamic>? ?? [];
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
                else ...items.asMap().entries.map((e) => _buildExerciseCard(e.value)).toList(),
              ],
            ),
          ),
        );
      },
    );
  }

  Widget _buildExerciseCard(dynamic item) {
    final theme = Theme.of(context);
    // Normalize different item types to common fields
    int? exerciseId;
    List<dynamic> sets = const [];
    if (item is ExerciseScheduleItemDto) {
      exerciseId = item.exerciseId;
      sets = item.sets
          .map((s) => {
                'intensity': s.intensity,
                'effort': s.effort,
                'volume': s.volume,
              })
          .toList();
    } else if (item is Map<String, dynamic>) {
      exerciseId = item['exercise_id'];
      sets = (item['sets'] as List<dynamic>? ?? []);
    }
    final title = (exerciseId is int && _exerciseNames.containsKey(exerciseId))
        ? _exerciseNames[exerciseId]!
        : 'Упражнение #$exerciseId';

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
                Text('${sets.length} сет(ов)', style: theme.textTheme.bodySmall),
              ],
            ),
            const SizedBox(height: 8),
            if (sets.isEmpty) const Text('Нет сетов')
            else ...sets.asMap().entries.map((entry) {
              final setIdx = entry.key + 1;
              final s = entry.value as Map<String, dynamic>;
              final intensity = s['intensity'];
              final effort = s['effort'];
              final volume = s['volume'];
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
                      child: Text('$setIdx', style: theme.textTheme.labelLarge?.copyWith(color: theme.colorScheme.primary)),
                    ),
                    const SizedBox(width: 12),
                    Expanded(
                      child: Wrap(
                        spacing: 8,
                        runSpacing: 8,
                        children: [
                          _chip('Intensity', intensity?.toString() ?? '-'),
                          _chip('Volume', volume?.toString() ?? '-'),
                          _chip('Effort', effort?.toString() ?? '-'),
                        ],
                      ),
                    ),
                  ],
                ),
              );
            }).toList(),
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
