import 'dart:async';

import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:workout_app/models/exercise_definition.dart';
import 'package:workout_app/models/exercise_instance.dart';
import 'package:workout_app/models/exercise_set_dto.dart';
import 'package:workout_app/models/progression_template.dart';
import 'package:workout_app/models/user_max.dart';
import 'package:workout_app/services/progression_service.dart';
import 'package:workout_app/services/exercise_service.dart';
import 'package:workout_app/services/user_max_service.dart';
import 'package:workout_app/services/workout_service.dart';

class ExerciseFormScreen extends StatefulWidget {
  final int workoutId;
  final ExerciseDefinition? exercise;
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
  late TextEditingController _muscleGroupController;
  // Multiple set controllers
  final List<TextEditingController> _volumeControllers = [];
  final List<TextEditingController> _weightControllers = [];

  // Muscle group dropdown (loaded from backend enum)
  List<String> _muscleGroups = [];
  String? _selectedMuscleGroup;

  List<ProgressionTemplate> _templates = [];
  ProgressionTemplate? _selectedTemplate;
  List<UserMax> _userMaxes = [];
  UserMax? _selectedUserMax;
  bool _isLoading = false;
  bool _isLoadingMaxes = false;

  // Set helpers
  void _addSetRow({String volume = '5', String weight = '0'}) {
    final v = TextEditingController(text: volume);
    final w = TextEditingController(text: weight);
    _volumeControllers.add(v);
    _weightControllers.add(w);
  }

  void _removeSetRow(int index) {
    if (index < 0 || index >= _volumeControllers.length) return;
    final v = _volumeControllers.removeAt(index);
    final w = _weightControllers.removeAt(index);
    v.dispose();
    w.dispose();
    setState(() {});
  }

  void _clearAllSetRows() {
    for (final c in _volumeControllers) { c.dispose(); }
    for (final c in _weightControllers) { c.dispose(); }
    _volumeControllers.clear();
    _weightControllers.clear();
  }

