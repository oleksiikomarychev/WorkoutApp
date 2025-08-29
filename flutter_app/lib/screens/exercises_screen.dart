import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:workout_app/config/constants/theme_constants.dart';
import 'package:workout_app/config/constants/app_constants.dart';
import 'package:workout_app/services/logger_service.dart';
import 'package:workout_app/services/exercise_service.dart';
import 'package:workout_app/widgets/empty_state.dart';
import 'package:workout_app/models/exercise_definition.dart';
import 'package:workout_app/services/service_locator.dart';
import 'package:workout_app/models/muscle_info.dart';

class ExercisesScreen extends ConsumerStatefulWidget {
  const ExercisesScreen({super.key});

  @override
  ConsumerState<ExercisesScreen> createState() => _ExercisesScreenState();
}

// State notifier for exercises
class ExercisesNotifier extends StateNotifier<AsyncValue<List<ExerciseDefinition>>> {
  final ExerciseService _exerciseService;
  
  ExercisesNotifier(this._exerciseService) : super(const AsyncValue.loading()) {
    loadExercises();
  }
  
  Future<void> loadExercises() async {
    state = const AsyncValue.loading();
    try {
      final exercises = await _exerciseService.getExerciseDefinitions();
      state = AsyncValue.data(exercises);
    } catch (e, stackTrace) {
      state = AsyncValue.error(e, stackTrace);
      rethrow;
    }
  }
}

// Simple autocomplete input that lets user pick one label at a time
class _TagAutocomplete extends StatefulWidget {
  final List<String> allOptions;
  final void Function(String label) onSelected;
  final Set<String> exclude; // labels already selected
  final List<String> selectedLabels; // render chips inline
  final void Function(String label) onDeleted;

  const _TagAutocomplete({
    required this.allOptions,
    required this.onSelected,
    required this.selectedLabels,
    required this.onDeleted,
    this.exclude = const <String>{},
  });

  @override
  State<_TagAutocomplete> createState() => _TagAutocompleteState();
}

class _TagAutocompleteState extends State<_TagAutocomplete> {
  final TextEditingController _controller = TextEditingController();
  TextEditingController? _fieldController; // controller provided by Autocomplete
  FocusNode? _fieldFocus; // focus provided by Autocomplete

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Autocomplete<String>(
      displayStringForOption: (opt) => opt,
      optionsBuilder: (TextEditingValue textEditingValue) {
        final q = textEditingValue.text.trim().toLowerCase();
        final base = widget.allOptions.where((o) => !widget.exclude.contains(o));
        if (q.isEmpty) return base.take(20);
        return base.where((o) => o.toLowerCase().contains(q)).take(20);
      },
      fieldViewBuilder: (context, controller, focusNode, onFieldSubmitted) {
        _controller.value = controller.value;
        _fieldController = controller;
        _fieldFocus = focusNode;
        // Nudge options to open when focused with empty text
        focusNode.addListener(() {
          if (focusNode.hasFocus) {
            controller.value = controller.value.copyWith(text: controller.text + ' ');
            controller.value = controller.value.copyWith(text: controller.text.isNotEmpty ? controller.text.trimRight() : '');
          }
        });

        return SizedBox(
          width: double.infinity,
          child: InputDecorator(
            decoration: const InputDecoration(
              labelText: 'Add muscle tag',
              hintText: 'Type to search...',
              border: OutlineInputBorder(),
              isDense: false,
              contentPadding: EdgeInsets.fromLTRB(12, 20, 12, 12),
              floatingLabelBehavior: FloatingLabelBehavior.always,
            ),
            child: Wrap(
              spacing: 6,
              runSpacing: 6,
              children: [
                for (final l in widget.selectedLabels)
                  Chip(
                    label: Text(l),
                    onDeleted: () => widget.onDeleted(l),
                    materialTapTargetSize: MaterialTapTargetSize.shrinkWrap,
                    visualDensity: VisualDensity.compact,
                  ),
                ConstrainedBox(
                  constraints: const BoxConstraints(minWidth: 80, maxWidth: 260),
                  child: TextField(
                    controller: controller,
                    focusNode: focusNode,
                    decoration: const InputDecoration.collapsed(
                      hintText: 'Type to search...',
                    ),
                    onSubmitted: (value) {
                      final label = value.trim();
                      if (label.isEmpty) return;
                      // Try to match exactly (case-insensitive) to an available option
                      final lower = label.toLowerCase();
                      final match = widget.allOptions.firstWhere(
                        (o) => o.toLowerCase() == lower,
                        orElse: () => '',
                      );
                      if (match.isNotEmpty) {
                        widget.onSelected(match);
                        controller.clear();
                      }
                    },
                  ),
                ),
              ],
            ),
          ),
        );
      },
      onSelected: (String selection) {
        widget.onSelected(selection);
        _controller.clear();
        _fieldController?.clear();
        // Keep focus to allow rapid multi-add
        if (_fieldFocus != null) {
          Future.microtask(() => _fieldFocus!.requestFocus());
        }
      },
    );
  }
}

