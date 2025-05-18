import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../models/workout.dart';
import '../models/exercise.dart';
import '../services/workout_service.dart';
import '../services/exercise_service.dart';
class WorkoutDetailScreen extends StatefulWidget {
  final Workout? workout;
  const WorkoutDetailScreen({Key? key, this.workout}) : super(key: key);
  @override
  _WorkoutDetailScreenState createState() => _WorkoutDetailScreenState();
}
class _WorkoutDetailScreenState extends State<WorkoutDetailScreen> {
  final _formKey = GlobalKey<FormState>();
  late TextEditingController _nameController;
  late TextEditingController _descriptionController;
  bool _isLoading = false;
  List<Exercise> _exercises = [];
  bool _isLoadingExercises = false;
  @override
  void initState() {
    super.initState();
    _nameController = TextEditingController(text: widget.workout?.name ?? '');
    _descriptionController = TextEditingController(text: widget.workout?.description ?? '');
    if (widget.workout != null) {
      _loadExercises();
    }
  }
  Future<void> _loadExercises() async {
    setState(() {
      _isLoadingExercises = true;
    });
    try {
      final exerciseService = Provider.of<ExerciseService>(context, listen: false);
      final exercises = await exerciseService.getExercises();
      setState(() {
        _exercises = exercises.where((e) => e.workoutId == widget.workout!.id).toList();
      });
    } catch (e) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Ошибка загрузки упражнений: $e')),
      );
    } finally {
      setState(() {
        _isLoadingExercises = false;
      });
    }
  }
  @override
  void dispose() {
    _nameController.dispose();
    _descriptionController.dispose();
    super.dispose();
  }
  Future<void> _saveWorkout() async {
    if (!_formKey.currentState!.validate()) return;
    setState(() {
      _isLoading = true;
    });
    try {
      final workoutService = Provider.of<WorkoutService>(context, listen: false);
      final workout = Workout(
        id: widget.workout?.id,
        name: _nameController.text,
        description: _descriptionController.text.isEmpty ? null : _descriptionController.text,
        progressionTemplateId: widget.workout?.progressionTemplateId,
      );
      if (widget.workout == null) {
        await workoutService.createWorkout(workout);
      } else {
        await workoutService.updateWorkout(workout);
      }
      Navigator.pop(context);
    } catch (e) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Ошибка сохранения: $e')),
      );
    } finally {
      setState(() {
        _isLoading = false;
      });
    }
  }
  Future<void> _addExercise() async {
    if (widget.workout == null) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Сохраните тренировку перед добавлением упражнений')),
      );
      return;
    }
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Добавить упражнение'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Text('Здесь будет форма для создания упражнения'),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('Отмена'),
          ),
          TextButton(
            onPressed: () {
              Navigator.pop(context);
              _loadExercises();
            },
            child: const Text('Добавить'),
          ),
        ],
      ),
    );
  }
  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text(widget.workout == null ? 'Новая тренировка' : 'Редактировать тренировку'),
        actions: [
          if (widget.workout != null)
            IconButton(
              icon: const Icon(Icons.delete),
              onPressed: () async {
                final confirm = await showDialog<bool>(
                  context: context,
                  builder: (context) => AlertDialog(
                    title: const Text('Удалить тренировку?'),
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
                if (confirm == true) {
                  try {
                    final workoutService = Provider.of<WorkoutService>(context, listen: false);
                    await workoutService.deleteWorkout(widget.workout!.id!);
                    Navigator.pop(context);
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
      body: _isLoading
          ? const Center(child: CircularProgressIndicator())
          : SingleChildScrollView(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Form(
                    key: _formKey,
                    child: Column(
                      children: [
                        TextFormField(
                          controller: _nameController,
                          decoration: const InputDecoration(
                            labelText: 'Название',
                            border: OutlineInputBorder(),
                          ),
                          validator: (value) {
                            if (value == null || value.isEmpty) {
                              return 'Введите название тренировки';
                            }
                            return null;
                          },
                        ),
                        const SizedBox(height: 16),
                        TextFormField(
                          controller: _descriptionController,
                          decoration: const InputDecoration(
                            labelText: 'Описание',
                            border: OutlineInputBorder(),
                          ),
                          maxLines: 3,
                        ),
                        const SizedBox(height: 24),
                        ElevatedButton(
                          onPressed: _saveWorkout,
                          style: ElevatedButton.styleFrom(
                            minimumSize: const Size.fromHeight(50),
                          ),
                          child: Text(
                            widget.workout == null ? 'Создать тренировку' : 'Сохранить изменения',
                          ),
                        ),
                      ],
                    ),
                  ),
                  if (widget.workout != null) ...[
                    const SizedBox(height: 32),
                    Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      children: [
                        const Text(
                          'Упражнения',
                          style: TextStyle(
                            fontSize: 18,
                            fontWeight: FontWeight.bold,
                          ),
                        ),
                        ElevatedButton.icon(
                          onPressed: _addExercise,
                          icon: const Icon(Icons.add),
                          label: const Text('Добавить'),
                        ),
                      ],
                    ),
                    const SizedBox(height: 16),
                    _isLoadingExercises
                        ? const Center(child: CircularProgressIndicator())
                        : _exercises.isEmpty
                            ? const Center(
                                child: Text('Нет упражнений в этой тренировке'),
                              )
                            : ListView.builder(
                                shrinkWrap: true,
                                physics: const NeverScrollableScrollPhysics(),
                                itemCount: _exercises.length,
                                itemBuilder: (context, index) {
                                  final exercise = _exercises[index];
                                  return Card(
                                    margin: const EdgeInsets.only(bottom: 8),
                                    child: ListTile(
                                      title: Text(exercise.name),
                                      subtitle: Text(
                                        '${exercise.sets} подходов x ${exercise.reps} повторений' +
                                            (exercise.weight != null
                                                ? ' x ${exercise.weight} кг'
                                                : ''),
                                      ),
                                      trailing: IconButton(
                                        icon: const Icon(Icons.edit),
                                        onPressed: () {
                                        },
                                      ),
                                    ),
                                  );
                                },
                              ),
                  ],
                ],
              ),
            ),
    );
  }
}
