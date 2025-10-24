import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:workout_app/models/calendar_plan.dart';
import 'package:workout_app/models/microcycle.dart';
import 'package:workout_app/models/user_max.dart';
import 'package:workout_app/src/api/plan_api.dart';

class ApplyPlanWidget extends StatefulWidget {
  final CalendarPlan plan;
  final List<UserMax> userMaxList;
  final Set<int> allowedExerciseIds;
  final Set<String> allowedExerciseNames;
  final int planId;
  final Future<void> Function(Map<String, dynamic>) onApply;
  final VoidCallback? onUserMaxAdded;

  const ApplyPlanWidget({
    Key? key,
    required this.plan,
    required this.userMaxList,
    required this.allowedExerciseIds,
    required this.allowedExerciseNames,
    required this.planId,
    required this.onApply,
    this.onUserMaxAdded,
  }) : super(key: key);

  @override
  State<ApplyPlanWidget> createState() => _ApplyPlanWidgetState();
}

class _ApplyPlanWidgetState extends State<ApplyPlanWidget> {
  static const String _prefsKeyPrefix = 'apply_plan_last_user_max_ids';

  final _formKey = GlobalKey<FormState>();

  List<int> _selectedUserMaxIds = [];
  List<int> _savedUserMaxIds = [];
  bool _computeWeights = true;
  double _roundingStep = 2.5;
  String _roundingMode = 'nearest';
  bool _isApplying = false;

  @override
  void initState() {
    super.initState();
    _loadLastSelection();
  }

  @override
  void didUpdateWidget(covariant ApplyPlanWidget oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (!listEquals(oldWidget.userMaxList, widget.userMaxList) ||
        !setEquals(oldWidget.allowedExerciseIds, widget.allowedExerciseIds) ||
        !setEquals(oldWidget.allowedExerciseNames, widget.allowedExerciseNames)) {
      _filterCurrentSelection();
      _loadLastSelection();
    }
  }

  List<PlanExercise> _getAllPlanExercises() {
    final exercises = <PlanExercise>[];
    final seen = <String>{};

    for (final mesocycle in widget.plan.mesocycles) {
      for (final microcycle in mesocycle.microcycles) {
        for (final workout in microcycle.planWorkouts) {
          for (final exercise in workout.exercises) {
            final key = '${exercise.exerciseDefinitionId}_${exercise.exerciseName}';
            if (!seen.contains(key)) {
              seen.add(key);
              exercises.add(exercise);
            }
          }
        }
      }
    }

    exercises.sort((a, b) => a.exerciseName.compareTo(b.exerciseName));
    return exercises;
  }

  String? _normalizeExerciseName(String? name) {
    final value = name?.trim();
    if (value == null || value.isEmpty) return null;
    return value.toLowerCase();
  }

  List<UserMax> _userMaxesForExercise(PlanExercise exercise) {
    final byId = <UserMax>[];
    final byName = <UserMax>[];

    for (final userMax in widget.userMaxList) {
      if (userMax.exerciseId == exercise.exerciseDefinitionId && userMax.exerciseId > 0) {
        byId.add(userMax);
      }
    }

    if (byId.isNotEmpty) {
      return byId;
    }

    final normalized = _normalizeExerciseName(exercise.exerciseName);
    if (normalized == null) {
      return const [];
    }

    for (final userMax in widget.userMaxList) {
      final userMaxNormalized = _normalizeExerciseName(userMax.exerciseName);
      if (userMaxNormalized == normalized) {
        byName.add(userMax);
      }
    }

    return byName;
  }

  UserMax? _latestUserMax(List<UserMax> userMaxes) {
    if (userMaxes.isEmpty) {
      return null;
    }
    UserMax latest = userMaxes.first;
    for (final userMax in userMaxes.skip(1)) {
      if (userMax.id > latest.id) {
        latest = userMax;
      }
    }
    return latest;
  }

