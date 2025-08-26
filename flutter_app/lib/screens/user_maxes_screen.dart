import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:workout_app/config/constants/theme_constants.dart';
import 'package:workout_app/models/user_max.dart';
import 'package:workout_app/models/exercise_definition.dart';
import 'package:workout_app/providers/providers.dart';
import 'package:workout_app/widgets/empty_state.dart';
import 'package:workout_app/screens/user_max_screen.dart';
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

  @override
  void initState() {
    super.initState();
    _loadUserMaxes();
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
      appBar: AppBar(
        title: const Text('Мои максимумы'),
        centerTitle: true,
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: _loadUserMaxes,
            tooltip: 'Обновить',
          ),
        ],
      ),
      body: _buildBody(),
      floatingActionButton: FloatingActionButton(
        onPressed: () async {
          await Navigator.of(context).push(
            MaterialPageRoute(builder: (_) => const UserMaxScreen()),
          );
          if (mounted) {
            _loadUserMaxes();
          }
        },
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
}
