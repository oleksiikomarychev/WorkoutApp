import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:workout_app/models/muscle_info.dart';
import '../models/exercise_list.dart';
import '../services/exercise_service.dart';

class ExerciseListScreen extends StatefulWidget {
  const ExerciseListScreen({Key? key}) : super(key: key);

  @override
  _ExerciseListScreenState createState() => _ExerciseListScreenState();
}

class _ExerciseListScreenState extends State<ExerciseListScreen> {
  late Future<List<ExerciseList>> _exercisesFuture;
  final TextEditingController _nameController = TextEditingController();
  final TextEditingController _equipmentController = TextEditingController();
  // Muscles
  List<String> _muscleGroups = [];
  String? _selectedMuscleGroup;
  bool _loadingMuscles = false;

  @override
  void initState() {
    super.initState();
    _loadExercises();
    _loadMuscleGroups();
  }

  void _loadExercises() {
    _exercisesFuture = Provider.of<ExerciseService>(context, listen: false).getExerciseDefinitions();
  }

  Future<void> _loadMuscleGroups() async {
    setState(() { _loadingMuscles = true; });
    try {
      final svc = Provider.of<ExerciseService>(context, listen: false);
      final muscles = await svc.getMuscles();
      final groups = muscles.map((m) => m.group).toSet().toList()..sort();
      setState(() {
        _muscleGroups = groups;
        // Keep previous selection if still valid
        if (_selectedMuscleGroup != null && !_muscleGroups.contains(_selectedMuscleGroup)) {
          _selectedMuscleGroup = null;
        }
      });
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Ошибка загрузки групп мышц: $e')),
        );
      }
    } finally {
      if (mounted) setState(() { _loadingMuscles = false; });
    }
  }

  void _showAddExerciseDialog() {
    _clearForm();
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Добавить упражнение'),
        content: SingleChildScrollView(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              TextField(
                controller: _nameController,
                decoration: const InputDecoration(labelText: 'Название'),
              ),
              const SizedBox(height: 8),
              DropdownButtonFormField<String>(
                value: _selectedMuscleGroup,
                isExpanded: true,
                decoration: const InputDecoration(labelText: 'Группа мышц'),
                hint: _loadingMuscles
                    ? const Text('Загрузка...')
                    : const Text('Выберите группу'),
                items: _muscleGroups
                    .map((g) => DropdownMenuItem<String>(
                          value: g,
                          child: Text(g),
                        ))
                    .toList(),
                onChanged: (val) => setState(() { _selectedMuscleGroup = val; }),
                validator: (val) {
                  if (_muscleGroups.isEmpty) return 'Загрузка групп...';
                  if (val == null || val.isEmpty) return 'Выберите группу мышц';
                  return null;
                },
              ),
              TextField(
                controller: _equipmentController,
                decoration: const InputDecoration(labelText: 'Оборудование'),
              ),
            ],
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('Отмена'),
          ),
          TextButton(
            onPressed: () => _addExercise(),
            child: const Text('Добавить'),
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
    if (_nameController.text.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Введите название упражнения')),
      );
      return;
    }
    if (_muscleGroups.isNotEmpty && (_selectedMuscleGroup == null || _selectedMuscleGroup!.isEmpty)) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Выберите группу мышц')),
      );
      return;
    }
    try {
      final exerciseService = Provider.of<ExerciseService>(context, listen: false);
      final exercise = ExerciseList(
        name: _nameController.text,
        muscleGroup: _selectedMuscleGroup,
        equipment: _equipmentController.text.isEmpty ? null : _equipmentController.text,
      );
      await exerciseService.createExerciseDefinition(exercise);
      Navigator.pop(context);
      setState(() {
        _loadExercises();
      });
    } catch (e) {
      Navigator.pop(context);
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Ошибка: $e')),
      );
    }
  }

  Future<void> _deleteExercise(int id) async {
    try {
      final exerciseService = Provider.of<ExerciseService>(context, listen: false);
      await exerciseService.deleteExerciseDefinition(id);
      setState(() {
        _loadExercises();
      });
    } catch (e) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Ошибка удаления: $e')),
      );
    }
  }

  @override
  void dispose() {
    _nameController.dispose();
    _equipmentController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: SafeArea(
        child: Column(
          children: [
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 8.0),
              child: Row(
                children: [
                  const BackButton(),
                  Expanded(
                    child: Text(
                      'Упражнения',
                      style: Theme.of(context).textTheme.titleLarge,
                      textAlign: TextAlign.center,
                    ),
                  ),
                  const SizedBox(width: 48), // To balance the BackButton
                ],
              ),
            ),
            Expanded(
              child: FutureBuilder<List<ExerciseList>>(
                future: _exercisesFuture,
                builder: (context, snapshot) {
                  if (snapshot.connectionState == ConnectionState.waiting) {
                    return const Center(child: CircularProgressIndicator());
                  } else if (snapshot.hasError) {
                    return Center(
                      child: Text(
                        'Ошибка: ${snapshot.error}',
                        style: const TextStyle(color: Colors.red),
                      ),
                    );
                  } else if (!snapshot.hasData || snapshot.data!.isEmpty) {
                    return const Center(
                      child: Text('Нет упражнений. Добавьте новое!'),
                    );
                  } else {
                    final exercises = snapshot.data!;
                    return ListView.builder(
                      itemCount: exercises.length,
                      itemBuilder: (context, index) {
                        final exercise = exercises[index];
                        return Card(
                          margin: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
                          child: ListTile(
                            title: Text(
                              exercise.name,
                              style: const TextStyle(fontWeight: FontWeight.bold),
                            ),
                            subtitle: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                if (exercise.muscleGroup != null && exercise.muscleGroup!.isNotEmpty)
                                  Text('Группа мышц: ${exercise.muscleGroup}'),
                                if (exercise.equipment != null && exercise.equipment!.isNotEmpty)
                                  Text('Оборудование: ${exercise.equipment}'),
                                // Removed weight display as it's not part of ExerciseList model
                              ],
                            ),
                            trailing: IconButton(
                              icon: const Icon(Icons.delete),
                              onPressed: () async {
                                final confirm = await showDialog<bool>(
                                  context: context,
                                  builder: (context) => AlertDialog(
                                    title: const Text('Удалить упражнение?'),
                                    content: const Text('Это действие нельзя отменить.'),
                                    actions: [
                                      TextButton(
                                        onPressed: () => Navigator.pop(context, false),
                                        child: const Text('Отмена'),
                                      ),
                                      TextButton(
                                        onPressed: () => Navigator.pop(context, true),
                                        child: const Text('Удалить'),
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
                            },
                          ),
                        );
                      },
                    );
                  }
                },
              ),
            ),
          ],
        ),
      ),
      floatingActionButton: FloatingActionButton(
        onPressed: _showAddExerciseDialog,
        child: const Icon(Icons.add),
      ),
    );
  }
}
