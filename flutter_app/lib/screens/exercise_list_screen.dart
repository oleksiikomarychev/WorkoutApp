import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:workout_app/l10n/app_localizations.dart';
import 'package:workout_app/widgets/primary_app_bar.dart';
import 'package:workout_app/widgets/assistant_chat_host.dart';
import 'package:workout_app/widgets/loading_indicator.dart';
import 'package:workout_app/widgets/error_message.dart';
import 'package:workout_app/widgets/empty_state.dart';
import '../models/exercise_definition.dart';
import 'package:workout_app/providers/target_data_providers.dart';
import 'package:workout_app/providers/exercise_pagination_provider.dart';

class ExerciseListScreen extends ConsumerStatefulWidget {
  const ExerciseListScreen({super.key});

  @override
  ConsumerState<ExerciseListScreen> createState() => _ExerciseListScreenState();
}

class _ExerciseListScreenState extends ConsumerState<ExerciseListScreen> {
  final ScrollController _scrollController = ScrollController();
  final TextEditingController _nameController = TextEditingController();
  final TextEditingController _equipmentController = TextEditingController();

  List<String> _muscleGroups = [];
  String? _selectedMuscleGroup;
  bool _loadingMuscles = false;

  @override
  void initState() {
    super.initState();
    _scrollController.addListener(_onScroll);
    _loadMuscleGroups();
    // Load initial exercises
    WidgetsBinding.instance.addPostFrameCallback((_) {
      ref.read(paginatedExercisesProvider.notifier).refresh();
    });
  }

  void _onScroll() {
    if (_scrollController.position.pixels >=
        _scrollController.position.maxScrollExtent - 200) {
      ref
          .read(paginatedExercisesProvider.notifier)
          .loadMore(
            muscleGroups: _selectedMuscleGroup != null
                ? [_selectedMuscleGroup!]
                : null,
          );
    }
  }

