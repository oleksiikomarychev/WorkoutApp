import 'dart:async';

import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:workout_app/models/exercise_list.dart';
import 'package:workout_app/models/exercise_instance.dart';
import 'package:workout_app/models/progression_template.dart';
import 'package:workout_app/models/user_max.dart';
import 'package:workout_app/services/progression_service.dart';
import 'package:workout_app/services/user_max_service.dart';
import 'package:workout_app/services/workout_service.dart';

class ExerciseFormScreen extends StatefulWidget {
  final int workoutId;
  final ExerciseList? exercise;
  final ExerciseInstance? instance;

  const ExerciseFormScreen({
    Key? key,
    required this.workoutId,
    this.exercise,
    this.instance,
  }) : super(key: key);

  @override
  _ExerciseFormScreenState createState() => _ExerciseFormScreenState();
}

class _ExerciseFormScreenState extends State<ExerciseFormScreen> {
  final _formKey = GlobalKey<FormState>();
  late TextEditingController _nameController;
  late TextEditingController _volumeController;
  late TextEditingController _weightController;
  late TextEditingController _intensityController;
  late TextEditingController _effortController;

  List<ProgressionTemplate> _templates = [];
  ProgressionTemplate? _selectedTemplate;
  List<UserMax> _userMaxes = [];
  UserMax? _selectedUserMax;
  bool _isLoading = false;
  bool _isLoadingMaxes = false;

  @override
  void initState() {
    super.initState();

    _nameController = TextEditingController();
    _volumeController = TextEditingController();
    _weightController = TextEditingController();
    _intensityController = TextEditingController();
    _effortController = TextEditingController();

    if (widget.exercise != null) {
      _nameController.text = widget.exercise!.name;
    } else if (widget.instance?.exerciseDefinition != null) {
      _nameController.text = widget.instance!.exerciseDefinition!.name;
    }

    if (widget.instance != null) {
      _volumeController.text = widget.instance!.volume.toString();
      _weightController.text = widget.instance!.weight?.toString() ?? '0';
      _intensityController.text = widget.instance!.intensity.toString();
      _effortController.text = widget.instance!.effort.toString();
    } else {
      _volumeController.text = '5';
      _weightController.text = '0';
      _intensityController.text = '70';
      _effortController.text = '7';
    }

    _loadData();
    final exerciseId = widget.exercise?.id ?? widget.instance?.exerciseListId;
    if (exerciseId != null) {
      _fetchUserMaxes(exerciseId);
    }
  }

  @override
  void dispose() {
    _nameController.dispose();
    _volumeController.dispose();
    _weightController.dispose();
    _intensityController.dispose();
    _effortController.dispose();
    super.dispose();
  }

