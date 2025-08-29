import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:workout_app/config/constants/theme_constants.dart';
import 'package:workout_app/models/user_max.dart';
import 'package:workout_app/models/exercise_definition.dart';
import 'package:workout_app/providers/providers.dart';
import 'package:workout_app/widgets/empty_state.dart';
import 'package:workout_app/services/service_locator.dart';

class UserMaxesScreen extends ConsumerStatefulWidget {
  const UserMaxesScreen({super.key});

  @override
  ConsumerState<UserMaxesScreen> createState() => _UserMaxesScreenState();
}

class _UserMaxesScreenState extends ConsumerState<UserMaxesScreen> {
  bool _isLoading = false;
  List<UserMax> _userMaxes = [];
  String? _errorMessage;
  Map<int, ExerciseDefinition> _exerciseById = {};
  // Add form state for inline add dialog
  final _formKey = GlobalKey<FormState>();
  ExerciseDefinition? _selectedExercise;
  final TextEditingController _maxWeightController = TextEditingController();
  final TextEditingController _repMaxController = TextEditingController();

  @override
  void initState() {
    super.initState();
    _loadUserMaxes();
  }

  @override
  void dispose() {
    _maxWeightController.dispose();
    _repMaxController.dispose();
    super.dispose();
  }

  Future<void> _loadUserMaxes() async {
    if (!mounted) return;
    
    setState(() {
      _isLoading = true;
      _errorMessage = null;
    });
    
    try {
      // Get the UserMaxService from the provider
      final userMaxService = ref.read(userMaxServiceProvider);
      final exerciseService = ref.read(exerciseServiceProvider);
      
      // Fetch user maxes from the server
      final maxes = await userMaxService.getUserMaxes();

      // Fetch exercise definitions for the ids we have
      final ids = maxes.map((m) => m.exerciseId).toSet().toList();
      List<ExerciseDefinition> exercises = [];
      if (ids.isNotEmpty) {
        exercises = await exerciseService.getExercisesByIds(ids);
      }
      
      if (!mounted) return;
      
      setState(() {
        _userMaxes = maxes;
        _exerciseById = {for (final e in exercises) if (e.id != null) e.id!: e};
      });
    } catch (e) {
      debugPrint('Error loading user maxes: $e');
      
      if (!mounted) return;
      
      setState(() {
        _errorMessage = 'Не удалось загрузить ваши максимумы. Пожалуйста, проверьте подключение к серверу.';
      });
      
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(_errorMessage!),
            backgroundColor: Theme.of(context).colorScheme.error,
          ),
        );
      }
    } finally {
      if (mounted) {
        setState(() => _isLoading = false);
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: SafeArea(
        child: _buildBody(),
      ),
      floatingActionButton: FloatingActionButton(
        onPressed: _showAddUserMaxDialog,
        child: const Icon(Icons.add),
      ),
    );
  }

  Widget _buildBody() {
    if (_isLoading) {
      return const Center(child: CircularProgressIndicator());
    }

    if (_errorMessage != null) {
      return Center(
        child: Padding(
          padding: const EdgeInsets.all(16.0),
          child: Text(
            _errorMessage!,
            textAlign: TextAlign.center,
            style: const TextStyle(color: Colors.red),
          ),
        ),
      );
    }

    if (_userMaxes.isEmpty) {
      return const EmptyState(
        icon: Icons.leaderboard,
        title: 'Нет записей',
        description: 'Добавьте ваш первый максимум для отслеживания прогресса!',
      );
    }

    return ListView.builder(
      itemCount: _userMaxes.length,
      itemBuilder: (context, index) {
        final max = _userMaxes[index];
        final exerciseName = _exerciseById[max.exerciseId]?.name ?? 'Упражнение #${max.exerciseId}';
        return ListTile(
          title: Text(exerciseName),
          subtitle: Text('Макс. вес: ${max.maxWeight} кг x ${max.repMax} повтор.'),
        );
      },
    );
  }

  Future<void> _showAddUserMaxDialog() async {
    final exerciseService = ref.read(exerciseServiceProvider);
    List<ExerciseDefinition> exercises = [];
    try {
      exercises = await exerciseService.getExerciseDefinitions();
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Не удалось загрузить упражнения: $e')),
      );
      return;
    }

    if (exercises.isEmpty) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Сначала добавьте упражнения!')),
      );
      return;
    }

    _selectedExercise = exercises.first;
    _maxWeightController.clear();
    _repMaxController.clear();

    if (!mounted) return;
    await showDialog(
      context: context,
      builder: (ctx) => StatefulBuilder(
        builder: (context, setDialogState) => AlertDialog(
          title: const Text('Добавить максимум'),
          content: Form(
            key: _formKey,
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                DropdownButtonFormField<ExerciseDefinition>(
                  value: _selectedExercise,
                  decoration: const InputDecoration(labelText: 'Упражнение'),
                  items: exercises
                      .map((e) => DropdownMenuItem<ExerciseDefinition>(
                            value: e,
                            child: Text(e.name),
                          ))
                      .toList(),
                  onChanged: (val) => setDialogState(() => _selectedExercise = val),
                  validator: (val) => val == null ? 'Выберите упражнение' : null,
                ),
                TextFormField(
                  controller: _maxWeightController,
                  decoration: const InputDecoration(labelText: 'Вес (кг)'),
                  keyboardType: TextInputType.number,
                  validator: (value) {
                    if (value == null || value.isEmpty) return 'Введите вес';
                    final v = int.tryParse(value);
                    if (v == null || v <= 0) return 'Введите корректное число';
                    return null;
                  },
                ),
                TextFormField(
                  controller: _repMaxController,
                  decoration: const InputDecoration(labelText: 'Повторений максимум'),
                  keyboardType: TextInputType.number,
                  validator: (value) {
                    if (value == null || value.isEmpty) return 'Введите повторения';
                    final v = int.tryParse(value);
                    if (v == null || v <= 0 || v > 12) return '1..12';
                    return null;
                  },
                ),
              ],
            ),
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.of(ctx).pop(),
              child: const Text('Отмена'),
            ),
            ElevatedButton(
              onPressed: () async {
                if (!_formKey.currentState!.validate()) return;
                final userMaxService = ref.read(userMaxServiceProvider);
                final newMax = UserMax(
                  exerciseId: _selectedExercise!.id!,
                  maxWeight: int.parse(_maxWeightController.text),
                  repMax: int.parse(_repMaxController.text),
                );
                try {
                  await userMaxService.createUserMax(newMax);
                  if (!mounted) return;
                  Navigator.of(ctx).pop();
                  await _loadUserMaxes();
                } catch (e) {
                  if (!mounted) return;
                  Navigator.of(ctx).pop();
                  ScaffoldMessenger.of(context).showSnackBar(
                    SnackBar(content: Text('Ошибка: $e')),
                  );
                }
              },
              child: const Text('Добавить'),
            ),
          ],
        ),
      ),
    );
  }
}
