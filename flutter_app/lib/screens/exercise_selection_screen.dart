import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../models/exercise_list.dart';
import '../screens/exercise_form_screen.dart';
import '../services/exercise_service.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';

class ExerciseSelectionScreen extends StatefulWidget {
  final int workoutId;
  
  const ExerciseSelectionScreen({Key? key, required this.workoutId}) : super(key: key);

  @override
  _ExerciseSelectionScreenState createState() => _ExerciseSelectionScreenState();
}

class _ExerciseSelectionScreenState extends State<ExerciseSelectionScreen> {
  final _storage = const FlutterSecureStorage();
  List<ExerciseList> _exercises = [];
  List<ExerciseList> _filteredExercises = [];
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
      final exerciseService = Provider.of<ExerciseService>(context, listen: false);
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
      appBar: AppBar(
        title: const Text('Выберите упражнение'),
        leading: IconButton(
          icon: const Icon(Icons.arrow_back),
          onPressed: () => Navigator.of(context).pop(null),
        ),
      ),
      body: Column(
        children: [
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
    );
  }
}
