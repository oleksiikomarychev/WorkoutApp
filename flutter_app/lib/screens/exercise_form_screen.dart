import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../models/exercise.dart';
import '../models/exercise_instance.dart';
import '../services/exercise_service.dart';
import '../services/workout_service.dart';

class ExerciseFormScreen extends StatefulWidget {
  final int workoutId;
  final Exercise? exercise;
  final ExerciseInstance? exerciseInstance;

  const ExerciseFormScreen({
    Key? key,
    required this.workoutId,
    this.exercise,
    this.exerciseInstance,
  }) : super(key: key);

  @override
  _ExerciseFormScreenState createState() => _ExerciseFormScreenState();
}

class _ExerciseFormScreenState extends State<ExerciseFormScreen> {
  final _formKey = GlobalKey<FormState>();
  bool _isLoading = false;
  
  // Controllers
  final _nameController = TextEditingController();
  final _descriptionController = TextEditingController();
  final _volumeController = TextEditingController();
  final _weightController = TextEditingController();
  final _intensityController = TextEditingController();
  final _effortController = TextEditingController();

  @override
  @override
  void initState() {
    super.initState();
    
    // If we're editing an existing exercise instance, use its values
    if (widget.exerciseInstance != null) {
      _volumeController.text = '${widget.exerciseInstance!.volume}';
      _weightController.text = '${widget.exerciseInstance!.weight ?? 0}';
      _intensityController.text = '${widget.exerciseInstance!.intensity}';
      _effortController.text = '${widget.exerciseInstance!.effort}';
      
      // If we don't have exercise data but have an instance, use its exercise ID
      if (widget.exercise == null && widget.exerciseInstance!.exerciseId != null) {
        _loadExerciseDetails(widget.exerciseInstance!.exerciseId!);
      }
    } else {
      // Default values for new exercise instances
      _volumeController.text = '5';
      _weightController.text = '0';
      _intensityController.text = '70';
      _effortController.text = '7';
    }
    
    // Set exercise name and description if available
    if (widget.exercise != null) {
      _nameController.text = widget.exercise!.name;
      _descriptionController.text = widget.exercise?.description ?? '';
    }
  }