  @override
  void initState() {
    super.initState();

    _nameController = TextEditingController();
    _muscleGroupController = TextEditingController();
    // initialize first set by default
    _addSetRow();

    if (widget.exercise != null) {
      _nameController.text = widget.exercise!.name;
      _muscleGroupController.text = widget.exercise!.muscleGroup ?? '';
    } else if (widget.instance?.exerciseDefinition != null) {
      _nameController.text = widget.instance!.exerciseDefinition!.name;
      _muscleGroupController.text = widget.instance!.exerciseDefinition?.muscleGroup ?? '';
    }

    // Defer selected value initialization until groups are loaded
    _selectedMuscleGroup = null;

    if (widget.instance != null) {
      // If instance has sets, populate all
      if (widget.instance!.sets.isNotEmpty) {
        // clear initial default
        _clearAllSetRows();
        for (final s in widget.instance!.sets) {
          _addSetRow(
            volume: (s.reps).toString(),
            weight: (s.weight).toString(),
          );
        }
      } else {
        // fallback from deprecated fields
        _volumeControllers.first.text = (widget.instance!.volume ?? 0).toString();
        _weightControllers.first.text = (widget.instance!.weight ?? 0).toString();
      }
    } else {
      _volumeControllers.first.text = '5';
      _weightControllers.first.text = '0';
    }

    _loadData();
    final exerciseId = widget.exercise?.id ?? widget.instance?.exerciseDefinitionId;
    if (exerciseId != null) {
      _fetchUserMaxes(exerciseId);
    }
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
      final progressionService = Provider.of<ProgressionService>(context, listen: false);
      final exerciseService = Provider.of<ExerciseService>(context, listen: false);

      // Fetch in parallel
      final results = await Future.wait([
        progressionService.getTemplates(),
        exerciseService.getMuscles(),
      ]);

      final templates = results[0] as List<ProgressionTemplate>;
      final muscles = results[1] as List<dynamic>; // MuscleInfo but we just need groups

      // Derive unique, sorted groups
      final groups = muscles
          .map((m) => (m as dynamic).group as String)
          .toSet()
          .toList()
        ..sort();

      if (mounted) {
        setState(() {
          _templates = templates;
          _muscleGroups = groups;
          // Initialize selected muscle group if existing value matches a group (case-insensitive, trimmed)
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
      // Build sets array from controllers
      final sets = <Map<String, int>>[];
      for (int i = 0; i < _volumeControllers.length; i++) {
        final volume = int.tryParse(_volumeControllers[i].text) ?? 0;
        final weight = int.tryParse(_weightControllers[i].text) ?? 0;
        sets.add({'weight': weight, 'volume': volume});
      }
      final int? userMaxId = _selectedUserMax?.id;

      if (isUpdating) {
        // Update the exercise definition if needed
        final updatedDefinition = (widget.instance?.exerciseDefinition ?? widget.exercise)?.copyWith(
          name: _nameController.text,
          muscleGroup: _muscleGroupController.text,
        );
        
        // Convert form sets to ExerciseSetDto objects
        final setDtos = sets.map((set) {
          final reps = int.tryParse(set['volume']?.toString() ?? '0') ?? 0;
          final weight = double.tryParse(set['weight']?.toString() ?? '0') ?? 0.0;
          
          return ExerciseSetDto(
            id: null, // Will be handled by the server
            reps: reps,
            weight: weight,
            volume: reps, // Set volume from reps for backward compatibility
          );
        }).toList();
        
        final updatedInstance = widget.instance!.copyWith(
          exerciseDefinition: updatedDefinition,
          sets: setDtos,
          userMaxId: userMaxId,
        );
        
        await workoutService.updateExerciseInstance(updatedInstance);
      } else {
        // Convert form sets to ExerciseSetDto objects
        final setDtos = sets.map((set) {
          final reps = int.tryParse(set['volume']?.toString() ?? '0') ?? 0;
          final weight = double.tryParse(set['weight']?.toString() ?? '0') ?? 0.0;
          
          return ExerciseSetDto(
            id: null, // Will be assigned by the server
            reps: reps,
            weight: weight,
            volume: reps, // Set volume from reps for backward compatibility
            // Include other set properties if available
          );
        }).toList();
        
        final newInstance = ExerciseInstance(
          id: 0, // Will be assigned by the server
          workoutId: widget.workoutId,
          exerciseListId: widget.exercise!.id!,
          sets: setDtos,
          userMaxId: userMaxId,
          order: 0, // Default order
          notes: null, // Optional field
          exerciseDefinition: widget.exercise, // Pass the exercise definition directly
        );
        
        await workoutService.createExerciseInstance(newInstance);
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

  void _calculateAndUpdateWeight() {
    if (_selectedTemplate != null && _selectedUserMax != null) {
      final intensity = _selectedTemplate!.intensity;
      final userMaxWeight = _selectedUserMax!.maxWeight;
      final currentIntensity = intensity ?? 0.0;
      final calculatedWeight = userMaxWeight * (currentIntensity / 100.0);
      if (_weightControllers.isNotEmpty) {
        _weightControllers.first.text = calculatedWeight.toStringAsFixed(0);
      }
    }
  }

  Widget _buildTemplateDropdown() {
    return DropdownButtonFormField<ProgressionTemplate>(
      value: _selectedTemplate,
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
        }).toList(),
      ],
      onChanged: (template) {
        setState(() {
          _selectedTemplate = template;
          if (template != null) {
            // autofill first set volume and intensity/effort
            if (_volumeControllers.isNotEmpty) {
              _volumeControllers.first.text = template.volume.toString();
            }
            _calculateAndUpdateWeight();
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
                      widget.instance == null ? 'Add Exercise' : 'Edit Exercise',
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
                      value: _selectedMuscleGroup,
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
                    const SizedBox(height: 16),
                    if (_isLoadingMaxes)
                      const LinearProgressIndicator()
                    else if (_userMaxes.isNotEmpty)
                      DropdownButtonFormField<UserMax>(
                        value: _selectedUserMax,
                        decoration: const InputDecoration(
                          labelText: 'Select Max (optional)',
                          border: OutlineInputBorder(),
                        ),
                        items: [
                          const DropdownMenuItem<UserMax>(
                            value: null,
                            child: Text('No max selected'),
                          ),
                        ],
                        onChanged: (max) {
                          setState(() {
                            _selectedUserMax = max;
                            if (max != null && _selectedTemplate != null) {
                              _calculateAndUpdateWeight();
                            }
                          });
                        },
                      ),
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
