import 'dart:async';

import 'package:flutter/material.dart';
import 'package:workout_app/models/exercise_definition.dart';
import 'package:workout_app/models/exercise_instance.dart';
import 'package:workout_app/models/exercise_set_dto.dart';
import 'package:workout_app/models/progression_template.dart';
import 'package:workout_app/services/exercise_service.dart';
import 'package:workout_app/services/service_locator.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

class ExerciseFormScreen extends ConsumerStatefulWidget {
  final ExerciseDefinition exercise;
  final int workoutId;
  final ExerciseInstance? initialInstance;
  final int? defaultOrder;

  const ExerciseFormScreen({
    super.key,
    required this.exercise,
    required this.workoutId,
    this.initialInstance,
    this.defaultOrder,
  });

  @override
  ConsumerState<ExerciseFormScreen> createState() => _ExerciseFormScreenState();
}

class _ExerciseFormScreenState extends ConsumerState<ExerciseFormScreen> {
  final _formKey = GlobalKey<FormState>();
  late TextEditingController _nameController;
  late TextEditingController _muscleGroupController;

  final List<TextEditingController> _volumeControllers = [];
  final List<TextEditingController> _weightControllers = [];
  final List<ExerciseSetDto?> _existingSetDtos = [];


  List<String> _muscleGroups = [];
  String? _selectedMuscleGroup;

  List<ProgressionTemplate> _templates = [];
  ProgressionTemplate? _selectedTemplate;
  bool _isLoading = false;


  void _addSetRow({ExerciseSetDto? existing, String? volume, String? weight}) {
    final defaultReps = existing?.reps.toString() ?? '5';
    final defaultWeight = () {
      final val = existing?.weight ?? 0.0;
      return (val % 1 == 0)
          ? val.toStringAsFixed(0)
          : val.toStringAsFixed(1);
    }();
    final v = TextEditingController(text: volume ?? defaultReps);
    final w = TextEditingController(text: weight ?? defaultWeight);
    _volumeControllers.add(v);
    _weightControllers.add(w);
    _existingSetDtos.add(existing);
  }

  void _removeSetRow(int index) {
    if (index < 0 || index >= _volumeControllers.length) return;
    final v = _volumeControllers.removeAt(index);
    final w = _weightControllers.removeAt(index);
    _existingSetDtos.removeAt(index);
    v.dispose();
    w.dispose();
    setState(() {});
  }

  void _clearAllSetRows() {
    for (final c in _volumeControllers) { c.dispose(); }
    for (final c in _weightControllers) { c.dispose(); }
    _existingSetDtos.clear();
    _volumeControllers.clear();
    _weightControllers.clear();
  }

  @override
  void initState() {
    super.initState();

    _nameController = TextEditingController(text: widget.exercise.name);
    _muscleGroupController = TextEditingController(text: widget.exercise.muscleGroup ?? '');

    final existingSets = widget.initialInstance?.sets ?? [];
    if (existingSets.isNotEmpty) {
      for (final set in existingSets) {
        _addSetRow(existing: set);
      }
    } else {
      _addSetRow();
    }


    _selectedMuscleGroup = null;

    _loadData();
  }

  @override
  void dispose() {
    _nameController.dispose();
    _muscleGroupController.dispose();
    for (final c in _volumeControllers) { c.dispose(); }
    for (final c in _weightControllers) { c.dispose(); }
    super.dispose();
  }