  Future<void> _loadData() async {
    setState(() {
      _isLoading = true;
    });
    try {
      final progressionService = Provider.of<ProgressionService>(context, listen: false);
      final templates = await progressionService.getTemplates();
      if (mounted) {
        setState(() {
          _templates = templates;
        });
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Не удалось загрузить данные: $e')),
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

  Future<void> _fetchUserMaxes(int exerciseId) async {
    setState(() {
      _isLoadingMaxes = true;
    });
    final workoutService = Provider.of<WorkoutService>(context, listen: false);
    try {
      final maxes = await workoutService.getUserMaxesForExercise(exerciseId);
      if (mounted) {
        setState(() {
          _userMaxes = maxes;
          _isLoadingMaxes = false;
        });
      }
    } catch (e) {
      if (mounted) {
        setState(() {
          _isLoadingMaxes = false;
        });
        // Handle error appropriately
        debugPrint('Failed to load user maxes: $e');
      }
    }
  }

  Future<bool> _saveExercise() async {
    if (!_formKey.currentState!.validate()) {
      return false;
    }

    setState(() {
      _isLoading = true;
    });

    final workoutService = Provider.of<WorkoutService>(context, listen: false);
    final isUpdating = widget.instance != null;

    try {
      final volume = double.tryParse(_volumeController.text) ?? 0.0;
      final weight = double.tryParse(_weightController.text) ?? 0.0;
      final intensity = double.tryParse(_intensityController.text) ?? 0.0;
      final effort = double.tryParse(_effortController.text) ?? 0.0;

      if (isUpdating) {
        final updatedInstance = widget.instance!.copyWith(
          volume: volume.toInt(),
          weight: weight.toInt(),
          intensity: intensity.toInt(),
          effort: effort.toInt(),
        );
        await workoutService.updateExerciseInstance(updatedInstance);
      } else {
        await workoutService.createExerciseInstance(
          workoutId: widget.workoutId,
          exerciseListId: widget.exercise!.id!,
          volume: volume.toInt(),
          weight: weight.toInt(),
          intensity: intensity.toInt(),
          effort: effort.toInt(),
        );
      }

      if (mounted) {
        Navigator.of(context).pop(true);
      }
      return true;
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Ошибка сохранения: $e')),
        );
      }
      return false;
    } finally {
      if (mounted) {
        setState(() {
          _isLoading = false;
        });
      }
    }
  }

  void _calculateAndUpdateWeight() {
    if (_selectedTemplate != null && _selectedUserMax != null) {
      final intensity = _selectedTemplate!.intensity;
      final userMaxWeight = _selectedUserMax!.maxWeight;
      final currentIntensity = intensity ?? 0.0;
      final calculatedWeight = userMaxWeight * (currentIntensity / 100.0);
      _weightController.text = calculatedWeight.toStringAsFixed(2);
    }
  }

  Widget _buildTemplateDropdown() {
    return DropdownButtonFormField<ProgressionTemplate>(
      value: _selectedTemplate,
      decoration: const InputDecoration(
        labelText: 'Шаблон прогрессии (опционально)',
        border: OutlineInputBorder(),
      ),
      hint: const Text('Выберите шаблон'),
      isExpanded: true,
      items: [
        const DropdownMenuItem<ProgressionTemplate>(
          value: null,
          child: Text('Без шаблона'),
        ),
        ..._templates.map((template) {
          return DropdownMenuItem<ProgressionTemplate>(
            value: template,
            child: Text(template.name),
          );
        }).toList(),
      ],
      onChanged: (template) {
        setState(() {
          _selectedTemplate = template;
          if (template != null) {
            _volumeController.text = template.volume.toString();
            _intensityController.text = template.intensity.toString();
            _effortController.text = template.effort.toString();
            _calculateAndUpdateWeight();
          } else {
            _volumeController.text = '5';
            _intensityController.text = '70';
            _effortController.text = '7';
            _weightController.text = '0';
          }
        });
      },
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text(widget.instance == null ? 'Добавить упражнение' : 'Редактировать упражнение'),
        actions: [
          IconButton(
            icon: const Icon(Icons.save),
            onPressed: _isLoading ? null : () async {
              final result = await _saveExercise();
              if (result) {
                Navigator.of(context).pop(true);
              }
            },
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
                  children: <Widget>[
                    TextFormField(
                      controller: _nameController,
                      decoration: const InputDecoration(
                        labelText: 'Название упражнения',
                        border: OutlineInputBorder(),
                      ),
                      readOnly: true,
                    ),
                    const SizedBox(height: 16),
                    _buildTemplateDropdown(),
                    const SizedBox(height: 16),
                    if (_isLoadingMaxes)
                      const CircularProgressIndicator()
                    else if (_userMaxes.isNotEmpty)
                      DropdownButtonFormField<UserMax>(
                        value: _selectedUserMax,
                        hint: const Text('Select a User Max'),
                        items: _userMaxes.map((UserMax max) {
                          return DropdownMenuItem<UserMax>(
                            value: max,
                            child: Text('${widget.exercise?.name ?? widget.instance?.exerciseDefinition?.name ?? "Exercise"} - ${max.maxWeight} kg x ${max.repMax} reps'),
                          );
                        }).toList(),
                        onChanged: (UserMax? newValue) {
                          setState(() {
                            _selectedUserMax = newValue;
                          });
                        },
                        decoration: const InputDecoration(labelText: 'User Max'),
                      )
                    else
                      const Text('No user maxes found for this exercise.'),
                    const SizedBox(height: 24),
                    TextFormField(
                      controller: _volumeController,
                      decoration: const InputDecoration(
                        labelText: 'Объем (повторения)',
                        border: OutlineInputBorder(),
                      ),
                      keyboardType: TextInputType.number,
                      validator: (value) {
                        if (value == null || value.isEmpty) {
                          return 'Пожалуйста, введите объем';
                        }
                        if (int.tryParse(value) == null) {
                          return 'Пожалуйста, введите корректное число';
                        }
                        return null;
                      },
                    ),
                    const SizedBox(height: 16),
                    TextFormField(
                      controller: _weightController,
                      decoration: const InputDecoration(
                        labelText: 'Вес (кг)',
                        border: OutlineInputBorder(),
                      ),
                      keyboardType: const TextInputType.numberWithOptions(decimal: true),
                      validator: (value) {
                        if (value == null || value.isEmpty) {
                          return 'Пожалуйста, введите вес';
                        }
                        if (double.tryParse(value) == null) {
                          return 'Пожалуйста, введите корректное число';
                        }
                        return null;
                      },
                    ),
                    const SizedBox(height: 16),
                    TextFormField(
                      controller: _intensityController,
                      decoration: const InputDecoration(
                        labelText: 'Интенсивность (%)',
                        border: OutlineInputBorder(),
                      ),
                      keyboardType: const TextInputType.numberWithOptions(decimal: true),
                      validator: (value) {
                        if (value == null || value.isEmpty) {
                          return 'Пожалуйста, введите интенсивность';
                        }
                        if (double.tryParse(value) == null) {
                          return 'Пожалуйста, введите корректное число';
                        }
                        return null;
                      },
                    ),
                    const SizedBox(height: 16),
                    TextFormField(
                      controller: _effortController,
                      decoration: const InputDecoration(
                        labelText: 'Усилие (RPE)',
                        border: OutlineInputBorder(),
                      ),
                      keyboardType: TextInputType.number,
                      validator: (value) {
                        if (value == null || value.isEmpty) {
                          return 'Пожалуйста, введите усилие';
                        }
                        if (double.tryParse(value) == null) {
                          return 'Пожалуйста, введите корректное число';
                        }
                        return null;
                      },
                    ),
                    const SizedBox(height: 24),
                    SizedBox(
                      height: 50,
                      child: ElevatedButton(
                        onPressed: _isLoading ? null : () async {
                          final result = await _saveExercise();
                          if (result) {
                            Navigator.of(context).pop(true);
                          }
                        },
                        child: Text(
                          widget.instance == null ? 'ДОБАВИТЬ' : 'СОХРАНИТЬ',
                          style: const TextStyle(fontSize: 18),
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
