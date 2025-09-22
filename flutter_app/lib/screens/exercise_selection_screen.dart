import 'package:flutter/material.dart';
import '../models/exercise_definition.dart';
import '../screens/exercise_form_screen.dart';
import '../services/exercise_service.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:workout_app/services/service_locator.dart';

class ExerciseSelectionScreen extends ConsumerStatefulWidget {
  const ExerciseSelectionScreen({super.key});

  @override
  ConsumerState<ExerciseSelectionScreen> createState() => _ExerciseSelectionScreenState();
}

class _ExerciseSelectionScreenState extends ConsumerState<ExerciseSelectionScreen> {
  List<ExerciseDefinition> _exercises = [];
  List<ExerciseDefinition> _filteredExercises = [];
  bool _isLoading = true;
  final TextEditingController _searchController = TextEditingController();

  @override
  void initState() {
    super.initState();
    _loadExercises();
    _searchController.addListener(_filterExercises);
  }

  @override
  void dispose() {
    _searchController.dispose();
    super.dispose();
  }

  Future<void> _loadExercises() async {
    try {
      // Use correct service provider
      final exerciseService = ref.read(exerciseServiceProvider);
      final exercises = await exerciseService.getExerciseDefinitions();
      setState(() {
        _exercises = exercises;
        _filteredExercises = exercises;
        _isLoading = false;
      });
    } catch (e) {
      setState(() => _isLoading = false);
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Ошибка загрузки упражнений: $e')),
        );
      }
    }
  }

  void _filterExercises() {
    final query = _searchController.text.toLowerCase();
    setState(() {
      _filteredExercises = _exercises.where((exercise) {
        return exercise.name.toLowerCase().contains(query) ||
               (exercise.muscleGroup?.toLowerCase().contains(query) ?? false) ||
               (exercise.equipment?.toLowerCase().contains(query) ?? false);
      }).toList();
    });
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
                      'Выберите упражнение',
                      style: Theme.of(context).textTheme.titleLarge,
                      textAlign: TextAlign.center,
                    ),
                  ),
                  const SizedBox(width: 48), // To balance the BackButton
                ],
              ),
            ),
            Padding(
              padding: const EdgeInsets.all(8.0),
              child: TextField(
                controller: _searchController,
                decoration: InputDecoration(
                  labelText: 'Поиск упражнений',
                  prefixIcon: const Icon(Icons.search),
                  border: OutlineInputBorder(
                    borderRadius: BorderRadius.circular(10.0),
                  ),
                ),
              ),
            ),
            Expanded(
              child: _isLoading
                  ? const Center(child: CircularProgressIndicator())
                  : _filteredExercises.isEmpty
                      ? const Center(child: Text('Упражнения не найдены'))
                      : ListView.builder(
                          itemCount: _filteredExercises.length,
                          itemBuilder: (context, index) {
                            final exercise = _filteredExercises[index];
                            return ListTile(
                              title: Text(exercise.name),
                              subtitle: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  if (exercise.muscleGroup != null)
                                    Text('Группа мышц: ${exercise.muscleGroup}'),
                                  if (exercise.equipment != null)
                                    Text('Оборудование: ${exercise.equipment}'),
                                ],
                              ),
                              onTap: () => Navigator.of(context).pop(exercise),
                            );
                          },
                        ),
            ),
          ],
        ),
      ),
    );
  }
}
