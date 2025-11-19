import 'package:flutter/material.dart';
import 'package:workout_app/models/calendar_plan.dart';
import 'package:workout_app/models/microcycle.dart';
import 'package:workout_app/models/plan_schedule.dart';
import 'package:workout_app/services/api_client.dart';
import 'package:workout_app/services/mesocycle_service.dart';
import 'package:workout_app/models/exercise_definition.dart';
import 'package:workout_app/screens/exercise_selection_screen.dart';
import 'package:workout_app/screens/plan_microcycle_editor.dart';
import 'package:workout_app/widgets/mode_value_control.dart';
import 'package:workout_app/screens/macros/macros_list_screen.dart';
import 'package:workout_app/config/rpe_table.dart' as rpe_table;

class _MicroDiff {
  final int id;
  final String name;
  final int totalSets;
  final int changedSets;
  final int changedIntensity;
  final int changedEffort;
  final int changedVolume;

  const _MicroDiff({
    required this.id,
    required this.name,
    required this.totalSets,
    required this.changedSets,
    required this.changedIntensity,
    required this.changedEffort,
    required this.changedVolume,
  });
}

class _ReplaceConfig {
  final Set<int> sourceExerciseIds;
  final ExerciseDefinition target;
  final int? dayIndex;

  const _ReplaceConfig({required this.sourceExerciseIds, required this.target, required this.dayIndex});
}

enum RecalcTarget { auto, intensity, rpe, reps }
enum FixStrategy { none, fixReps, fixIntensity }

class PlanEditorScreen extends StatefulWidget {
  final CalendarPlan plan;

  const PlanEditorScreen({super.key, required this.plan});

  @override
  State<PlanEditorScreen> createState() => _PlanEditorScreenState();
}

class _PlanEditorScreenState extends State<PlanEditorScreen> {
  final TextEditingController _searchCtrl = TextEditingController();
  String _query = '';
  final Set<int> _selectedMicrocycleIds = {};
  bool _batchSaving = false;
  late final MesocycleService _mesoService;

  @override
  void initState() {
    super.initState();
    _mesoService = MesocycleService(apiClient: ApiClient());
    _searchCtrl.addListener(() {
      setState(() {
        _query = _searchCtrl.text.trim().toLowerCase();
      });
    });
  }

