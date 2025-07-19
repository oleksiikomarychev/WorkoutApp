import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../models/user_max.dart';
import '../models/exercise_list.dart';
import '../services/user_max_service.dart';
import '../services/exercise_service.dart';

class UserMaxScreen extends StatefulWidget {
  const UserMaxScreen({Key? key}) : super(key: key);

  @override
  _UserMaxScreenState createState() => _UserMaxScreenState();
}

class _UserMaxScreenState extends State<UserMaxScreen> {
  late Future<List<UserMax>> _userMaxesFuture;
  late Future<List<ExerciseList>> _exercisesFuture;
  bool _isLoading = false;
  final _formKey = GlobalKey<FormState>();
  ExerciseList? _selectedExercise;
  final TextEditingController _maxWeightController = TextEditingController();
  final TextEditingController _repMaxController = TextEditingController();

  @override
  void initState() {
    super.initState();
    _loadData();
  }

  void _loadData() {
    _userMaxesFuture = Provider.of<UserMaxService>(context, listen: false).getUserMaxes();
    _exercisesFuture = Provider.of<ExerciseService>(context, listen: false).getExerciseDefinitions();
  }

  void _showAddUserMaxDialog() async {
    _resetForm();
    final exercises = await _exercisesFuture;
    if (exercises.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Сначала добавьте упражнения!')),
      );
      return;
    }
    if (!mounted) return;
    _selectedExercise = exercises.first;
    showDialog(
      context: context,
      builder: (context) => StatefulBuilder(
        builder: (context, setState) => AlertDialog(
          title: const Text('Добавить максимум'),
          content: Form(
            key: _formKey,
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                DropdownButtonFormField<ExerciseList>(
                  value: _selectedExercise,
                  decoration: const InputDecoration(labelText: 'Упражнение'),
                  items: exercises.map((e) => DropdownMenuItem<ExerciseList>(
                    value: e,
                    child: Text(e.name),
                  )).toList(),
                  onChanged: (value) {
                    setState(() {
                      _selectedExercise = value;
                    });
                  },
                  validator: (value) {
                    if (value == null) return 'Выберите упражнение';
                    return null;
                  },
                ),
                TextFormField(
                  controller: _maxWeightController,
                  decoration: const InputDecoration(labelText: 'Вес (кг)'),
                  keyboardType: TextInputType.number,
                  validator: (value) {
                    if (value == null || value.isEmpty) {
                      return 'Введите вес';
                    }
                    if (double.tryParse(value) == null) {
                      return 'Введите корректное число';
                    }
                    return null;
                  },
                ),
                TextFormField(
                  controller: _repMaxController,
                  decoration: const InputDecoration(labelText: 'Повторений максимум'),
                  keyboardType: TextInputType.number,
                  validator: (value) {
                    if (value == null || value.isEmpty) {
                      return 'Введите повторений максимум';
                    }
                    if (int.tryParse(value) == null) {
                      return 'Введите корректное число';
                    }
                    return null;
                  },
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
              onPressed: () {
                if (_formKey.currentState!.validate()) {
                  final newMax = UserMax(
                    exerciseId: _selectedExercise!.id!,
                    maxWeight: int.parse(_maxWeightController.text),
                    repMax: int.parse(_repMaxController.text),
                  );
                  Provider.of<UserMaxService>(context, listen: false).createUserMax(newMax).then((_) {
                    Navigator.pop(context);
                    setState(() {
                      _loadData();
                    });
                  }).catchError((e) {
                    Navigator.pop(context);
                    ScaffoldMessenger.of(context).showSnackBar(
                      SnackBar(content: Text('Ошибка: $e')),
                    );
                  });
                }
              },
              child: const Text('Добавить'),
            ),
          ],
        ),
      ),
    );
  }

  void _resetForm() {
    _selectedExercise = null;
    _maxWeightController.clear();
    _repMaxController.clear();
  }

  @override
  void dispose() {
    _maxWeightController.dispose();
    _repMaxController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Мои максимумы'),
      ),
      body: _isLoading
          ? const Center(child: CircularProgressIndicator())
          : FutureBuilder<List<UserMax>>(
              future: _userMaxesFuture,
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
                    child: Text('Нет максимумов. Добавьте новый!'),
                  );
                } else {
                  final userMaxes = snapshot.data!;
                  return FutureBuilder<List<ExerciseList>>(
                    future: _exercisesFuture,
                    builder: (context, exerciseSnapshot) {
                      final exercises = exerciseSnapshot.data ?? [];
                      final exercisesMap = {
                        for (var exercise in exercises) exercise.id: exercise
                      };
                      return ListView.builder(
                        itemCount: userMaxes.length,
                        itemBuilder: (context, index) {
                          final userMax = userMaxes[index];
                          final exercise = exercisesMap[userMax.exerciseId];
                          return ListTile(
                            title: Text(
                              exercise?.name ?? 'Упражнение #${userMax.exerciseId}',
                              style: const TextStyle(fontWeight: FontWeight.bold),
                            ),
                            subtitle: Text('Max: ${userMax.maxWeight}kg x ${userMax.repMax} reps'),
                            trailing: Row(
                              mainAxisSize: MainAxisSize.min,
                              children: [
                                IconButton(
                                  icon: const Icon(Icons.delete),
                                  onPressed: () async {
                                    final confirm = await showDialog<bool>(
                                      context: context,
                                      builder: (context) => AlertDialog(
                                        title: const Text('Удалить максимум?'),
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
                                    if (confirm == true && userMax.id != null) {
                                      try {
                                        final userMaxService = Provider.of<UserMaxService>(context, listen: false);
                                        await userMaxService.deleteUserMax(userMax.id!);
                                        setState(() {
                                          _loadData();
                                        });
                                      } catch (e) {
                                        ScaffoldMessenger.of(context).showSnackBar(
                                          SnackBar(content: Text('Ошибка удаления: $e')),
                                        );
                                      }
                                    }
                                  },
                                ),
                              ],
                            ),
                          );
                        },
                      );
                    },
                  );
                }
              },
            ),
      floatingActionButton: FloatingActionButton(
        onPressed: _showAddUserMaxDialog,
        child: const Icon(Icons.add),
      ),
    );
  }
}