  Future<void> _loadData() async {
    setState(() {
      _isLoading = true;
    });
    try {
      final exerciseService = ref.read(exerciseServiceProvider);

      final results = await Future.wait([
        exerciseService.getTemplates(),
        exerciseService.getMuscles(),
      ]);

      final templates = results[0] as List<ProgressionTemplate>;
      final muscles = results[1];


      final groups = Set<String>.from(muscles.map((m) => (m as dynamic).group as String));
      _muscleGroups = groups.toList()..sort();

      if (mounted) {
        setState(() {
          _templates = templates;

          final current = _muscleGroupController.text.trim();
          if (current.isNotEmpty) {
            String? match;
            for (final g in groups) {
              if (g.toLowerCase() == current.toLowerCase()) {
                match = g;
                break;
              }
            }
            _selectedMuscleGroup = match;
          } else {
            _selectedMuscleGroup = null;
          }
        });
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Failed to load data: $e')),
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

  Future<bool> _saveExercise() async {
    if (_formKey.currentState?.validate() ?? false) {
      setState(() {
        _isLoading = true;
      });

      try {
        final exerciseDef = widget.exercise;
        final exerciseListId = exerciseDef.id;
        if (exerciseListId == null) {
          throw Exception('Exercise definition id is required');
        }

        final sets = <ExerciseSetDto>[];
        for (int i = 0; i < _volumeControllers.length; i++) {
          final reps = int.tryParse(_volumeControllers[i].text.trim()) ?? 0;
          final weightRaw = _weightControllers[i].text.replaceAll(',', '.').trim();
          final weight = double.tryParse(weightRaw) ?? 0.0;
          final existing = _existingSetDtos[i];

          sets.add(ExerciseSetDto(
            id: existing?.id,
            reps: reps,
            weight: weight,
            rpe: existing?.rpe,
            order: existing?.order ?? i,
            exerciseInstanceId: existing?.exerciseInstanceId,
          ));
        }

        final newInstance = ExerciseInstance(
          id: widget.initialInstance?.id,
          workoutId: widget.initialInstance?.workoutId ?? widget.workoutId,
          exerciseListId: exerciseListId,
          exerciseDefinition: exerciseDef,
          userMaxId: widget.initialInstance?.userMaxId,
          sets: sets,
          notes: widget.initialInstance?.notes,
          order: widget.initialInstance?.order ?? widget.defaultOrder,
        );

        if (mounted) {
          Navigator.of(context).pop({
            'instance': newInstance,
            'isNew': widget.initialInstance == null,
            'refresh': true,
          });
        }
        return true;
      } catch (e) {
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(content: Text('Error saving: $e')),
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
    return false;
  }

  Widget _buildTemplateDropdown() {
    return DropdownButtonFormField<ProgressionTemplate>(
      initialValue: _selectedTemplate,
      decoration: const InputDecoration(
        labelText: 'Progression Template (optional)',
        border: OutlineInputBorder(),
      ),
      hint: const Text('Select template'),
      isExpanded: true,
      items: [
        const DropdownMenuItem<ProgressionTemplate>(
          value: null,
          child: Text('No template'),
        ),
        ..._templates.map((template) {
          return DropdownMenuItem<ProgressionTemplate>(
            value: template,
            child: Text(template.name),
          );
        }),
      ],
      onChanged: (template) {
        setState(() {
          _selectedTemplate = template;
          if (template != null) {

            if (_volumeControllers.isNotEmpty) {
              _volumeControllers.first.text = template.volume.toString();
            }

          } else {
            if (_volumeControllers.isNotEmpty) {
              _volumeControllers.first.text = '5';
            }
            if (_weightControllers.isNotEmpty) {
              _weightControllers.first.text = '0';
            }
          }
        });
      },
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: _isLoading
          ? const Center(child: CircularProgressIndicator())
          : SingleChildScrollView(
              padding: const EdgeInsets.all(16.0),
              child: Form(
                key: _formKey,
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    Text(
                      'Add Exercise',
                      style: Theme.of(context).textTheme.headlineSmall,
                      textAlign: TextAlign.center,
                    ),
                    const SizedBox(height: 24),
                    TextFormField(
                      controller: _nameController,
                      decoration: const InputDecoration(
                        labelText: 'Exercise Name',
                        border: OutlineInputBorder(),
                      ),
                      validator: (value) {
                        if (value == null || value.isEmpty) {
                          return 'Please enter a name';
                        }
                        return null;
                      },
                    ),
                    const SizedBox(height: 16),
                    DropdownButtonFormField<String>(
                      initialValue: _selectedMuscleGroup,
                      decoration: const InputDecoration(
                        labelText: 'Muscle Group',
                        border: OutlineInputBorder(),
                      ),
                      isExpanded: true,
                      hint: _muscleGroups.isEmpty
                          ? const Text('Loading...')
                          : const Text('Select group'),
                      items: _muscleGroups
                          .map((g) => DropdownMenuItem<String>(
                                value: g,
                                child: Text(g),
                              ))
                          .toList(),
                      onChanged: (val) {
                        setState(() {
                          _selectedMuscleGroup = val;
                          _muscleGroupController.text = val ?? '';
                        });
                      },
                      validator: (val) {
                        if (_muscleGroups.isEmpty) return 'Loading groups...';
                        if (val == null || val.isEmpty) {
                          return 'Please select a muscle group';
                        }
                        return null;
                      },
                    ),
                    const SizedBox(height: 16),
                    _buildTemplateDropdown(),
                    const SizedBox(height: 24),
                    const Text(
                      'Sets',
                      style: TextStyle(
                        fontSize: 18,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                    const SizedBox(height: 8),
                    ..._buildSetRows(),
                    const SizedBox(height: 16),
                    ElevatedButton.icon(
                      onPressed: () {
                        setState(() {
                          _addSetRow();
                        });
                      },
                      icon: const Icon(Icons.add),
                      label: const Text('Add Set'),
                    ),
                    const SizedBox(height: 16),
                    ElevatedButton.icon(
                      icon: const Icon(Icons.save),
                      label: const Text('Save Exercise'),
                      onPressed: _isLoading
                          ? null
                          : () async {
                              final result = await _saveExercise();
                              if (result) {
                                if (mounted) {
                                  Navigator.of(context).pop({'refresh': true});
                                }
                              }
                            },
                    ),
                  ],
                ),
              ),
            ),
    );
  }

  List<Widget> _buildSetRows() {
    return List<Widget>.generate(_volumeControllers.length, (index) {
      return Row(
        children: [
          Expanded(
            flex: 1,
            child: Padding(
              padding: const EdgeInsets.only(right: 8.0),
              child: TextFormField(
                controller: _weightControllers[index],
                decoration: const InputDecoration(
                  labelText: 'Weight (kg)',
                  border: OutlineInputBorder(),
                ),
                keyboardType: TextInputType.number,
                validator: (value) {
                  if (value == null || value.isEmpty) {
                    return 'Required';
                  }
                  return null;
                },
              ),
            ),
          ),
          Expanded(
            flex: 1,
            child: Padding(
              padding: const EdgeInsets.only(right: 8.0),
              child: TextFormField(
                controller: _volumeControllers[index],
                decoration: const InputDecoration(
                  labelText: 'Reps',
                  border: OutlineInputBorder(),
                ),
                keyboardType: TextInputType.number,
                validator: (value) {
                  if (value == null || value.isEmpty) {
                    return 'Required';
                  }
                  return null;
                },
              ),
            ),
          ),
          IconButton(
            icon: const Icon(Icons.delete, color: Colors.red),
            onPressed: _volumeControllers.length > 1
                ? () => _removeSetRow(index)
                : null,
          ),
        ],
      );
    });
  }
}