  Future<void> _openMassReplaceDialog() async {
    if (_selectedMicrocycleIds.isEmpty) return;

    // Build lookup for selected microcycles
    final idToMicro = <int, Microcycle>{};
    for (final meso in widget.plan.mesocycles) {
      for (final micro in meso.microcycles) {
        if (_selectedMicrocycleIds.contains(micro.id)) {
          idToMicro[micro.id] = micro;
        }
      }
    }

    // Unique exercises across selection
    final Map<int, String> unique = {};
    final Map<int, int> counts = {};
    for (final micro in idToMicro.values) {
      for (final w in micro.planWorkouts) {
        for (final ex in w.exercises) {
          unique[ex.exerciseDefinitionId] = ex.exerciseName;
          counts[ex.exerciseDefinitionId] = (counts[ex.exerciseDefinitionId] ?? 0) + 1;
        }
      }
    }

    final exerciseIdsSorted = unique.keys.toList()..sort((a, b) => unique[a]!.toLowerCase().compareTo(unique[b]!.toLowerCase()));

    final TextEditingController dayCtrl = TextEditingController();
    Set<int> selectedSources = exerciseIdsSorted.toSet(); // default: all
    ExerciseDefinition? target;
    String? error;

    await showDialog<void>(
      context: context,
      builder: (ctx) => StatefulBuilder(
        builder: (ctx, setState) {
          return AlertDialog(
            title: const Text('Массовая замена упражнений'),
            content: SizedBox(
              width: 440,
              child: Column(
                mainAxisSize: MainAxisSize.min,
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      Expanded(
                        child: TextButton.icon(
                          onPressed: () async {
                            final res = await Navigator.of(context).push(
                              MaterialPageRoute(
                                builder: (_) => const ExerciseSelectionScreen(),
                              ),
                            );
                            if (res is ExerciseDefinition) {
                              setState(() => target = res);
                            }
                          },
                          icon: const Icon(Icons.search),
                          label: Text(target == null ? 'Выбрать целевое упражнение' : 'Цель: ${target!.name}'),
                        ),
                      ),
                      const SizedBox(width: 8),
                      TextButton(
                        onPressed: () {
                          setState(() {
                            if (selectedSources.length == exerciseIdsSorted.length) {
                              selectedSources.clear();
                            } else {
                              selectedSources = exerciseIdsSorted.toSet();
                            }
                          });
                        },
                        child: Text(selectedSources.length == exerciseIdsSorted.length ? 'Снять все' : 'Выбрать все'),
                      ),
                    ],
                  ),
                  const SizedBox(height: 8),
                  SizedBox(
                    height: 260,
                    child: Scrollbar(
                      child: ListView(
                        children: exerciseIdsSorted.map((id) => CheckboxListTile(
                          dense: true,
                          value: selectedSources.contains(id),
                          onChanged: (v) {
                            setState(() {
                              if (v == true) {
                                selectedSources.add(id);
                              } else {
                                selectedSources.remove(id);
                              }
                            });
                          },
                          title: Text(unique[id] ?? 'Exercise $id'),
                          subtitle: Text('Вхождений: ${counts[id] ?? 0}'),
                          controlAffinity: ListTileControlAffinity.leading,
                        )).toList(),
                      ),
                    ),
                  ),
                  const SizedBox(height: 8),
                  TextField(
                    controller: dayCtrl,
                    decoration: const InputDecoration(labelText: 'Фильтр: день (число, опционально)'),
                    keyboardType: TextInputType.number,
                  ),
                  if (error != null) ...[
                    const SizedBox(height: 8),
                    Text(error!, style: TextStyle(color: Theme.of(context).colorScheme.error)),
                  ],
                ],
              ),
            ),
            actions: [
              TextButton(onPressed: () => Navigator.of(ctx).pop(), child: const Text('Отмена')),
              FilledButton(
                onPressed: () async {
                  final dayIndex = int.tryParse(dayCtrl.text);
                  if (target == null) {
                    setState(() => error = 'Выберите целевое упражнение');
                    return;
                  }
                  if (selectedSources.isEmpty) {
                    setState(() => error = 'Выберите хотя бы одно упражнение для замены');
                    return;
                  }
                  Navigator.of(ctx).pop();
                  await _previewAndMaybeApplyReplace(
                    sourceExerciseIds: selectedSources,
                    target: target!,
                    dayIndex: dayIndex,
                  );
                },
                child: const Text('Предпросмотр'),
              ),
            ],
          );
        },
      ),
    );
  }

  Future<void> _previewAndMaybeApplyReplace({
    required Set<int> sourceExerciseIds,
    required ExerciseDefinition target,
    int? dayIndex,
  }) async {
    if (_selectedMicrocycleIds.isEmpty) return;
    List<int> validIds = const [];
    try {
      validIds = await _mesoService.validateMicrocycles(_selectedMicrocycleIds.toList());
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Проверка прав недоступна, продолжаю без неё: $e')),
        );
      }
      validIds = _selectedMicrocycleIds.toList();
    }

    if (validIds.isEmpty) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Нет доступных микроциклов для замены')),
        );
      }
      return;
    }

    final idToMicro = <int, Microcycle>{};
    for (final meso in widget.plan.mesocycles) {
      for (final micro in meso.microcycles) {
        idToMicro[micro.id] = micro;
      }
    }

    final diffs = <Map<String, dynamic>>[]; // {name, ex, sets}
    int totalEx = 0, totalSets = 0;
    for (final id in validIds) {
      final micro = idToMicro[id];
      if (micro == null) continue;
      final d = _simulateReplaceDiff(micro, sourceExerciseIds: sourceExerciseIds, dayIndex: dayIndex);
      if ((d['ex'] ?? 0) > 0) {
        diffs.add({'name': micro.name, 'ex': d['ex'], 'sets': d['sets']});
        totalEx += d['ex'] as int;
        totalSets += d['sets'] as int;
      }
    }

    if (totalEx == 0) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Нет упражнений для замены')));
      }
      return;
    }

    final confirmed = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Предпросмотр замены упражнений'),
        content: SizedBox(
          width: 440,
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text('Цель: ${target.name}'),
              Text('Будет заменено упражнений: $totalEx, сетов затронуто: $totalSets'),
              const SizedBox(height: 8),
              Flexible(
                child: SingleChildScrollView(
                  child: Column(
                    children: diffs.map((e) => ListTile(
                      dense: true,
                      title: Text(e['name'] as String),
                      subtitle: Text('Упражнений: ${e['ex']} · Сетов: ${e['sets']}'),
                    )).toList(),
                  ),
                ),
              ),
            ],
          ),
        ),
        actions: [
          TextButton(onPressed: () => Navigator.of(ctx).pop(false), child: const Text('Отмена')),
          FilledButton(onPressed: () => Navigator.of(ctx).pop(true), child: const Text('Применить')),
        ],
      ),
    );

    if (confirmed == true) {
      await _applyMassReplace(sourceExerciseIds: sourceExerciseIds, target: target, dayIndex: dayIndex);
    }
  }

  Map<String, int> _simulateReplaceDiff(
    Microcycle micro, {
    required Set<int> sourceExerciseIds,
    int? dayIndex,
  }) {
    int exCount = 0, setCount = 0;
    for (final w in micro.planWorkouts) {
      if (dayIndex != null) {
        final label = w.dayLabel.trim().toLowerCase();
        int? d;
        if (label.startsWith('day ')) {
          d = int.tryParse(label.substring(4).trim());
        }
        d ??= (w.orderIndex + 1);
        if (d != dayIndex) continue;
      }
      for (final ex in w.exercises) {
        if (sourceExerciseIds.contains(ex.exerciseDefinitionId)) {
          exCount += 1;
          setCount += ex.sets.length;
        }
      }
    }
    return {'ex': exCount, 'sets': setCount};
  }

  Future<void> _applyMassReplace({
    required Set<int> sourceExerciseIds,
    required ExerciseDefinition target,
    int? dayIndex,
  }) async {
    if (_selectedMicrocycleIds.isEmpty) return;
    setState(() => _batchSaving = true);
    try {
      final validIds = await _mesoService.validateMicrocycles(_selectedMicrocycleIds.toList());

      final idToMicro = <int, Microcycle>{};
      for (final meso in widget.plan.mesocycles) {
        for (final micro in meso.microcycles) {
          idToMicro[micro.id] = micro;
        }
      }

      int success = 0, failed = 0;
      for (final id in validIds) {
        final micro = idToMicro[id];
        if (micro == null) { failed++; continue; }

        bool changed = false;
        for (int wi = 0; wi < micro.planWorkouts.length; wi++) {
          final w = micro.planWorkouts[wi];
          if (dayIndex != null) {
            final label = w.dayLabel.trim().toLowerCase();
            int? d;
            if (label.startsWith('day ')) {
              d = int.tryParse(label.substring(4).trim());
            }
            d ??= (w.orderIndex + 1);
            if (d != dayIndex) {
              continue;
            }
          }
          final newExercises = <PlanExercise>[];
          for (final ex in w.exercises) {
            if (sourceExerciseIds.contains(ex.exerciseDefinitionId)) {
              newExercises.add(PlanExercise(
                id: ex.id,
                exerciseDefinitionId: target.id ?? ex.exerciseDefinitionId,
                exerciseName: target.name,
                orderIndex: ex.orderIndex,
                planWorkoutId: ex.planWorkoutId,
                sets: ex.sets,
              ));
              changed = true;
            } else {
              newExercises.add(ex);
            }
          }
          micro.planWorkouts[wi] = PlanWorkout(
            id: w.id,
            microcycleId: w.microcycleId,
            dayLabel: w.dayLabel,
            orderIndex: w.orderIndex,
            exercises: newExercises,
          );
        }

        if (!changed) continue;

        final schedule = _toSchedule(micro);
        try {
          await _mesoService.updateMicrocycle(id, MicrocycleUpdateDto(
            name: micro.name,
            daysCount: micro.daysCount,
            schedule: schedule,
          ));
          success++;
        } catch (_) {
          failed++;
        }
      }

      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Замена: успешно $success, ошибок $failed')),
      );
    } finally {
      if (mounted) setState(() => _batchSaving = false);
    }
  }

  int? _nearestRepsForIntensity(int intensity, int desired) {
    int? best;
    int bestDelta = 1 << 30;
    for (int rpe = 10; rpe >= 4; rpe--) {
      final reps = rpe_table.RpeTable.getReps(intensity, rpe);
      if (reps == null) continue;
      final d = (reps - desired).abs();
      if (d < bestDelta) { bestDelta = d; best = reps; }
    }
    return best;
  }

  Map<String, int> _simulateDiff(
    Microcycle micro, {
    String? intensityMode,
    double? intensityValue,
    String? effortMode,
    double? effortValue,
    String? volumeMode,
    double? volumeValue,
    Set<int>? exerciseIds,
    int? dayIndex,
    String? recalcTarget,
    String? fixStrategy,
  }) {
    int total = 0, changed = 0, ci = 0, ce = 0, cv = 0, invalid = 0;
    int? _applyInt(int? orig, String? mode, double? val) {
      if (mode == null || val == null) return orig;
      if (mode == 'set') return val.round();
      if (mode == 'offset') {
        if (orig == null) return orig;
        return (orig + val).round();
      }
      if (mode == 'scale') {
        if (orig == null) return orig;
        return (orig * val).round();
      }
      return orig;
    }
    int? _clampIntensity(int? v) => v == null ? null : v.clamp(0, 100);
    int? _clampEffort(int? v) => v == null ? null : v.clamp(4, 10);
    int? _clampVolume(int? v) => v == null ? null : (v < 1 ? 1 : v);
    for (final w in micro.planWorkouts) {
      if (dayIndex != null) {
        final label = w.dayLabel.trim().toLowerCase();
        int? d;
        if (label.startsWith('day ')) {
          d = int.tryParse(label.substring(4).trim());
        }
        d ??= (w.orderIndex + 1);
        if (d != dayIndex) continue;
      }
      for (final ex in w.exercises) {
        if (exerciseIds != null) {
          if (exerciseIds.isEmpty || !exerciseIds.contains(ex.exerciseDefinitionId)) {
            continue;
          }
        }
        for (final s in ex.sets) {
          total += 1;
          int? ni = _clampIntensity(_applyInt(s.intensity, intensityMode, intensityValue));
          int? ne = _clampEffort(_applyInt(s.effort, effortMode, effortValue));
          int? nv = _clampVolume(_applyInt(s.volume, volumeMode, volumeValue));

          String? target = recalcTarget;
          if (target == null || target == 'auto') {
            final bool chI = ni != s.intensity;
            final bool chE = ne != s.effort;
            final bool chV = nv != s.volume;
            if ((chI || chE) && !chV) {
              target = 'reps';
            } else if (chV && !(chI || chE)) {
              target = 'intensity';
            } else if (chI && chV && !chE) {
              target = 'rpe';
            } else {
              target = null;
            }
          }

          if (target == 'reps') {
            if (ni != null && ne != null) {
              final r = rpe_table.RpeTable.getReps(ni, ne);
              if (r != null) {
                nv = _clampVolume(r);
              } else {
                invalid += 1;
              }
            }
          } else if (target == 'rpe') {
            if (ni != null && nv != null) {
              final rpe = rpe_table.RpeTable.getRpe(ni, nv);
              if (rpe != null) {
                ne = _clampEffort(rpe);
              } else {
                // invalid combo; apply fix if requested
                invalid += 1;
                final strategy = fixStrategy ?? 'none';
                if (strategy == 'fixReps') {
                  final fixed = _nearestRepsForIntensity(ni, nv);
                  if (fixed != null) {
                    nv = _clampVolume(fixed);
                    final rpe2 = rpe_table.RpeTable.getRpe(ni, nv!);
                    if (rpe2 != null) ne = _clampEffort(rpe2);
                  }
                } else if (strategy == 'fixIntensity') {
                  final ii = rpe_table.RpeTable.getIntensity(nv, 10);
                  if (ii != null) {
                    ni = _clampIntensity(ii);
                    final rpe2 = rpe_table.RpeTable.getRpe(ni!, nv);
                    if (rpe2 != null) ne = _clampEffort(rpe2);
                  }
                }
              }
            }
          } else if (target == 'intensity') {
            if (nv != null && ne != null) {
              final ii = rpe_table.RpeTable.getIntensity(nv, ne);
              if (ii != null) {
                ni = _clampIntensity(ii);
              } else {
                invalid += 1;
              }
            }
          }

          bool any = false;
          if (ni != s.intensity) { ci += 1; any = true; }
          if (ne != s.effort) { ce += 1; any = true; }
          if (nv != s.volume) { cv += 1; any = true; }
          if (any) changed += 1;
        }
      }
    }
    return {'total': total, 'changed': changed, 'i': ci, 'e': ce, 'v': cv, 'invalid': invalid};
  }

  @override
  void dispose() {
    _searchCtrl.dispose();
    super.dispose();
  }

  bool _microHasMatch(Microcycle micro) {
    if (_query.isEmpty) return true;
    for (final w in micro.planWorkouts) {
      for (final ex in w.exercises) {
        if (ex.exerciseName.toLowerCase().contains(_query)) return true;
      }
    }
    return false;
  }

  @override
  Widget build(BuildContext context) {
    final plan = widget.plan;
    return Scaffold(
      appBar: AppBar(
        title: Text('Редактор: ${plan.name}'),
        actions: [
          TextButton.icon(
            onPressed: () {
              final id = plan.id;
              if (id != null) {
                Navigator.of(context).push(
                  MaterialPageRoute(
                    builder: (_) => MacrosListScreen(calendarPlanId: id),
                  ),
                );
              } else {
                ScaffoldMessenger.of(context).showSnackBar(
                  const SnackBar(content: Text('Нет ID плана')),
                );
              }
            },
            icon: const Icon(Icons.auto_fix_high, color: Colors.white),
            label: const Text('Macros', style: TextStyle(color: Colors.white)),
          ),
          if (_selectedMicrocycleIds.isNotEmpty)
            TextButton.icon(
              onPressed: _batchSaving ? null : _openMassEditDialog,
              icon: _batchSaving
                  ? const SizedBox(width: 16, height: 16, child: CircularProgressIndicator(strokeWidth: 2))
                  : const Icon(Icons.tune, color: Colors.white),
              label: Text('Массово (${_selectedMicrocycleIds.length})', style: const TextStyle(color: Colors.white)),
            ),
          if (_selectedMicrocycleIds.isNotEmpty)
            TextButton.icon(
              onPressed: _batchSaving ? null : _openMassReplaceDialog,
              icon: const Icon(Icons.swap_horiz, color: Colors.white),
              label: const Text('Замена', style: TextStyle(color: Colors.white)),
            ),
        ],
      ),
      body: Padding(
        padding: const EdgeInsets.all(12.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            TextField(
              controller: _searchCtrl,
              decoration: const InputDecoration(
                prefixIcon: Icon(Icons.search),
                hintText: 'Поиск упражнения по названию...',
                border: OutlineInputBorder(),
              ),
            ),
            const SizedBox(height: 8),
            Text(
              'Мезоциклы',
              style: Theme.of(context).textTheme.titleMedium,
            ),
            const SizedBox(height: 8),
            Expanded(
              child: ListView.builder(
                itemCount: plan.mesocycles.length,
                itemBuilder: (context, index) {
                  final meso = plan.mesocycles[index];
                  final filtered = meso.microcycles.where(_microHasMatch).toList();
                  if (filtered.isEmpty) return const SizedBox.shrink();
                  return ExpansionTile(
                    title: Row(
                      children: [
                        Expanded(child: Text(meso.name)),
                        IconButton(
                          icon: const Icon(Icons.delete_outline, color: Colors.red),
                          onPressed: () async {
                            final confirmed = await showDialog<bool>(
                              context: context,
                              builder: (ctx) => AlertDialog(
                                title: const Text('Удалить мезоцикл'),
                                content: Text('Вы уверены, что хотите удалить мезоцикл "${meso.name}" и все его микроциклы?'),
                                actions: [
                                  TextButton(onPressed: () => Navigator.of(ctx).pop(false), child: const Text('Отмена')),
                                  FilledButton(
                                    onPressed: () => Navigator.of(ctx).pop(true),
                                    style: FilledButton.styleFrom(backgroundColor: Colors.red),
                                    child: const Text('Удалить'),
                                  ),
                                ],
                              ),
                            );
                            if (confirmed == true) {
                              try {
                                await _mesoService.deleteMesocycle(meso.id!);
                                if (mounted) {
                                  setState(() {
                                    widget.plan.mesocycles.removeWhere((m) => m.id == meso.id);
                                  });
                                  ScaffoldMessenger.of(context).showSnackBar(
                                    const SnackBar(content: Text('Мезоцикл удалён')),
                                  );
                                }
                              } catch (e) {
                                if (mounted) {
                                  ScaffoldMessenger.of(context).showSnackBar(
                                    SnackBar(content: Text('Ошибка удаления: $e')),
                                  );
                                }
                              }
                            }
                          },
                          tooltip: 'Удалить мезоцикл',
                        ),
                      ],
                    ),
                    children: [
                      ...filtered.map((micro) => CheckboxListTile(
                            controlAffinity: ListTileControlAffinity.leading,
                            value: _selectedMicrocycleIds.contains(micro.id),
                            onChanged: (checked) {
                              setState(() {
                                if (checked == true) {
                                  _selectedMicrocycleIds.add(micro.id);
                                } else {
                                  _selectedMicrocycleIds.remove(micro.id);
                                }
                              });
                            },
                            title: Text(micro.name),
                            subtitle: Text('Дней: ${micro.daysCount ?? 0}'),
                            secondary: Row(
                              mainAxisSize: MainAxisSize.min,
                              children: [
                                IconButton(
                                  icon: const Icon(Icons.chevron_right),
                                  onPressed: () async {
                                    final changed = await Navigator.of(context).push(
                                      MaterialPageRoute(
                                        builder: (_) => PlanMicrocycleEditor(microcycle: micro),
                                      ),
                                    );
                                    if (!context.mounted) return;
                                    if (changed == true) {
                                      ScaffoldMessenger.of(context).showSnackBar(
                                        const SnackBar(content: Text('Изменения сохранены')),
                                      );
                                    } else if (changed is Map<String, dynamic> && changed['deletedId'] != null) {
                                      final int did = (changed['deletedId'] as num).toInt();
                                      setState(() {
                                        meso.microcycles.removeWhere((mc) => mc.id == did);
                                        _selectedMicrocycleIds.remove(did);
                                      });
                                      ScaffoldMessenger.of(context).showSnackBar(
                                        const SnackBar(content: Text('Микроцикл удалён')),
                                      );
                                    }
                                  },
                                ),
                                IconButton(
                                  icon: const Icon(Icons.delete_outline, color: Colors.red),
                                  onPressed: () async {
                                    final confirmed = await showDialog<bool>(
                                      context: context,
                                      builder: (ctx) => AlertDialog(
                                        title: const Text('Удалить микроцикл'),
                                        content: Text('Вы уверены, что хотите удалить микроцикл "${micro.name}"?'),
                                        actions: [
                                          TextButton(onPressed: () => Navigator.of(ctx).pop(false), child: const Text('Отмена')),
                                          FilledButton(
                                            onPressed: () => Navigator.of(ctx).pop(true),
                                            style: FilledButton.styleFrom(backgroundColor: Colors.red),
                                            child: const Text('Удалить'),
                                          ),
                                        ],
                                      ),
                                    );
                                    if (confirmed == true) {
                                      try {
                                        await _mesoService.deleteMicrocycle(micro.id!);
                                        if (mounted) {
                                          setState(() {
                                            meso.microcycles.removeWhere((mc) => mc.id == micro.id);
                                            _selectedMicrocycleIds.remove(micro.id);
                                          });
                                          ScaffoldMessenger.of(context).showSnackBar(
                                            const SnackBar(content: Text('Микроцикл удалён')),
                                          );
                                        }
                                      } catch (e) {
                                        if (mounted) {
                                          ScaffoldMessenger.of(context).showSnackBar(
                                            SnackBar(content: Text('Ошибка удаления: $e')),
                                          );
                                        }
                                      }
                                    }
                                  },
                                  tooltip: 'Удалить микроцикл',
                                ),
                              ],
                            ),
                          )),
                    ],
                  );
                },
              ),
            ),
          ],
        ),
      ),
    );
  }

  Future<void> _openMassEditDialog() async {
    // New mode/value state per parameter
    bool intensityEnabled = false;
    bool effortEnabled = false;
    bool volumeEnabled = false;
    ModeValue intensityMV = ModeValue(mode: ParamMode.set, value: 60.0);
    ModeValue effortMV = ModeValue(mode: ParamMode.set, value: 8.0);
    ModeValue volumeMV = ModeValue(mode: ParamMode.set, value: 8.0);
    RecalcTarget recalcTarget = RecalcTarget.auto;
    final dayCtrl = TextEditingController();

    // Build unique exercises across the entire plan for multi-select filter
    final Map<int, String> unique = {};
    final Map<int, int> counts = {};
    for (final meso in widget.plan.mesocycles) {
      for (final micro in meso.microcycles) {
        for (final w in micro.planWorkouts) {
          for (final ex in w.exercises) {
            unique[ex.exerciseDefinitionId] = ex.exerciseName;
            counts[ex.exerciseDefinitionId] = (counts[ex.exerciseDefinitionId] ?? 0) + 1;
          }
        }
      }
    }
    final exerciseIdsSorted = unique.keys.toList()
      ..sort((a, b) => (unique[a] ?? '').toLowerCase().compareTo((unique[b] ?? '').toLowerCase()));
    Set<int> selectedExerciseIds = exerciseIdsSorted.toSet(); // default: all

    final confirmed = await showDialog<bool>(
      context: context,
      builder: (ctx) => StatefulBuilder(
        builder: (ctx, setState) {
          return AlertDialog(
            title: const Text('Массовые правки: выбранные микроциклы'),
            content: SingleChildScrollView(
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  ModeValueControl(
                    label: 'Интенсивность',
                    enabled: intensityEnabled,
                    onEnabledChanged: (v) => setState(() { intensityEnabled = v; }),
                    value: intensityMV,
                    onChanged: (mv) => setState(() { intensityMV = mv; }),
                    allowedModes: const [ParamMode.set, ParamMode.offset, ParamMode.scale],
                    modeTitles: const {
                      ParamMode.set: 'Задать',
                      ParamMode.offset: 'Сдвиг',
                      ParamMode.scale: 'Множитель',
                    },
                    displayTextBuilder: (m, v) {
                      if (m == ParamMode.scale) return v.toStringAsFixed(2);
                      return '${v.toStringAsFixed((v % 1 == 0) ? 0 : 1)}%';
                    },
                    stepForMode: (m) {
                      switch (m) {
                        case ParamMode.set: return 1.0;
                        case ParamMode.offset: return 2.5;
                        case ParamMode.scale: return 0.01;
                      }
                    },
                    setMin: 0,
                    setMax: 100,
                    scaleMin: 0.01,
                  ),
                  const SizedBox(height: 8),
                  ModeValueControl(
                    label: 'RPE',
                    enabled: effortEnabled,
                    onEnabledChanged: (v) => setState(() { effortEnabled = v; }),
                    value: effortMV,
                    onChanged: (mv) => setState(() { effortMV = mv; }),
                    allowedModes: const [ParamMode.set, ParamMode.offset],
                    modeTitles: const {
                      ParamMode.set: 'Задать',
                      ParamMode.offset: 'Сдвиг',
                    },
                    displayTextBuilder: (m, v) => v.toStringAsFixed(0),
                    stepForMode: (m) => 1.0,
                    setMin: 4,
                    setMax: 10,
                  ),
                  const SizedBox(height: 8),
                  ModeValueControl(
                    label: 'Повторы',
                    enabled: volumeEnabled,
                    onEnabledChanged: (v) => setState(() { volumeEnabled = v; }),
                    value: volumeMV,
                    onChanged: (mv) => setState(() { volumeMV = mv; }),
                    allowedModes: const [ParamMode.set, ParamMode.offset, ParamMode.scale],
                    modeTitles: const {
                      ParamMode.set: 'Задать',
                      ParamMode.offset: 'Сдвиг',
                      ParamMode.scale: 'Множитель',
                    },
                    displayTextBuilder: (m, v) => m == ParamMode.scale ? v.toStringAsFixed(2) : v.toStringAsFixed(0),
                    stepForMode: (m) {
                      switch (m) {
                        case ParamMode.set: return 1.0;
                        case ParamMode.offset: return 1.0;
                        case ParamMode.scale: return 0.05;
                      }
                    },
                    setMin: 1,
                    setMax: null,
                    scaleMin: 0.01,
                  ),
                  const SizedBox(height: 8),
                  DropdownButtonFormField<RecalcTarget>(
                    value: recalcTarget,
                    items: const [
                      DropdownMenuItem(value: RecalcTarget.auto, child: Text('Пересчитать: Авто')),
                      DropdownMenuItem(value: RecalcTarget.reps, child: Text('Пересчитать: Повторы')),
                      DropdownMenuItem(value: RecalcTarget.rpe, child: Text('Пересчитать: RPE')),
                      DropdownMenuItem(value: RecalcTarget.intensity, child: Text('Пересчитать: Интенсивность')),
                    ],
                    onChanged: (v) => setState(() { recalcTarget = v ?? RecalcTarget.auto; }),
                  ),
                  if (recalcTarget == RecalcTarget.auto) ...[
                    const SizedBox(height: 6),
                    Builder(
                      builder: (innerCtx) {
                        final chI = intensityEnabled;
                        final chE = effortEnabled;
                        final chV = volumeEnabled;
                        String t;
                        if ((chI || chE) && !chV) {
                          t = 'Авто-пересчет: Повторы (по Интенсивности и RPE)';
                        } else if (chV && !(chI || chE)) {
                          t = 'Авто-пересчет: Интенсивность (по Повторам и RPE)';
                        } else if (chI && chV && !chE) {
                          t = 'Авто-пересчет: RPE (по Интенсивности и Повторам)';
                        } else {
                          t = 'Авто-пересчет: не применяется';
                        }
                        return Row(
                          children: [
                            Icon(Icons.info_outline, size: 16, color: Theme.of(innerCtx).hintColor),
                            const SizedBox(width: 6),
                            Expanded(child: Text(t)),
                          ],
                        );
                      },
                    ),
                  ],
                  const SizedBox(height: 8),
                  Row(
                    children: [
                      const Expanded(child: Text('Фильтр: упражнения (опционально)')),
                      TextButton(
                        onPressed: () {
                          setState(() {
                            if (selectedExerciseIds.length == exerciseIdsSorted.length) {
                              selectedExerciseIds.clear();
                            } else {
                              selectedExerciseIds = exerciseIdsSorted.toSet();
                            }
                          });
                        },
                        child: Text(selectedExerciseIds.length == exerciseIdsSorted.length ? 'Снять все' : 'Выбрать все'),
                      ),
                    ],
                  ),
                  SizedBox(
                    height: 220,
                    child: Scrollbar(
                      child: SingleChildScrollView(
                        primary: false,
                        child: Column(
                          children: exerciseIdsSorted.map((id) => CheckboxListTile(
                            dense: true,
                            value: selectedExerciseIds.contains(id),
                            onChanged: (v) {
                              setState(() {
                                if (v == true) {
                                  selectedExerciseIds.add(id);
                                } else {
                                  selectedExerciseIds.remove(id);
                                }
                              });
                            },
                            title: Text(unique[id] ?? 'Exercise $id'),
                            subtitle: Text('Вхождений: ${counts[id] ?? 0}'),
                            controlAffinity: ListTileControlAffinity.leading,
                          )).toList(),
                        ),
                      ),
                    ),
                  ),
                  const SizedBox(height: 8),
                  TextField(
                    controller: dayCtrl,
                    decoration: const InputDecoration(labelText: 'Фильтр: день (число, опционально)'),
                    keyboardType: TextInputType.number,
                  ),
                  const SizedBox(height: 8),
                  const Text('Будут изменены ВСЕ подходы всех упражнений во всех выбранных микроциклах.'),
                ],
              ),
            ),
            actions: [
              TextButton(onPressed: () => Navigator.of(ctx).pop(false), child: const Text('Отмена')),
              FilledButton(onPressed: () => Navigator.of(ctx).pop(true), child: const Text('Применить')),
            ],
          );
        },
      ),
    );

    if (confirmed != true) return;
    final dayIndex = int.tryParse(dayCtrl.text);
    String? mapMode(ParamMode m) {
      switch (m) {
        case ParamMode.set: return 'set';
        case ParamMode.offset: return 'offset';
        case ParamMode.scale: return 'scale';
      }
    }
    final String recalcTargetStr = () {
      switch (recalcTarget) {
        case RecalcTarget.auto: return 'auto';
        case RecalcTarget.intensity: return 'intensity';
        case RecalcTarget.rpe: return 'rpe';
        case RecalcTarget.reps: return 'reps';
      }
    }();
    await _previewAndMaybeApply(
      intensityMode: intensityEnabled ? mapMode(intensityMV.mode) : null,
      intensityValue: intensityEnabled ? intensityMV.value : null,
      effortMode: effortEnabled ? mapMode(effortMV.mode) : null,
      effortValue: effortEnabled ? effortMV.value : null,
      volumeMode: volumeEnabled ? mapMode(volumeMV.mode) : null,
      volumeValue: volumeEnabled ? volumeMV.value : null,
      exerciseIds: selectedExerciseIds,
      dayIndex: dayIndex,
      recalcTarget: recalcTargetStr,
    );
  }

  Future<void> _previewAndMaybeApply({
    String? intensityMode,
    double? intensityValue,
    String? effortMode,
    double? effortValue,
    String? volumeMode,
    double? volumeValue,
    Set<int>? exerciseIds,
    int? dayIndex,
    String? recalcTarget,
    String? fixStrategy,
  }) async {
    if (_selectedMicrocycleIds.isEmpty) return;
    // Validate ownership first
    final validIds = await _mesoService.validateMicrocycles(_selectedMicrocycleIds.toList());

    // Build lookup
    final idToMicro = <int, Microcycle>{};
    for (final meso in widget.plan.mesocycles) {
      for (final micro in meso.microcycles) {
        idToMicro[micro.id] = micro;
      }
    }

    // Compute diffs (with ability to recompute inside dialog)
    var diffs = <_MicroDiff>[];
    int sumTotal = 0, sumChanged = 0, sumI = 0, sumE = 0, sumV = 0, sumInvalid = 0;
    void recompute() {
      diffs = <_MicroDiff>[];
      sumTotal = 0; sumChanged = 0; sumI = 0; sumE = 0; sumV = 0; sumInvalid = 0;
      for (final id in validIds) {
        final micro = idToMicro[id];
        if (micro == null) continue;
        final d = _simulateDiff(
          micro,
          intensityMode: intensityMode,
          intensityValue: intensityValue,
          effortMode: effortMode,
          effortValue: effortValue,
          volumeMode: volumeMode,
          volumeValue: volumeValue,
          exerciseIds: exerciseIds,
          dayIndex: dayIndex,
          recalcTarget: recalcTarget,
          fixStrategy: fixStrategy,
        );
        diffs.add(_MicroDiff(
          id: id,
          name: micro.name,
          totalSets: d['total'] ?? 0,
          changedSets: d['changed'] ?? 0,
          changedIntensity: d['i'] ?? 0,
          changedEffort: d['e'] ?? 0,
          changedVolume: d['v'] ?? 0,
        ));
        sumTotal += d['total'] ?? 0;
        sumChanged += d['changed'] ?? 0;
        sumI += d['i'] ?? 0;
        sumE += d['e'] ?? 0;
        sumV += d['v'] ?? 0;
        sumInvalid += d['invalid'] ?? 0;
      }
    }
    recompute();

    if (sumChanged == 0) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Нет изменений по выбранным параметрам')));
      }
      return;
    }

    FixStrategy localFix = () {
      switch (fixStrategy) {
        case 'fixReps': return FixStrategy.fixReps;
        case 'fixIntensity': return FixStrategy.fixIntensity;
        default: return FixStrategy.none;
      }
    }();
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (ctx) => StatefulBuilder(
        builder: (ctx, setState) {
          return AlertDialog(
            title: const Text('Предпросмотр массовых правок'),
            content: SizedBox(
              width: 460,
              child: Column(
                mainAxisSize: MainAxisSize.min,
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      Expanded(child: Text('Микроциклов: ${diffs.length}')),
                      const SizedBox(width: 8),
                      Expanded(child: Text('Несоответствий: $sumInvalid')),
                    ],
                  ),
                  Text('Изменённых сетов: $sumChanged из $sumTotal'),
                  Text('Изменения: Int $sumI · RPE $sumE · Повт $sumV'),
                  const SizedBox(height: 8),
                  DropdownButtonFormField<FixStrategy>(
                    value: localFix,
                    items: const [
                      DropdownMenuItem(value: FixStrategy.none, child: Text('Валидатор: Без авто-исправлений')),
                      DropdownMenuItem(value: FixStrategy.fixReps, child: Text('Валидатор: Поправить Повторы')),
                      DropdownMenuItem(value: FixStrategy.fixIntensity, child: Text('Валидатор: Поправить Интенсивность')),
                    ],
                    onChanged: (v) {
                      localFix = v ?? FixStrategy.none;
                      fixStrategy = () {
                        switch (localFix) {
                          case FixStrategy.fixReps: return 'fixReps';
                          case FixStrategy.fixIntensity: return 'fixIntensity';
                          case FixStrategy.none: default: return 'none';
                        }
                      }();
                      setState(() { recompute(); });
                    },
                  ),
                  const SizedBox(height: 6),
                  Flexible(
                    child: SingleChildScrollView(
                      child: Column(
                        children: diffs.map((d) => ListTile(
                          dense: true,
                          title: Text(d.name),
                          subtitle: Text('Сеты: ${d.changedSets}/${d.totalSets} · Δ Int ${d.changedIntensity} · Δ RPE ${d.changedEffort} · Δ Повт ${d.changedVolume}'),
                        )).toList(),
                      ),
                    ),
                  ),
                ],
              ),
            ),
            actions: [
              TextButton(onPressed: () => Navigator.of(ctx).pop(false), child: const Text('Отмена')),
              FilledButton(onPressed: () => Navigator.of(ctx).pop(true), child: const Text('Применить')),
            ],
          );
        },
      ),
    );

    if (confirmed == true) {
      await _applyMassEdits(
        intensityMode: intensityMode,
        intensityValue: intensityValue,
        effortMode: effortMode,
        effortValue: effortValue,
        volumeMode: volumeMode,
        volumeValue: volumeValue,
        exerciseIds: exerciseIds,
        dayIndex: dayIndex,
        recalcTarget: recalcTarget,
        fixStrategy: fixStrategy,
      );
    }
  }

  Future<void> _applyMassEdits({
    String? intensityMode,
    double? intensityValue,
    String? effortMode,
    double? effortValue,
    String? volumeMode,
    double? volumeValue,
    Set<int>? exerciseIds,
    int? dayIndex,
    String? recalcTarget,
    String? fixStrategy,
  }) async {
    if (_selectedMicrocycleIds.isEmpty) return;
    setState(() => _batchSaving = true);
    try {
      List<int> validIds;
      try {
        validIds = await _mesoService.validateMicrocycles(_selectedMicrocycleIds.toList());
        final invalidCount = _selectedMicrocycleIds.length - validIds.length;
        if (invalidCount > 0) {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(content: Text('Пропущено $invalidCount микроциклов без прав доступа')),
          );
        }
      } catch (e) {
        validIds = _selectedMicrocycleIds.toList();
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Проверка прав недоступна, применяю ко всем выбранным: $e')),
        );
      }

      // Build a map id -> microcycle reference
      final idToMicro = <int, Microcycle>{};
      for (final meso in widget.plan.mesocycles) {
        for (final micro in meso.microcycles) {
          idToMicro[micro.id] = micro;
        }
      }

      int success = 0;
      int failed = 0;
      for (final id in validIds) {
        final micro = idToMicro[id];
        if (micro == null) { failed++; continue; }

        // Apply changes in-memory copy
        final changed = _applySetParamsToMicro(
          micro,
          intensityMode: intensityMode,
          intensityValue: intensityValue,
          effortMode: effortMode,
          effortValue: effortValue,
          volumeMode: volumeMode,
          volumeValue: volumeValue,
          exerciseIds: exerciseIds,
          dayIndex: dayIndex,
          recalcTarget: recalcTarget,
          fixStrategy: fixStrategy,
        );
        if (!changed) { continue; }

        final schedule = _toSchedule(micro);
        try {
          await _mesoService.updateMicrocycle(id, MicrocycleUpdateDto(
            name: micro.name,
            daysCount: micro.daysCount,
            schedule: schedule,
          ));
          success++;
        } catch (_) {
          failed++;
        }
      }

      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Массовые правки: успешно $success, ошибок $failed')),
      );
    } finally {
      if (mounted) setState(() => _batchSaving = false);
    }
  }

  bool _applySetParamsToMicro(
    Microcycle micro, {
    String? intensityMode,
    double? intensityValue,
    String? effortMode,
    double? effortValue,
    String? volumeMode,
    double? volumeValue,
    Set<int>? exerciseIds,
    int? dayIndex,
    String? recalcTarget,
    String? fixStrategy,
  }) {
    bool changed = false;
    int? _applyInt(int? orig, String? mode, double? val) {
      if (mode == null || val == null) return orig;
      if (mode == 'set') return val.round();
      if (mode == 'offset') {
        if (orig == null) return orig; // skip if no original
        return (orig + val).round();
      }
      if (mode == 'scale') {
        if (orig == null) return orig;
        return (orig * val).round();
      }
      return orig;
    }
    int? _clampIntensity(int? v) => v == null ? null : v.clamp(0, 100);
    int? _clampEffort(int? v) => v == null ? null : v.clamp(4, 10);
    int? _clampVolume(int? v) => v == null ? null : (v < 1 ? 1 : v);
    for (int wi = 0; wi < micro.planWorkouts.length; wi++) {
      final w = micro.planWorkouts[wi];
      // Optional filter by day index (Day N)
      if (dayIndex != null) {
        final label = w.dayLabel.trim().toLowerCase();
        int? d;
        if (label.startsWith('day ')) {
          d = int.tryParse(label.substring(4).trim());
        }
        d ??= (w.orderIndex + 1);
        if (d != dayIndex) {
          continue;
        }
      }
      final newExercises = <PlanExercise>[];
      for (final ex in w.exercises) {
        if (exerciseIds != null) {
          if (exerciseIds.isEmpty || !exerciseIds.contains(ex.exerciseDefinitionId)) {
            newExercises.add(ex);
            continue;
          }
        }
        final newSets = <PlanSet>[];
        for (final s in ex.sets) {
          int? ni = _clampIntensity(_applyInt(s.intensity, intensityMode, intensityValue));
          int? ne = _clampEffort(_applyInt(s.effort, effortMode, effortValue));
          int? nv = _clampVolume(_applyInt(s.volume, volumeMode, volumeValue));

          String? target = recalcTarget;
          if (target == null || target == 'auto') {
            final bool chI = ni != s.intensity;
            final bool chE = ne != s.effort;
            final bool chV = nv != s.volume;
            if ((chI || chE) && !chV) {
              target = 'reps';
            } else if (chV && !(chI || chE)) {
              target = 'intensity';
            } else if (chI && chV && !chE) {
              target = 'rpe';
            } else {
              target = null;
            }
          }

          if (target == 'reps') {
            if (ni != null && ne != null) {
              final r = rpe_table.RpeTable.getReps(ni, ne);
              if (r != null) nv = _clampVolume(r);
            }
          } else if (target == 'rpe') {
            if (ni != null && nv != null) {
              final rpe = rpe_table.RpeTable.getRpe(ni, nv);
              if (rpe != null) {
                ne = _clampEffort(rpe);
              } else {
                final strategy = fixStrategy ?? 'none';
                if (strategy == 'fixReps') {
                  final fixed = _nearestRepsForIntensity(ni, nv);
                  if (fixed != null) {
                    nv = _clampVolume(fixed);
                    final rpe2 = rpe_table.RpeTable.getRpe(ni, nv!);
                    if (rpe2 != null) ne = _clampEffort(rpe2);
                  }
                } else if (strategy == 'fixIntensity') {
                  final ii = rpe_table.RpeTable.getIntensity(nv, 10);
                  if (ii != null) {
                    ni = _clampIntensity(ii);
                    final rpe2 = rpe_table.RpeTable.getRpe(ni!, nv);
                    if (rpe2 != null) ne = _clampEffort(rpe2);
                  }
                }
              }
            }
          } else if (target == 'intensity') {
            if (nv != null && ne != null) {
              final ii = rpe_table.RpeTable.getIntensity(nv, ne);
              if (ii != null) ni = _clampIntensity(ii);
            }
          }

          final ns = PlanSet(
            id: s.id,
            orderIndex: s.orderIndex,
            intensity: ni,
            effort: ne,
            volume: nv,
            planExerciseId: s.planExerciseId,
          );
          if (ns.intensity != s.intensity || ns.effort != s.effort || ns.volume != s.volume) {
            changed = true;
          }
          newSets.add(ns);
        }
        newExercises.add(PlanExercise(
          id: ex.id,
          exerciseDefinitionId: ex.exerciseDefinitionId,
          exerciseName: ex.exerciseName,
          orderIndex: ex.orderIndex,
          planWorkoutId: ex.planWorkoutId,
          sets: newSets,
        ));
      }
      micro.planWorkouts[wi] = PlanWorkout(
        id: w.id,
        microcycleId: w.microcycleId,
        dayLabel: w.dayLabel,
        orderIndex: w.orderIndex,
        exercises: newExercises,
      );
    }
    return changed;
  }

  Map<String, List<ExerciseScheduleItemDto>> _toSchedule(Microcycle micro) {
    final map = <String, List<ExerciseScheduleItemDto>>{};
    for (final pw in micro.planWorkouts) {
      final label = pw.dayLabel.trim();
      int? day;
      if (label.toLowerCase().startsWith('day ')) {
        final rest = label.substring(4).trim();
        day = int.tryParse(rest);
      }
      day ??= (pw.orderIndex + 1);
      final key = day.toString();
      final items = <ExerciseScheduleItemDto>[];
      for (final ex in pw.exercises) {
        final sets = ex.sets.map((s) => ParamsSets(
          intensity: s.intensity?.toDouble(),
          effort: s.effort?.toDouble(),
          volume: s.volume?.toDouble(),
        )).toList();
        items.add(ExerciseScheduleItemDto(id: 0, exerciseId: ex.exerciseDefinitionId, sets: sets, name: ex.exerciseName, exercises: const []));
      }
      if (items.isNotEmpty) {
        map[key] = items;
      }
    }
    return map;
  }
}
