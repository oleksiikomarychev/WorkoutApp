import 'package:flutter/material.dart';
import 'dart:async';
import 'package:workout_app/models/microcycle.dart';
import 'package:workout_app/models/plan_schedule.dart';
import 'package:workout_app/services/api_client.dart';
import 'package:workout_app/services/mesocycle_service.dart';
import 'package:workout_app/models/exercise_definition.dart';
import 'package:workout_app/screens/exercise_selection_screen.dart';

class PlanMicrocycleEditor extends StatefulWidget {
  final Microcycle microcycle;

  const PlanMicrocycleEditor({super.key, required this.microcycle});

  @override
  State<PlanMicrocycleEditor> createState() => _PlanMicrocycleEditorState();
}

class _PlanMicrocycleEditorState extends State<PlanMicrocycleEditor> {
  late Microcycle _editing;
  bool _saving = false;
  String? _error;
  bool _dirty = false;
  Timer? _autosaveTimer;
  static const _autosaveDelay = Duration(milliseconds: 1200);

  late final MesocycleService _mesoService;

  @override
  void initState() {
    super.initState();
    _editing = widget.microcycle;
    _mesoService = MesocycleService(apiClient: ApiClient());
  }

  @override
  void dispose() {
    _autosaveTimer?.cancel();
    super.dispose();
  }

  void _markDirtyAndScheduleSave() {
    _dirty = true;
    _autosaveTimer?.cancel();
    _autosaveTimer = Timer(_autosaveDelay, () {
      if (mounted && _dirty && !_saving) {
        _save();
      }
    });
  }