class _SelectedChips extends StatelessWidget {
  final List<String> labels;
  final void Function(String label) onDeleted;

  const _SelectedChips({required this.labels, required this.onDeleted});

  @override
  Widget build(BuildContext context) {
    if (labels.isEmpty) {
      return Text('No tags selected', style: Theme.of(context).textTheme.bodySmall);
    }
    return Wrap(
      spacing: 8,
      runSpacing: -8,
      children: [
        for (final l in labels)
          Chip(
            label: Text(l),
            onDeleted: () => onDeleted(l),
          ),
      ],
    );
  }
}

// Provider for exercises notifier
final exercisesNotifierProvider = StateNotifierProvider<ExercisesNotifier, AsyncValue<List<ExerciseDefinition>>>((ref) {
  final exerciseService = ref.watch(exerciseServiceProvider);
  return ExercisesNotifier(exerciseService);
});

class _ExercisesScreenState extends ConsumerState<ExercisesScreen> {
  final LoggerService _logger = LoggerService('ExercisesScreen');
  final TextEditingController _nameController = TextEditingController();
  final TextEditingController _equipmentController = TextEditingController();
  String? _movementType; // 'compound' | 'isolation'
  String? _region; // 'upper' | 'lower'
  // Muscles dropdown state
  String? _selectedMuscleGroup;
  Future<List<String>>? _groupsFuture;
  // Muscles (enum) for tag selectors
  Future<List<MuscleInfo>>? _musclesFuture;
  List<MuscleInfo> _muscles = const [];
  // Selected tags (store KEYS for backend; render labels)
  final Set<String> _selectedTargetKeys = <String>{};
  final Set<String> _selectedSynergistKeys = <String>{};
  // Equipment tags (store labels directly)
  final Set<String> _selectedEquipment = <String>{};
  
  @override
  void initState() {
    super.initState();
    // Trigger initial load
    WidgetsBinding.instance.addPostFrameCallback((_) {
      ref.read(exercisesNotifierProvider.notifier).loadExercises();
    });
  }

  @override
  void dispose() {
    _nameController.dispose();
    _equipmentController.dispose();
    super.dispose();
  }

