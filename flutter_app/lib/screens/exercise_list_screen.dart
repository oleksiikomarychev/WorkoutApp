import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
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
  final TextEditingController _muscleGroupController = TextEditingController();
  final TextEditingController _equipmentController = TextEditingController();

  @override
  void initState() {
    super.initState();
    _loadExercises();
  }

  void _loadExercises() {
    _exercisesFuture = Provider.of<ExerciseService>(context, listen: false).getExerciseDefinitions();
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
              TextField(
                controller: _muscleGroupController,
                decoration: const InputDecoration(labelText: 'Группа мышц'),
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
    _muscleGroupController.clear();
    _equipmentController.clear();
  }

  Future<void> _addExercise() async {
    if (_nameController.text.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Введите название упражнения')),
      );
      return;
    }
    try {
      final exerciseService = Provider.of<ExerciseService>(context, listen: false);
      final exercise = ExerciseList(
        name: _nameController.text,
        muscleGroup: _muscleGroupController.text.isEmpty ? null : _muscleGroupController.text,
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
    _muscleGroupController.dispose();
    _equipmentController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Упражнения'),
      ),
      body: FutureBuilder<List<ExerciseList>>(
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
      floatingActionButton: FloatingActionButton(
        onPressed: _showAddExerciseDialog,
        child: const Icon(Icons.add),
      ),
    );
  }
}