  Future<void> _loadMuscleGroups() async {
    setState(() {
      _loadingMuscles = true;
    });
    try {
      final svc = ref.read(exerciseServiceProvider);
      final muscles = await svc.getMuscles();
      final groups = muscles.map((m) => m.group).toSet().toList()..sort();
      setState(() {
        _muscleGroups = groups.cast<String>();

        if (_selectedMuscleGroup != null &&
            !_muscleGroups.contains(_selectedMuscleGroup)) {
          _selectedMuscleGroup = null;
        }
      });
    } catch (e) {
      if (mounted) {
        final l10n = AppLocalizations.of(context);
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(
              l10n.exerciseListErrorLoadingMuscleGroups(e.toString()),
            ),
          ),
        );
      }
    } finally {
      if (mounted)
        setState(() {
          _loadingMuscles = false;
        });
    }
  }

  void _onMuscleGroupChanged(String? group) {
    setState(() {
      _selectedMuscleGroup = group;
    });
    ref
        .read(paginatedExercisesProvider.notifier)
        .refresh(muscleGroups: group != null ? [group] : null);
  }

  void _showAddExerciseDialog() {
    final l10n = AppLocalizations.of(context);
    _clearForm();
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: Text(l10n.exerciseListAddExerciseTitle),
        content: SingleChildScrollView(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              TextField(
                controller: _nameController,
                decoration: InputDecoration(
                  labelText: l10n.exerciseListNameLabel,
                ),
              ),
              const SizedBox(height: 8),
              DropdownButtonFormField<String>(
                initialValue: _selectedMuscleGroup,
                isExpanded: true,
                decoration: InputDecoration(
                  labelText: l10n.exerciseListMuscleGroupLabel,
                ),
                hint: _loadingMuscles
                    ? Text(l10n.exerciseListLoading)
                    : Text(l10n.exerciseListSelectGroup),
                items: _muscleGroups
                    .map(
                      (g) => DropdownMenuItem<String>(value: g, child: Text(g)),
                    )
                    .toList(),
                onChanged: _onMuscleGroupChanged,
                validator: (val) {
                  if (_muscleGroups.isEmpty)
                    return l10n.exerciseListLoadingGroups;
                  if (val == null || val.isEmpty)
                    return l10n.exerciseListSelectMuscleGroupValidator;
                  return null;
                },
              ),
              TextField(
                controller: _equipmentController,
                decoration: InputDecoration(
                  labelText: l10n.exerciseListEquipmentLabel,
                ),
              ),
            ],
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: Text(l10n.cancel),
          ),
          TextButton(
            onPressed: () => _addExercise(),
            child: Text(l10n.exerciseListAddExerciseTitle),
          ),
        ],
      ),
    );
  }

  void _clearForm() {
    _nameController.clear();
    _equipmentController.clear();
    _selectedMuscleGroup = null;
  }

  Future<void> _addExercise() async {
    final l10n = AppLocalizations.of(context);
    if (_nameController.text.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(l10n.exerciseListEnterExerciseName)),
      );
      return;
    }
    if (_muscleGroups.isNotEmpty &&
        (_selectedMuscleGroup == null || _selectedMuscleGroup!.isEmpty)) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(l10n.exerciseListSelectMuscleGroupSnack)),
      );
      return;
    }
    try {
      final exerciseService = ref.read(exerciseServiceProvider);
      final exercise = ExerciseDefinition(
        name: _nameController.text,
        muscleGroup: _selectedMuscleGroup,
        equipment: _equipmentController.text.isEmpty
            ? null
            : _equipmentController.text,
      );
      await exerciseService.createExerciseDefinition(exercise);
      Navigator.pop(context);
      // Refresh the list
      ref
          .read(paginatedExercisesProvider.notifier)
          .refresh(
            muscleGroups: _selectedMuscleGroup != null
                ? [_selectedMuscleGroup!]
                : null,
          );
    } catch (e) {
      Navigator.pop(context);
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(l10n.exerciseListErrorGeneric(e.toString()))),
      );
    }
  }

  Future<void> _deleteExercise(int id) async {
    final l10n = AppLocalizations.of(context);
    try {
      final exerciseService = ref.read(exerciseServiceProvider);
      await exerciseService.deleteExerciseDefinition(id);
      // Refresh the list
      ref
          .read(paginatedExercisesProvider.notifier)
          .refresh(
            muscleGroups: _selectedMuscleGroup != null
                ? [_selectedMuscleGroup!]
                : null,
          );
    } catch (e) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(l10n.exerciseListErrorDeleting(e.toString()))),
      );
    }
  }

  @override
  void dispose() {
    _scrollController.dispose();
    _nameController.dispose();
    _equipmentController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    final exercisesState = ref.watch(paginatedExercisesProvider);

    return AssistantChatHost(
      contextBuilder: () async => {
        'screen': 'exercise_list',
        'entities': {
          'selected_muscle_group': _selectedMuscleGroup,
          'exercises_count': exercisesState.exercises.length,
        },
      },
      builder: (context, openChat) {
        return Scaffold(
          appBar: PrimaryAppBar(
            title: l10n.exerciseListTitle,
            onTitleTap: openChat,
            showBack: true,
          ),
          body: Column(
            children: [
              // Muscle group filter
              if (_muscleGroups.isNotEmpty)
                Container(
                  height: 60,
                  padding: const EdgeInsets.symmetric(vertical: 8),
                  child: ListView.builder(
                    scrollDirection: Axis.horizontal,
                    padding: const EdgeInsets.symmetric(horizontal: 16),
                    itemCount: _muscleGroups.length + 1,
                    itemBuilder: (context, index) {
                      if (index == 0) {
                        // "All" option
                        final isSelected = _selectedMuscleGroup == null;
                        return Padding(
                          padding: const EdgeInsets.only(right: 8),
                          child: FilterChip(
                            label: const Text('All'),
                            selected: isSelected,
                            onSelected: (selected) {
                              if (selected) _onMuscleGroupChanged(null);
                            },
                          ),
                        );
                      }

                      final group = _muscleGroups[index - 1];
                      final isSelected = _selectedMuscleGroup == group;
                      return Padding(
                        padding: const EdgeInsets.only(right: 8),
                        child: FilterChip(
                          label: Text(group),
                          selected: isSelected,
                          onSelected: (selected) {
                            if (selected) _onMuscleGroupChanged(group);
                          },
                        ),
                      );
                    },
                  ),
                ),
              Expanded(
                child: RefreshIndicator(
                  onRefresh: () async {
                    ref
                        .read(paginatedExercisesProvider.notifier)
                        .refresh(
                          muscleGroups: _selectedMuscleGroup != null
                              ? [_selectedMuscleGroup!]
                              : null,
                        );
                  },
                  child: _buildList(exercisesState, l10n),
                ),
              ),
            ],
          ),
          floatingActionButton: FloatingActionButton(
            onPressed: _showAddExerciseDialog,
            child: const Icon(Icons.add),
          ),
        );
      },
    );
  }

  Widget _buildList(PaginatedExercisesState state, AppLocalizations l10n) {
    if (state.exercises.isEmpty && state.isLoading) {
      return const LoadingIndicator();
    }

    if (state.exercises.isEmpty && !state.isLoading) {
      return EmptyState(
        icon: Icons.fitness_center,
        title: l10n.exerciseListEmpty,
        description: 'Try changing the filter or add a new exercise',
      );
    }

    return ListView.builder(
      controller: _scrollController,
      physics: const AlwaysScrollableScrollPhysics(),
      itemCount: state.exercises.length + (state.isLoading ? 1 : 0),
      itemBuilder: (context, index) {
        if (index == state.exercises.length) {
          return const Padding(
            padding: EdgeInsets.all(16),
            child: LoadingIndicator(),
          );
        }

        final exercise = state.exercises[index];
        return Card(
          margin: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
          child: ListTile(
            title: Text(
              exercise.name ?? '',
              style: const TextStyle(fontWeight: FontWeight.bold),
            ),
            subtitle: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                if (exercise.muscleGroup != null &&
                    exercise.muscleGroup!.isNotEmpty)
                  Text(
                    l10n.exerciseListMuscleGroupPrefix(exercise.muscleGroup!),
                  ),
                if (exercise.equipment != null &&
                    exercise.equipment!.isNotEmpty)
                  Text(l10n.exerciseListEquipmentPrefix(exercise.equipment!)),
              ],
            ),
            trailing: IconButton(
              icon: const Icon(Icons.delete_outline, color: Colors.red),
              onPressed: () async {
                final confirm = await showDialog<bool>(
                  context: context,
                  builder: (context) => AlertDialog(
                    title: Text(l10n.exerciseListDeleteExerciseTitle),
                    content: Text(l10n.exerciseListDeleteExerciseBody),
                    actions: [
                      TextButton(
                        onPressed: () => Navigator.pop(context, false),
                        child: Text(l10n.cancel),
                      ),
                      TextButton(
                        onPressed: () => Navigator.pop(context, true),
                        child: Text(
                          l10n.exerciseListDelete,
                          style: const TextStyle(color: Colors.red),
                        ),
                      ),
                    ],
                  ),
                );
                if (confirm == true && exercise.id != null) {
                  await _deleteExercise(exercise.id!);
                }
              },
            ),
            onTap: () {
              // TODO: Navigate to exercise details
            },
          ),
        );
      },
    );
  }
}