  Future<void> _showExerciseDialog({ExerciseDefinition? initial}) async {
    _nameController.text = initial?.name ?? '';
    _selectedMuscleGroup = initial?.muscleGroup;
    _equipmentController.text = initial?.equipment ?? '';
    _movementType = initial?.movementType;
    _region = initial?.region;
    _selectedTargetKeys
      ..clear()
      ..addAll(initial?.targetMuscles ?? const <String>[]);
    _selectedSynergistKeys
      ..clear()
      ..addAll(initial?.synergistMuscles ?? const <String>[]);

    // Initialize equipment tags from comma-separated string (if any)
    _selectedEquipment
      ..clear()
      ..addAll(
        (initial?.equipment ?? '')
            .split(',')
            .map((e) => e.trim())
            .where((e) => e.isNotEmpty),
      );

    final service = ref.read(exerciseServiceProvider);
    final isEdit = initial?.id != null;

    // Prepare groups Future (load from backend muscles endpoint)
    _groupsFuture = service.getMuscles().then((muscles) {
      final groups = muscles.map((m) => m.group).toSet().toList()..sort();
      // Ensure selected group is valid
      if (_selectedMuscleGroup != null && !groups.contains(_selectedMuscleGroup)) {
        _selectedMuscleGroup = null;
      }
      return groups;
    });

    // Load full muscles list for tag pickers and wait for it
    try {
      _muscles = await service.getMuscles();
    } catch (e) {
      // Handle error if needed
      _muscles = [];
    }
    _musclesFuture = Future.value(_muscles);

    await showDialog(
      context: context,
      builder: (ctx) => StatefulBuilder(
        builder: (context, setDialogState) => AlertDialog(
          title: Text(isEdit ? 'Edit Exercise' : 'Create Exercise'),
          content: SingleChildScrollView(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
              TextField(
                controller: _nameController,
                decoration: const InputDecoration(labelText: 'Name'),
              ),
              const SizedBox(height: 8),
              FutureBuilder<List<String>>(
                future: _groupsFuture,
                builder: (context, snapshot) {
                  if (snapshot.connectionState == ConnectionState.waiting) {
                    return const ListTile(
                      contentPadding: EdgeInsets.zero,
                      title: Text('Muscle group'),
                      subtitle: Text('Loading...'),
                    );
                  }
                  if (snapshot.hasError) {
                    return Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        const Text('Muscle group', style: TextStyle(fontSize: 12, color: Colors.grey)),
                        const SizedBox(height: 4),
                        Text('Failed to load groups: ${snapshot.error}', style: const TextStyle(color: Colors.red)),
                      ],
                    );
                  }
                  final groups = snapshot.data ?? const <String>[];
                  return DropdownButtonFormField<String>(
                    value: _selectedMuscleGroup,
                    isExpanded: true,
                    decoration: const InputDecoration(labelText: 'Muscle group'),
                    hint: const Text('Select group'),
                    items: groups
                        .map((g) => DropdownMenuItem<String>(value: g, child: Text(g)))
                        .toList(),
                    onChanged: (val) => setDialogState(() => _selectedMuscleGroup = val),
                  );
                },
              ),
              const SizedBox(height: 8),
              // Target muscles tags
              Align(
                alignment: Alignment.centerLeft,
                child: Text('Target muscles', style: Theme.of(context).textTheme.bodySmall),
              ),
              const SizedBox(height: 4),
              FutureBuilder<List<MuscleInfo>>(
                future: _musclesFuture,
                builder: (context, snap) {
                  if (snap.connectionState == ConnectionState.waiting) {
                    return const LinearProgressIndicator(minHeight: 2);
                  }
                  if (snap.hasError) {
                    return Text('Failed to load muscles: ${snap.error}', style: const TextStyle(color: Colors.red));
                  }
                  final muscles = snap.data ?? const <MuscleInfo>[];
                  final selectedLabels = _selectedTargetKeys
                      .map((k) => _muscles.firstWhere((m) => m.key == k, orElse: () => MuscleInfo(key: k, label: k, group: '')).label)
                      .toList()
                    ..sort();
                  return _TagAutocomplete(
                    allOptions: muscles.map((m) => m.label).toList(),
                    selectedLabels: selectedLabels,
                    onDeleted: (label) => setDialogState(() {
                      final key = _muscles.firstWhere((m) => m.label == label, orElse: () => const MuscleInfo(key: '', label: '', group: '')).key;
                      if (key.isNotEmpty) _selectedTargetKeys.remove(key);
                    }),
                    exclude: _selectedTargetKeys
                        .map((k) => _muscles.firstWhere((m) => m.key == k, orElse: () => MuscleInfo(key: k, label: k, group: '')).label)
                        .toSet(),
                    onSelected: (label) => setDialogState(() {
                      final normalized = label.trim().toLowerCase();
                      final key = muscles
                          .firstWhere(
                            (m) => m.label.trim().toLowerCase() == normalized,
                            orElse: () => const MuscleInfo(key: '', label: '', group: ''),
                          )
                          .key;
                      if (key.isNotEmpty) _selectedTargetKeys.add(key);
                    }),
                  );
                },
              ),
              const SizedBox(height: 8),
              // Synergist muscles tags
              Align(
                alignment: Alignment.centerLeft,
                child: Text('Synergist muscles', style: Theme.of(context).textTheme.bodySmall),
              ),
              const SizedBox(height: 4),
              FutureBuilder<List<MuscleInfo>>(
                future: _musclesFuture,
                builder: (context, snap) {
                  if (snap.connectionState == ConnectionState.waiting) {
                    return const LinearProgressIndicator(minHeight: 2);
                  }
                  if (snap.hasError) {
                    return Text('Failed to load muscles: ${snap.error}', style: const TextStyle(color: Colors.red));
                  }
                  final muscles = snap.data ?? const <MuscleInfo>[];
                  final selectedLabels = _selectedSynergistKeys
                      .map((k) => _muscles.firstWhere((m) => m.key == k, orElse: () => MuscleInfo(key: k, label: k, group: '')).label)
                      .toList()
                    ..sort();
                  return _TagAutocomplete(
                    allOptions: muscles.map((m) => m.label).toList(),
                    selectedLabels: selectedLabels,
                    onDeleted: (label) => setDialogState(() {
                      final key = _muscles.firstWhere((m) => m.label == label, orElse: () => const MuscleInfo(key: '', label: '', group: '')).key;
                      if (key.isNotEmpty) _selectedSynergistKeys.remove(key);
                    }),
                    exclude: _selectedSynergistKeys
                        .map((k) => _muscles.firstWhere((m) => m.key == k, orElse: () => MuscleInfo(key: k, label: k, group: '')).label)
                        .toSet(),
                    onSelected: (label) => setDialogState(() {
                      final normalized = label.trim().toLowerCase();
                      final key = muscles
                          .firstWhere(
                            (m) => m.label.trim().toLowerCase() == normalized,
                            orElse: () => const MuscleInfo(key: '', label: '', group: ''),
                          )
                          .key;
                      if (key.isNotEmpty) _selectedSynergistKeys.add(key);
                    }),
                  );
                },
              ),
              const SizedBox(height: 8),
              // Equipment tags (enum + tags)
              Align(
                alignment: Alignment.centerLeft,
                child: Text('Equipment', style: Theme.of(context).textTheme.bodySmall),
              ),
              const SizedBox(height: 4),
              _TagAutocomplete(
                allOptions: AppConstants.exerciseEquipment,
                selectedLabels: _selectedEquipment.toList()..sort(),
                onDeleted: (label) => setDialogState(() {
                  _selectedEquipment.remove(label);
                }),
                exclude: _selectedEquipment,
                onSelected: (label) => setDialogState(() {
                  _selectedEquipment.add(label);
                }),
              ),
              const SizedBox(height: 8),
              DropdownButtonFormField<String>(
                value: _movementType,
                decoration: const InputDecoration(labelText: 'Movement type'),
                items: const [
                  DropdownMenuItem(value: 'compound', child: Text('Compound')),
                  DropdownMenuItem(value: 'isolation', child: Text('Isolation')),
                ],
                onChanged: (val) => setDialogState(() => _movementType = val),
              ),
              const SizedBox(height: 8),
              DropdownButtonFormField<String>(
                value: _region,
                decoration: const InputDecoration(labelText: 'Region'),
                items: const [
                  DropdownMenuItem(value: 'upper', child: Text('Upper')),
                  DropdownMenuItem(value: 'lower', child: Text('Lower')),
                ],
                onChanged: (val) => setDialogState(() => _region = val),
              ),
            ],
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(ctx).pop(),
            child: const Text('Cancel'),
          ),
          ElevatedButton(
            onPressed: () async {
              final name = _nameController.text.trim();
              if (name.isEmpty) return;
              final payload = ExerciseDefinition(
                id: initial?.id,
                name: name,
                muscleGroup: (_selectedMuscleGroup == null || _selectedMuscleGroup!.isEmpty)
                    ? null
                    : _selectedMuscleGroup,
                equipment: _selectedEquipment.isEmpty ? null : _selectedEquipment.join(', '),
                targetMuscles: _selectedTargetKeys.isEmpty ? null : _selectedTargetKeys.toList(),
                synergistMuscles: _selectedSynergistKeys.isEmpty ? null : _selectedSynergistKeys.toList(),
                movementType: _movementType,
                region: _region,
              );
              try {
                if (isEdit) {
                  await service.updateExerciseDefinition(payload);
                } else {
                  await service.createExerciseDefinition(payload);
                }
                if (!mounted) return;
                Navigator.of(ctx).pop();
                await ref.read(exercisesNotifierProvider.notifier).loadExercises();
              } catch (e) {
                if (!mounted) return;
                ScaffoldMessenger.of(context).showSnackBar(
                  SnackBar(content: Text('Failed to ${isEdit ? 'update' : 'create'} exercise: $e')),
                );
              }
            },
            child: Text(isEdit ? 'Save' : 'Create'),
          ),
        ],
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: Consumer(
        builder: (context, ref, child) {
          final exercisesState = ref.watch(exercisesNotifierProvider);
          
          return exercisesState.when(
            loading: () => const Center(child: CircularProgressIndicator()),
            error: (error, stackTrace) {
              _logger.e('Error loading exercises: $error\n$stackTrace');
              return Center(
                child: Column(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    const Icon(Icons.error_outline, color: Colors.red, size: 48),
                    const SizedBox(height: 16),
                    Text(
                      'Error loading exercises',
                      style: Theme.of(context).textTheme.titleMedium,
                    ),
                    const SizedBox(height: 8),
                    Text(
                      error.toString(),
                      textAlign: TextAlign.center,
                      style: Theme.of(context).textTheme.bodySmall,
                    ),
                    const SizedBox(height: 16),
                    ElevatedButton.icon(
                      onPressed: () => ref.refresh(exercisesNotifierProvider),
                      icon: const Icon(Icons.refresh),
                      label: const Text('Retry'),
                    ),
                  ],
                ),
              );
            },
            data: (exercises) {
              if (exercises.isEmpty) {
                return EmptyState(
                  icon: Icons.fitness_center,
                  title: 'No Exercises',
                  description: 'No exercises found. Add your first exercise!',
                  action: ElevatedButton.icon(
                    onPressed: () => ref.refresh(exercisesNotifierProvider),
                    icon: const Icon(Icons.refresh),
                    label: const Text('Refresh'),
                  ),
                );
              }
              
              return RefreshIndicator(
                onRefresh: () async {
                  await ref.refresh(exercisesNotifierProvider);
                  await ref.read(exercisesNotifierProvider.notifier).loadExercises();
                },
                child: ListView.builder(
                  padding: const EdgeInsets.all(16),
                  itemCount: exercises.length,
                  itemBuilder: (context, index) {
                    final exercise = exercises[index];
                    return Card(
                      margin: const EdgeInsets.only(bottom: 16),
                      child: ListTile(
                        leading: const Icon(Icons.fitness_center),
                        title: Text(
                          exercise.name,
                          style: Theme.of(context).textTheme.titleMedium,
                        ),
                        subtitle: Text(
                          '${exercise.muscleGroup ?? 'No muscle group'} • ${exercise.equipment ?? 'No equipment'}',
                          style: Theme.of(context).textTheme.bodySmall,
                        ),
                        trailing: Row(
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            IconButton(
                              icon: const Icon(Icons.delete, color: Colors.redAccent),
                              onPressed: () async {
                                final confirm = await showDialog<bool>(
                                  context: context,
                                  builder: (ctx) => AlertDialog(
                                    title: const Text('Delete exercise?'),
                                    content: Text('Are you sure you want to delete "${exercise.name}"?'),
                                    actions: [
                                      TextButton(
                                        onPressed: () => Navigator.of(ctx).pop(false),
                                        child: const Text('Cancel'),
                                      ),
                                      ElevatedButton(
                                        onPressed: () => Navigator.of(ctx).pop(true),
                                        child: const Text('Delete'),
                                      ),
                                    ],
                                  ),
                                );
                                if (confirm != true) return;
                                try {
                                  await ref.read(exerciseServiceProvider).deleteExerciseDefinition(exercise.id!);
                                  if (!mounted) return;
                                  await ref.read(exercisesNotifierProvider.notifier).loadExercises();
                                } catch (e) {
                                  if (!mounted) return;
                                  ScaffoldMessenger.of(context).showSnackBar(
                                    SnackBar(content: Text('Failed to delete exercise: $e')),
                                  );
                                }
                              },
                            ),
                            const Icon(Icons.chevron_right),
                          ],
                        ),
                        onTap: () => _showExerciseDialog(initial: exercise),
                      ),
                    );
                  },
                ),
              );
            },
          );
        },
      ),
      floatingActionButton: FloatingActionButton(
        onPressed: () => _showExerciseDialog(),
        child: const Icon(Icons.add),
      ),
    );
  }
}