  Future<void> _loadExerciseDetails(int exerciseId) async {
    try {
      final exerciseService = Provider.of<ExerciseService>(context, listen: false);
      final exercise = await exerciseService.getExercise(exerciseId);
      
      if (mounted) {
        setState(() {
          _nameController.text = exercise.name;
          _descriptionController.text = exercise.description ?? '';
        });
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Не удалось загрузить данные упражнения: $e')),
        );
      }
    }
  }

  @override
  void dispose() {
    _nameController.dispose();
    _descriptionController.dispose();
    _volumeController.dispose();
    _weightController.dispose();
    _intensityController.dispose();
    _effortController.dispose();
    super.dispose();
  }

  Future<void> _saveExercise() async {
    if (!_formKey.currentState!.validate()) return;
    if (widget.exercise == null) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Пожалуйста, выберите упражнение')),
        );
      }
      return;
    }

    setState(() {
      _isLoading = true;
    });

    try {
      final exerciseService = Provider.of<ExerciseService>(context, listen: false);
      
      // Create or update the exercise instance
      final exerciseInstance = ExerciseInstance(
        id: widget.exerciseInstance?.id,
        exerciseId: widget.exercise!.id!,
        workoutId: widget.workoutId,
        volume: int.tryParse(_volumeController.text) ?? 5,
        weight: int.tryParse(_weightController.text) ?? 0,
        intensity: int.tryParse(_intensityController.text) ?? 70,
        effort: int.tryParse(_effortController.text) ?? 7,
        notes: _descriptionController.text.isNotEmpty ? _descriptionController.text : null,
      );

      if (widget.exerciseInstance == null) {
        // Create new exercise instance
        await exerciseService.createExerciseInstance(exerciseInstance);
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(content: Text('Упражнение добавлено')),
          );
        }
      } else {
        // Update existing exercise instance
        await exerciseService.updateExerciseInstance(exerciseInstance);
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(content: Text('Изменения сохранены')),
          );
        }
      }

      if (mounted) {
        Navigator.of(context).pop(true);
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Ошибка: $e')),
        );
      }
    } finally {
      if (mounted) {
        setState(() {
          _isLoading = false;
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text(widget.exerciseInstance == null ? 'Добавить упражнение' : 'Редактировать упражнение'),
        actions: [
          IconButton(
            icon: const Icon(Icons.save),
            onPressed: _isLoading ? null : _saveExercise,
          ),
        ],
      ),
      body: _isLoading
          ? const Center(child: CircularProgressIndicator())
          : SingleChildScrollView(
              padding: const EdgeInsets.all(16.0),
              child: Form(
                key: _formKey,
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    // Exercise name field (read-only)
                    TextFormField(
                      controller: _nameController,
                      decoration: InputDecoration(
                        labelText: 'Упражнение',
                        suffixIcon: IconButton(
                          icon: const Icon(Icons.search),
                          onPressed: () {
                            // Navigate back to exercise selection
                            Navigator.pop(context);
                          },
                        ),
                        border: const OutlineInputBorder(),
                      ),
                      readOnly: true,
                      style: TextStyle(
                        color: Theme.of(context).primaryColor,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                    
                    const SizedBox(height: 16),
                    
                    // Exercise description
                    TextFormField(
                      controller: _descriptionController,
                      decoration: const InputDecoration(
                        labelText: 'Примечания',
                        hintText: 'Введите заметки по выполнению',
                        border: OutlineInputBorder(),
                      ),
                      maxLines: 3,
                    ),
                    
                    const SizedBox(height: 24),
                    const Text(
                      'Параметры подхода',
                      style: TextStyle(
                        fontSize: 18,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                    const SizedBox(height: 16),
                    
                    // Volume and weight row
                    Row(
                      children: [
                        // Volume field
                        Expanded(
                          child: TextFormField(
                            controller: _volumeController,
                            decoration: const InputDecoration(
                              labelText: 'Повторения',
                              border: OutlineInputBorder(),
                            ),
                            keyboardType: TextInputType.number,
                            validator: (value) {
                              if (value == null || value.isEmpty) {
                                return 'Укажите';
                              }
                              return null;
                            },
                          ),
                        ),
                        const SizedBox(width: 16),
                        // Weight field
                        Expanded(
                          child: TextFormField(
                            controller: _weightController,
                            decoration: const InputDecoration(
                              labelText: 'Вес (кг)',
                              border: OutlineInputBorder(),
                            ),
                            keyboardType: TextInputType.number,
                            validator: (value) {
                              if (value == null || value.isEmpty) {
                                return 'Укажите';
                              }
                              return null;
                            },
                          ),
                        ),
                      ],
                    ),
                    
                    const SizedBox(height: 16),
                    
                    // Intensity and effort row
                    Row(
                      children: [
                        // Intensity field
                        Expanded(
                          child: TextFormField(
                            controller: _intensityController,
                            decoration: const InputDecoration(
                              labelText: 'Интенсивность %',
                              border: OutlineInputBorder(),
                              suffixText: '%',
                            ),
                            keyboardType: TextInputType.number,
                            validator: (value) {
                              if (value == null || value.isEmpty) {
                                return 'Укажите';
                              }
                              final intensity = int.tryParse(value);
                              if (intensity == null || intensity < 0 || intensity > 100) {
                                return '0-100%';
                              }
                              return null;
                            },
                          ),
                        ),
                        const SizedBox(width: 16),
                        // Effort field
                        Expanded(
                          child: TextFormField(
                            controller: _effortController,
                            decoration: const InputDecoration(
                              labelText: 'Усилие (RPE)',
                              border: OutlineInputBorder(),
                              suffixText: '/10',
                            ),
                            keyboardType: const TextInputType.numberWithOptions(decimal: true),
                            validator: (value) {
                              if (value == null || value.isEmpty) {
                                return 'Укажите';
                              }
                              final effort = double.tryParse(value);
                              if (effort == null || effort < 1 || effort > 10) {
                                return '1-10';
                              }
                              return null;
                            },
                          ),
                        ),
                      ],
                    ),
                    
                    const SizedBox(height: 24),
                    
                    // Save button
                    SizedBox(
                      height: 50,
                      child: ElevatedButton(
                        onPressed: _isLoading ? null : _saveExercise,
                        style: ElevatedButton.styleFrom(
                          shape: RoundedRectangleBorder(
                            borderRadius: BorderRadius.circular(10),
                          ),
                        ),
                        child: _isLoading
                            ? const SizedBox(
                                width: 24,
                                height: 24,
                                child: CircularProgressIndicator(
                                  color: Colors.white,
                                  strokeWidth: 2,
                                ),
                              )
                            : Text(
                                widget.exercise == null ? 'ДОБАВИТЬ' : 'СОХРАНИТЬ',
                                style: const TextStyle(fontSize: 16),
                              ),
                      ),
                    ),
                  ],
                ),
              ),
            ),
    );
  }
}