  Future<void> _bulkEditExerciseSets({
    required int workoutIdx,
    required int exerciseIdx,
  }) async {
    final intensityCtrl = TextEditingController();
    final effortCtrl = TextEditingController();
    final volumeCtrl = TextEditingController();

    await showDialog<void>(
      context: context,
      builder: (ctx) {
        return AlertDialog(
          title: const Text('Массовое изменение сетов'),
          content: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              TextField(
                controller: intensityCtrl,
                decoration: const InputDecoration(labelText: 'Интенсивность %1RM (опционально)'),
                keyboardType: TextInputType.number,
              ),
              TextField(
                controller: effortCtrl,
                decoration: const InputDecoration(labelText: 'RPE (опционально)'),
                keyboardType: TextInputType.number,
              ),
              TextField(
                controller: volumeCtrl,
                decoration: const InputDecoration(labelText: 'Повторы (опционально)'),
                keyboardType: TextInputType.number,
              ),
            ],
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.of(ctx).pop(),
              child: const Text('Отмена'),
            ),
            FilledButton(
              onPressed: () {
                final intensity = int.tryParse(intensityCtrl.text);
                final effort = int.tryParse(effortCtrl.text);
                final volume = int.tryParse(volumeCtrl.text);
                setState(() {
                  final ex = _editing.planWorkouts[workoutIdx].exercises[exerciseIdx];
                  final newSets = <PlanSet>[];
                  for (final s in ex.sets) {
                    newSets.add(PlanSet(
                      id: s.id,
                      orderIndex: s.orderIndex,
                      intensity: intensity ?? s.intensity,
                      effort: effort ?? s.effort,
                      volume: volume ?? s.volume,
                      planExerciseId: s.planExerciseId,
                    ));
                  }
                  _editing.planWorkouts[workoutIdx].exercises[exerciseIdx] = PlanExercise(
                    id: ex.id,
                    exerciseDefinitionId: ex.exerciseDefinitionId,
                    exerciseName: ex.exerciseName,
                    orderIndex: ex.orderIndex,
                    planWorkoutId: ex.planWorkoutId,
                    sets: newSets,
                  );
                  _markDirtyAndScheduleSave();
                });
                Navigator.of(ctx).pop();
              },
              child: const Text('Применить'),
            ),
          ],
        );
      },
    );
  }

  Future<void> _save() async {
    if (_saving) return;
    setState(() {
      _saving = true;
      _error = null;
    });

    try {
      final schedule = _toSchedule(_editing);
      await _mesoService.updateMicrocycle(
        _editing.id,
        MicrocycleUpdateDto(
          name: _editing.name,
          daysCount: _editing.daysCount,
          schedule: schedule,
        ),
      );
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Микроцикл сохранён')));
      setState(() {
        _dirty = false;
      });
    } catch (e) {
      setState(() {
        _error = 'Ошибка сохранения: $e';
      });
    } finally {
      if (mounted) setState(() => _saving = false);
    }
  }

  Map<String, List<ExerciseScheduleItemDto>> _toSchedule(Microcycle micro) {
    // Convert planWorkouts (by day_label like "Day 1") into schedule map keyed by day number string
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
        final sets = ex.sets
            .map((s) => ParamsSets(
                  intensity: s.intensity?.toDouble(),
                  effort: s.effort?.toDouble(),
                  volume: s.volume?.toDouble(),
                ))
            .toList();
        items.add(ExerciseScheduleItemDto(
          id: 0,
          exerciseId: ex.exerciseDefinitionId,
          sets: sets,
          name: '',
          exercises: const [],
        ));
      }
      if (items.isNotEmpty) {
        map[key] = items;
      }
    }
    return map;
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text('Редактор микроцикла: ${_editing.name}'),
        actions: [
          IconButton(
            onPressed: () async {
              final confirmed = await showDialog<bool>(
                context: context,
                builder: (ctx) => AlertDialog(
                  title: const Text('Удалить микроцикл'),
                  content: Text('Вы уверены, что хотите удалить микроцикл "${_editing.name}"?'),
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
                  await _mesoService.deleteMicrocycle(_editing.id!);
                  if (mounted) {
                    ScaffoldMessenger.of(context).showSnackBar(
                      const SnackBar(content: Text('Микроцикл удалён')),
                    );
                    Navigator.of(context).pop({'deletedId': _editing.id});
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
            icon: const Icon(Icons.delete_outline, color: Colors.red),
            tooltip: 'Удалить микроцикл',
          ),
          IconButton(
            onPressed: _saving ? null : _save,
            icon: _saving
                ? const SizedBox(width: 18, height: 18, child: CircularProgressIndicator(strokeWidth: 2))
                : const Icon(Icons.save),
            tooltip: 'Сохранить',
          ),
        ],
      ),
      body: Padding(
        padding: const EdgeInsets.all(12.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                if (_dirty)
                  const Padding(
                    padding: EdgeInsets.only(right: 8.0),
                    child: Icon(Icons.circle, size: 10, color: Colors.amber),
                  ),
                if (_dirty)
                  const Text('Есть несохранённые изменения', style: TextStyle(fontSize: 12)),
              ],
            ),
            if (_error != null)
              Padding(
                padding: const EdgeInsets.only(bottom: 8.0),
                child: Text(_error!, style: TextStyle(color: Theme.of(context).colorScheme.error)),
              ),
            Expanded(
              child: ListView.builder(
                itemCount: _editing.planWorkouts.length,
                itemBuilder: (context, wIdx) {
                  final pw = _editing.planWorkouts[wIdx];
                  return Card(
                    margin: const EdgeInsets.symmetric(vertical: 6),
                    child: ExpansionTile(
                      title: Text('${pw.dayLabel}'),
                      subtitle: Text('Порядок: ${pw.orderIndex}'),
                      children: [
                        ...pw.exercises.asMap().entries.map((entry) {
                          final eIdx = entry.key;
                          final ex = entry.value;
                          return Padding(
                            padding: const EdgeInsets.symmetric(horizontal: 12.0, vertical: 6),
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Row(
                                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                                  children: [
                                    Expanded(child: Text('${ex.exerciseName}')),
                                    TextButton.icon(
                                      onPressed: () async {
                                        final result = await Navigator.of(context).push(
                                          MaterialPageRoute(
                                            builder: (_) => const ExerciseSelectionScreen(),
                                          ),
                                        );
                                        if (result is ExerciseDefinition) {
                                          setState(() {
                                            _editing.planWorkouts[wIdx].exercises[eIdx] = PlanExercise(
                                              id: ex.id,
                                              exerciseDefinitionId: result.id ?? ex.exerciseDefinitionId,
                                              exerciseName: result.name,
                                              orderIndex: ex.orderIndex,
                                              planWorkoutId: ex.planWorkoutId,
                                              sets: ex.sets,
                                            );
                                            _markDirtyAndScheduleSave();
                                          });
                                        }
                                      },
                                      icon: const Icon(Icons.swap_horiz),
                                      label: const Text('Заменить упражнение'),
                                    ),
                                    const SizedBox(width: 8),
                                    TextButton.icon(
                                      onPressed: () {
                                        setState(() {
                                          final sets = List<PlanSet>.from(_editing.planWorkouts[wIdx].exercises[eIdx].sets);
                                          sets.add(const PlanSet(id: 0));
                                          _editing.planWorkouts[wIdx].exercises[eIdx] = PlanExercise(
                                            id: ex.id,
                                            exerciseDefinitionId: ex.exerciseDefinitionId,
                                            exerciseName: ex.exerciseName,
                                            orderIndex: ex.orderIndex,
                                            planWorkoutId: ex.planWorkoutId,
                                            sets: sets,
                                          );
                                          _markDirtyAndScheduleSave();
                                        });
                                      },
                                      icon: const Icon(Icons.add),
                                      label: const Text('Добавить подход'),
                                    ),
                                    const SizedBox(width: 8),
                                    TextButton.icon(
                                      onPressed: () {
                                        _bulkEditExerciseSets(workoutIdx: wIdx, exerciseIdx: eIdx);
                                      },
                                      icon: const Icon(Icons.tune),
                                      label: const Text('Массово'),
                                    ),
                                  ],
                                ),
                                const SizedBox(height: 4),
                                ...ex.sets.asMap().entries.map((sEntry) {
                                  final sIdx = sEntry.key;
                                  final set = sEntry.value;
                                  return Row(
                                    children: [
                                      Expanded(
                                        child: TextFormField(
                                          initialValue: set.intensity?.toString() ?? '',
                                          decoration: const InputDecoration(labelText: '%1RM'),
                                          keyboardType: TextInputType.number,
                                          onChanged: (v) {
                                            final val = int.tryParse(v);
                                            setState(() {
                                              _editing.planWorkouts[wIdx].exercises[eIdx].sets[sIdx] = PlanSet(
                                                id: set.id,
                                                orderIndex: set.orderIndex,
                                                intensity: val,
                                                effort: set.effort,
                                                volume: set.volume,
                                                planExerciseId: set.planExerciseId,
                                              );
                                              _markDirtyAndScheduleSave();
                                            });
                                          },
                                        ),
                                      ),
                                      const SizedBox(width: 8),
                                      Expanded(
                                        child: TextFormField(
                                          initialValue: (set.effort?.toString() ?? ''),
                                          decoration: const InputDecoration(labelText: 'RPE'),
                                          keyboardType: TextInputType.number,
                                          onChanged: (v) {
                                            final val = int.tryParse(v);
                                            setState(() {
                                              _editing.planWorkouts[wIdx].exercises[eIdx].sets[sIdx] = PlanSet(
                                                id: set.id,
                                                orderIndex: set.orderIndex,
                                                intensity: set.intensity,
                                                effort: val,
                                                volume: set.volume,
                                                planExerciseId: set.planExerciseId,
                                              );
                                              _markDirtyAndScheduleSave();
                                            });
                                          },
                                        ),
                                      ),
                                      const SizedBox(width: 8),
                                      Expanded(
                                        child: TextFormField(
                                          initialValue: set.volume?.toString() ?? '',
                                          decoration: const InputDecoration(labelText: 'Повторы'),
                                          keyboardType: TextInputType.number,
                                          onChanged: (v) {
                                            final val = int.tryParse(v);
                                            setState(() {
                                              _editing.planWorkouts[wIdx].exercises[eIdx].sets[sIdx] = PlanSet(
                                                id: set.id,
                                                orderIndex: set.orderIndex,
                                                intensity: set.intensity,
                                                effort: set.effort,
                                                volume: val,
                                                planExerciseId: set.planExerciseId,
                                              );
                                              _markDirtyAndScheduleSave();
                                            });
                                          },
                                        ),
                                      ),
                                      IconButton(
                                        tooltip: 'Удалить подход',
                                        icon: const Icon(Icons.delete_outline),
                                        onPressed: () {
                                          setState(() {
                                            final sets = List<PlanSet>.from(_editing.planWorkouts[wIdx].exercises[eIdx].sets);
                                            if (sIdx >= 0 && sIdx < sets.length) {
                                              sets.removeAt(sIdx);
                                              _editing.planWorkouts[wIdx].exercises[eIdx] = PlanExercise(
                                                id: ex.id,
                                                exerciseDefinitionId: ex.exerciseDefinitionId,
                                                exerciseName: ex.exerciseName,
                                                orderIndex: ex.orderIndex,
                                                planWorkoutId: ex.planWorkoutId,
                                                sets: sets,
                                              );
                                              _markDirtyAndScheduleSave();
                                            }
                                          });
                                        },
                                      ),
                                    ],
                                  );
                                }),
                              ],
                            ),
                          );
                        }),
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
  }
}