  Future<void> _showAddUserMaxSheet(PlanExercise exercise) async {
    final weightController = TextEditingController();
    final repsController = TextEditingController(text: '1');
    bool isSubmitting = false;
    String? errorMessage;

    final result = await showModalBottomSheet<bool>(
      context: context,
      isScrollControlled: true,
      builder: (sheetContext) {
        return Padding(
          padding: EdgeInsets.only(
            left: 16,
            right: 16,
            top: 16,
            bottom: MediaQuery.of(sheetContext).viewInsets.bottom + 16,
          ),
          child: StatefulBuilder(
            builder: (context, setModalState) {
              return Column(
                mainAxisSize: MainAxisSize.min,
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    'Добавить максимум для «${exercise.exerciseName}»',
                    style: Theme.of(context).textTheme.titleMedium,
                  ),
                  const SizedBox(height: 16),
                  TextField(
                    controller: weightController,
                    keyboardType: TextInputType.number,
                    decoration: const InputDecoration(
                      labelText: 'Вес (кг)',
                    ),
                  ),
                  const SizedBox(height: 12),
                  TextField(
                    controller: repsController,
                    keyboardType: TextInputType.number,
                    decoration: const InputDecoration(
                      labelText: 'Повторения',
                    ),
                  ),
                  if (errorMessage != null) ...[
                    const SizedBox(height: 12),
                    Text(
                      errorMessage!,
                      style: TextStyle(color: Theme.of(context).colorScheme.error, fontSize: 12),
                    ),
                  ],
                  const SizedBox(height: 16),
                  SizedBox(
                    width: double.infinity,
                    child: FilledButton(
                      onPressed: isSubmitting
                          ? null
                          : () async {
                              final weight = int.tryParse(weightController.text);
                              final reps = int.tryParse(repsController.text);
                              if (weight == null || weight <= 0) {
                                setModalState(() {
                                  errorMessage = 'Введите корректный вес';
                                });
                                return;
                              }
                              if (reps == null || reps <= 0 || reps > 12) {
                                setModalState(() {
                                  errorMessage = 'Введите 1–12 повторений';
                                });
                                return;
                              }

                              setModalState(() {
                                isSubmitting = true;
                                errorMessage = null;
                              });

                              try {
                                await PlanApi.createUserMax(
                                  exerciseId: exercise.exerciseDefinitionId,
                                  maxWeight: weight,
                                  repMax: reps,
                                  date: DateTime.now().toIso8601String().split('T').first,
                                );
                                if (Navigator.of(sheetContext).canPop()) {
                                  Navigator.of(sheetContext).pop(true);
                                }
                              } catch (e) {
                                setModalState(() {
                                  errorMessage = 'Не удалось сохранить максимум: $e';
                                  isSubmitting = false;
                                });
                              }
                            },
                      child: isSubmitting
                          ? const SizedBox(
                              width: 18,
                              height: 18,
                              child: CircularProgressIndicator(strokeWidth: 2),
                            )
                          : const Text('Сохранить'),
                    ),
                  ),
                ],
              );
            },
          ),
        );
      },
    );

    weightController.dispose();
    repsController.dispose();

    if (result == true) {
      widget.onUserMaxAdded?.call();
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Максимум для ${exercise.exerciseName} сохранён')),
      );
    }
  }

  String get _storageKey => '${_prefsKeyPrefix}_${widget.planId}';

  Future<void> _loadLastSelection() async {
    final prefs = await SharedPreferences.getInstance();
    final saved = prefs.getStringList(_storageKey);
    final parsed = saved
            ?.map((value) => int.tryParse(value))
            .whereType<int>()
            .toList() ??
        [];

    if (!mounted) return;
    setState(() {
      _savedUserMaxIds = parsed;
    });
  }

  Future<void> _saveCurrentSelection(List<int> userMaxIds) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setStringList(
      _storageKey,
      userMaxIds.map((id) => id.toString()).toList(),
    );
    if (!mounted) return;
    setState(() {
      _savedUserMaxIds = List<int>.from(userMaxIds);
    });
  }

  void _filterCurrentSelection() {
    final allowedUserMaxIds = widget.userMaxList
        .where(_isExerciseAllowed)
        .map((userMax) => userMax.id)
        .toSet();

    _selectedUserMaxIds =
        _selectedUserMaxIds.where(allowedUserMaxIds.contains).toList();
  }

  bool _isExerciseAllowed(UserMax userMax) {
    if (widget.allowedExerciseIds.isEmpty &&
        widget.allowedExerciseNames.isEmpty) {
      return true;
    }

    if (widget.allowedExerciseIds.contains(userMax.exerciseId)) {
      return true;
    }

    final normalizedName = userMax.exerciseName.trim().toLowerCase();
    return widget.allowedExerciseNames.contains(normalizedName);
  }

  String _groupKey(UserMax userMax) {
    if (userMax.exerciseId > 0) {
      return 'id_${userMax.exerciseId}';
    }
    return 'name_${userMax.exerciseName.trim().toLowerCase()}';
  }

  Set<int> _computeLatestSelection(Map<String, List<UserMax>> groupedUserMaxes) {
    final latestIds = <int>{};
    for (final entry in groupedUserMaxes.values) {
      if (entry.isEmpty) continue;
      final latest = entry.reduce(
        (current, next) => next.id > current.id ? next : current,
      );
      latestIds.add(latest.id);
    }
    return latestIds;
  }

  void _applySelection(List<int> userMaxIds) {
    setState(() {
      _selectedUserMaxIds = userMaxIds.toSet().toList();
    });
  }

  void _handleUseLastValues(
    Map<String, List<UserMax>> groupedUserMaxes,
    Set<int> availableUserMaxIds,
  ) {
    final savedMatches =
        _savedUserMaxIds.where(availableUserMaxIds.contains).toList();

    if (savedMatches.isNotEmpty) {
      _applySelection(savedMatches);
      return;
    }

    final latestIds = _computeLatestSelection(groupedUserMaxes)
        .where(availableUserMaxIds.contains)
        .toList();

    if (latestIds.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Нет сохранённых максимумов для этого плана')),
      );
      return;
    }

    _applySelection(latestIds);
  }

  @override
  Widget build(BuildContext context) {
    final filteredUserMaxes = widget.userMaxList
        .where(_isExerciseAllowed)
        .toList();

    final useFallback = filteredUserMaxes.isEmpty && widget.userMaxList.isNotEmpty;
    final effectiveUserMaxes =
        useFallback ? widget.userMaxList : filteredUserMaxes;

    final availableUserMaxIds =
        effectiveUserMaxes.map((userMax) => userMax.id).toSet();

    final groupedUserMaxes = <String, List<UserMax>>{};
    for (final userMax in effectiveUserMaxes) {
      groupedUserMaxes
          .putIfAbsent(_groupKey(userMax), () => <UserMax>[])
          .add(userMax);
    }

    final groupedEntries = groupedUserMaxes.entries.toList()
      ..sort((a, b) => a.value.first.exerciseName
          .toLowerCase()
          .compareTo(b.value.first.exerciseName.toLowerCase()));

    return FractionallySizedBox(
      heightFactor: 0.7,
      child: Container(
        decoration: BoxDecoration(
          color: Theme.of(context).colorScheme.surface,
          borderRadius: const BorderRadius.vertical(top: Radius.circular(28)),
          boxShadow: [
            BoxShadow(
              color: Colors.black.withOpacity(0.2),
              blurRadius: 12,
              offset: const Offset(0, -4),
            ),
          ],
        ),
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(24),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Text(
                    'Apply Training Plan',
                    style: Theme.of(context).textTheme.headlineSmall,
                  ),
                  IconButton(
                    icon: const Icon(Icons.close),
                    onPressed: () => Navigator.pop(context),
                  ),
                ],
              ),
              const Divider(height: 24),
              Form(
                key: _formKey,
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      children: [
                        Text(
                          'Select User Max',
                          style: Theme.of(context).textTheme.titleMedium,
                        ),
                        if (groupedEntries.isNotEmpty)
                          TextButton.icon(
                            onPressed: () => _handleUseLastValues(
                              groupedUserMaxes,
                              availableUserMaxIds,
                            ),
                            icon: const Icon(Icons.history),
                            label: const Text('Использовать последние'),
                          ),
                      ],
                    ),
                    const SizedBox(height: 12),
                    Container(
                      padding: const EdgeInsets.all(12),
                      decoration: BoxDecoration(
                        color: Colors.blue.shade50,
                        borderRadius: BorderRadius.circular(8),
                        border: Border.all(color: Colors.blue.shade200),
                      ),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Row(
                            children: [
                              Icon(Icons.info_outline, size: 18, color: Colors.blue.shade700),
                              const SizedBox(width: 8),
                              Text(
                                'Упражнения в плане',
                                style: TextStyle(
                                  fontWeight: FontWeight.w600,
                                  fontSize: 14,
                                  color: Colors.blue.shade700,
                                ),
                              ),
                            ],
                          ),
                          const SizedBox(height: 8),
                          ..._getAllPlanExercises().map((exercise) {
                            final userMaxes = _userMaxesForExercise(exercise);
                            final latestUserMax = _latestUserMax(userMaxes);
                            return Padding(
                              padding: const EdgeInsets.symmetric(vertical: 4),
                              child: Row(
                                children: [
                                  Expanded(
                                    child: Column(
                                      crossAxisAlignment: CrossAxisAlignment.start,
                                      children: [
                                        Text(
                                          exercise.exerciseName,
                                          style: const TextStyle(
                                            fontSize: 13,
                                            fontWeight: FontWeight.w500,
                                          ),
                                        ),
                                        if (latestUserMax != null)
                                          Text(
                                            '${latestUserMax.maxWeight} кг × ${latestUserMax.repMax}',
                                            style: TextStyle(
                                              fontSize: 11,
                                              color: Colors.green.shade700,
                                            ),
                                          )
                                        else
                                          Text(
                                            'Максимум не задан',
                                            style: TextStyle(
                                              fontSize: 11,
                                              color: Colors.grey.shade600,
                                            ),
                                          ),
                                      ],
                                    ),
                                  ),
                                  TextButton.icon(
                                    onPressed: () => _showAddUserMaxSheet(exercise),
                                    icon: const Icon(Icons.add, size: 16),
                                    label: const Text('Добавить'),
                                    style: TextButton.styleFrom(
                                      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                                      minimumSize: Size.zero,
                                      tapTargetSize: MaterialTapTargetSize.shrinkWrap,
                                    ),
                                  ),
                                ],
                              ),
                            );
                          }).toList(),
                        ],
                      ),
                    ),
                    const SizedBox(height: 16),
                    if (groupedEntries.isEmpty)
                      Padding(
                        padding: const EdgeInsets.symmetric(vertical: 12),
                        child: Text(
                          'Нет сохранённых максимумов для упражнений в плане.',
                          style: Theme.of(context).textTheme.bodyMedium,
                        ),
                      )
                    else if (useFallback)
                      Padding(
                        padding: const EdgeInsets.symmetric(vertical: 12),
                        child: Text(
                          'В плане не найдено совпадающих упражнений, показаны все ваши User Max.',
                          style: Theme.of(context)
                              .textTheme
                              .bodyMedium
                              ?.copyWith(color: Theme.of(context).colorScheme.primary),
                        ),
                      )
                    else
                      Column(
                        children: groupedEntries.map((entry) {
                          final userMaxes = entry.value;
                          return ExpansionTile(
                            key: ValueKey(entry.key),
                            title: Text(userMaxes.first.exerciseName),
                            children: userMaxes.map((userMax) {
                              return Padding(
                                padding:
                                    const EdgeInsets.symmetric(vertical: 4),
                                child: FilterChip.elevated(
                                  label: Text(
                                    '${userMax.maxWeight} kg x ${userMax.repMax}',
                                  ),
                                  selected:
                                      _selectedUserMaxIds.contains(userMax.id),
                                  onSelected: (selected) {
                                    setState(() {
                                      if (selected) {
                                        _selectedUserMaxIds.add(userMax.id);
                                      } else {
                                        _selectedUserMaxIds
                                            .remove(userMax.id);
                                      }
                                    });
                                  },
                                ),
                              );
                            }).toList(),
                          );
                        }).toList(),
                      ),
                    const SizedBox(height: 20),
                    Row(
                      children: [
                        Switch.adaptive(
                          value: _computeWeights,
                          onChanged: (value) {
                            setState(() => _computeWeights = value);
                          },
                        ),
                        const SizedBox(width: 8),
                        Text(
                          'Compute weights',
                          style: Theme.of(context).textTheme.bodyLarge,
                        ),
                      ],
                    ),
                    const SizedBox(height: 20),
                    Row(
                      children: [
                        Expanded(
                          child: TextFormField(
                            decoration: const InputDecoration(
                              labelText: 'Rounding Step',
                              border: OutlineInputBorder(),
                              isDense: true,
                            ),
                            keyboardType: TextInputType.number,
                            initialValue: _roundingStep.toString(),
                            onChanged: (value) {
                              _roundingStep = double.tryParse(value) ?? 2.5;
                            },
                          ),
                        ),
                        const SizedBox(width: 16),
                        Expanded(
                          child: DropdownButtonFormField<String>(
                            value: _roundingMode,
                            decoration: const InputDecoration(
                              labelText: 'Rounding Mode',
                              border: OutlineInputBorder(),
                              isDense: true,
                            ),
                            items: const ['nearest', 'ceil', 'floor']
                                .map(
                                  (mode) => DropdownMenuItem(
                                    value: mode,
                                    child: Text(mode),
                                  ),
                                )
                                .toList(),
                            onChanged: (value) {
                              setState(() {
                                _roundingMode = value ?? 'nearest';
                              });
                            },
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 24),
                    FilledButton.tonal(
                      onPressed: _isApplying
                          ? null
                          : () async {
                              final validSelection = _selectedUserMaxIds
                                  .where(availableUserMaxIds.contains)
                                  .toList();

                              if (validSelection.isEmpty) {
                                ScaffoldMessenger.of(context).showSnackBar(
                                  const SnackBar(
                                    content: Text(
                                      'Пожалуйста, выберите хотя бы один User Max',
                                    ),
                                  ),
                                );
                                return;
                              }

                              setState(() {
                                _isApplying = true;
                              });

                              try {
                                await _saveCurrentSelection(validSelection);

                                await widget.onApply({
                                  'user_max_ids': validSelection,
                                  'compute_weights': _computeWeights,
                                  'rounding_step': _roundingStep,
                                  'rounding_mode': _roundingMode,
                                  'generate_workouts': true,
                                });
                              } finally {
                                if (!mounted) return;
                                setState(() {
                                  _isApplying = false;
                                });
                              }
                            },
                      child: _isApplying
                          ? const SizedBox(
                              height: 18,
                              width: 18,
                              child: CircularProgressIndicator(strokeWidth: 2),
                            )
                          : const Text('Apply Plan'),
                    ),
                  ],
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
