import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../config/api_config.dart';
import '../models/exercise_definition.dart';
import '../models/user_max.dart';
import '../services/api_client.dart';
import '../services/service_locator.dart';
import 'exercise_selection_screen.dart';

class UserMaxWidget extends ConsumerStatefulWidget {
  const UserMaxWidget({super.key});

  @override
  ConsumerState<UserMaxWidget> createState() => _UserMaxWidgetState();
}

class _UserMaxWidgetState extends ConsumerState<UserMaxWidget> {
  final ApiClient _apiClient = ApiClient.create();
  ExerciseDefinition? _selectedExercise;
  final TextEditingController _weightController = TextEditingController();
  final TextEditingController _repsController = TextEditingController(text: '1');
  final GlobalKey<FormState> _formKey = GlobalKey<FormState>();
  bool _isSubmitting = false;

  @override
  void dispose() {
    _apiClient.dispose();
    _weightController.dispose();
    _repsController.dispose();
    super.dispose();
  }

  Future<void> _pickExercise() async {
    final exerciseService = ref.read(exerciseServiceProvider);
    await exerciseService.getExerciseDefinitions();
    if (!mounted) return;

    final selected = await Navigator.of(context).push<ExerciseDefinition>(
      MaterialPageRoute(
        builder: (_) => const ExerciseSelectionScreen(),
      ),
    );

    if (selected != null && mounted) {
      setState(() => _selectedExercise = selected);
    }
  }

  Future<void> _submit() async {
    if (!_formKey.currentState!.validate() || _selectedExercise == null) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Заполните все поля и выберите упражнение')),
      );
      return;
    }

    setState(() => _isSubmitting = true);
    try {
      final payload = {
        'exercise_id': _selectedExercise!.id,
        'exercise_name': _selectedExercise!.name,
        'max_weight': int.tryParse(_weightController.text),
        'rep_max': int.tryParse(_repsController.text) ?? 1,
      };
      await _apiClient.post(
        ApiConfig.createUserMaxEndpoint(),
        payload,
        context: 'UserMaxWidget',
      );
      if (mounted) {
        Navigator.of(context).pop(true);
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Не удалось сохранить максимум: $e')),
        );
      }
    } finally {
      if (mounted) setState(() => _isSubmitting = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return SafeArea(
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 16.0, vertical: 24.0),
        child: Form(
          key: _formKey,
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Center(
                child: Container(
                  width: 60,
                  height: 4,
                  decoration: BoxDecoration(
                    color: Colors.grey.shade400,
                    borderRadius: BorderRadius.circular(2),
                  ),
                ),
              ),
              const SizedBox(height: 16),
              Text(
                'Добавить максимум',
                style: Theme.of(context).textTheme.titleLarge,
              ),
              const SizedBox(height: 16),
              TextFormField(
                readOnly: true,
                decoration: InputDecoration(
                  labelText: 'Упражнение',
                  suffixIcon: IconButton(
                    icon: const Icon(Icons.search),
                    onPressed: _pickExercise,
                  ),
                ),
                controller: TextEditingController(text: _selectedExercise?.name ?? ''),
                onTap: _pickExercise,
                validator: (_) {
                  if (_selectedExercise == null) {
                    return 'Выберите упражнение';
                  }
                  return null;
                },
              ),
              const SizedBox(height: 16),
              TextFormField(
                controller: _weightController,
                keyboardType: TextInputType.number,
                decoration: const InputDecoration(
                  labelText: 'Вес (кг)',
                ),
                validator: (value) {
                  final weight = int.tryParse(value ?? '');
                  if (weight == null || weight <= 0) {
                    return 'Введите вес > 0';
                  }
                  return null;
                },
              ),
              const SizedBox(height: 16),
              TextFormField(
                controller: _repsController,
                keyboardType: TextInputType.number,
                decoration: const InputDecoration(
                  labelText: 'Повторения',
                ),
                validator: (value) {
                  final reps = int.tryParse(value ?? '');
                  if (reps == null || reps <= 0) {
                    return 'Введите количество повторений > 0';
                  }
                  if (reps > 12) {
                    return 'Максимум 12 повторений';
                  }
                  return null;
                },
              ),
              const SizedBox(height: 24),
              SizedBox(
                width: double.infinity,
                child: ElevatedButton.icon(
                  onPressed: _isSubmitting ? null : _submit,
                  icon: _isSubmitting
                      ? const SizedBox(
                          width: 16,
                          height: 16,
                          child: CircularProgressIndicator(strokeWidth: 2),
                        )
                      : const Icon(Icons.save),
                  label: Text(_isSubmitting ? 'Сохраняем...' : 'Сохранить максимум'),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
