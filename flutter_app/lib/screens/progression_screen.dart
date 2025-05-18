import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../models/progression.dart';
import '../models/user_max.dart';
import '../services/progression_service.dart';
import '../services/user_max_service.dart';
class ProgressionScreen extends StatefulWidget {
  const ProgressionScreen({Key? key}) : super(key: key);
  @override
  _ProgressionScreenState createState() => _ProgressionScreenState();
}
class _ProgressionScreenState extends State<ProgressionScreen> {
  late Future<List<Progression>> _progressionsFuture;
  late Future<List<UserMax>> _userMaxesFuture;
  bool _isLoading = false;
  final _formKey = GlobalKey<FormState>();
  UserMax? _selectedUserMax;
  final TextEditingController _setsController = TextEditingController();
  final TextEditingController _intensityController = TextEditingController();
  final TextEditingController _effortController = TextEditingController();
  @override
  void initState() {
    super.initState();
    _loadData();
  }
  void _loadData() {
    _progressionsFuture = Provider.of<ProgressionService>(context, listen: false).getProgressions();
    _userMaxesFuture = Provider.of<UserMaxService>(context, listen: false).getUserMaxes();
  }
  void _showAddProgressionDialog() async {
    _resetForm();
    final userMaxes = await _userMaxesFuture;
    if (userMaxes.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Сначала добавьте максимумы!')),
      );
      return;
    }
    if (!mounted) return;
    _selectedUserMax = userMaxes.first;
    showDialog(
      context: context,
      builder: (context) => StatefulBuilder(
        builder: (context, setState) => AlertDialog(
          title: const Text('Добавить прогрессию'),
          content: Form(
            key: _formKey,
            child: SingleChildScrollView(
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  DropdownButtonFormField<UserMax>(
                    value: _selectedUserMax,
                    decoration: const InputDecoration(labelText: 'Максимум'),
                    items: userMaxes.map((e) => DropdownMenuItem(
                      value: e,
                      child: Text('${e.maxWeight} кг x ${e.repMax} ПМ'),
                    )).toList(),
                    onChanged: (value) {
                      setState(() {
                        _selectedUserMax = value;
                      });
                    },
                    validator: (value) {
                      if (value == null) return 'Выберите максимум';
                      return null;
                    },
                  ),
                  TextFormField(
                    controller: _setsController,
                    decoration: const InputDecoration(labelText: 'Количество подходов'),
                    keyboardType: TextInputType.number,
                    validator: (value) {
                      if (value == null || value.isEmpty) {
                        return 'Введите количество подходов';
                      }
                      if (int.tryParse(value) == null) {
                        return 'Введите целое число';
                      }
                      return null;
                    },
                  ),
                  TextFormField(
                    controller: _intensityController,
                    decoration: const InputDecoration(labelText: 'Интенсивность (%)'),
                    keyboardType: TextInputType.number,
                    validator: (value) {
                      if (value == null || value.isEmpty) {
                        return 'Введите интенсивность';
                      }
                      final intensity = double.tryParse(value);
                      if (intensity == null) {
                        return 'Введите корректное число';
                      }
                      if (intensity < 1 || intensity > 100) {
                        return 'Интенсивность должна быть от 1 до 100';
                      }
                      return null;
                    },
                  ),
                  TextFormField(
                    controller: _effortController,
                    decoration: const InputDecoration(labelText: 'RPE (1-10)'),
                    keyboardType: TextInputType.number,
                    validator: (value) {
                      if (value == null || value.isEmpty) {
                        return 'Введите значение RPE';
                      }
                      final effort = double.tryParse(value);
                      if (effort == null) {
                        return 'Введите корректное число';
                      }
                      if (effort < 1 || effort > 10) {
                        return 'RPE должно быть от 1 до 10';
                      }
                      return null;
                    },
                  ),
                ],
              ),
            ),
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(context),
              child: const Text('Отмена'),
            ),
            TextButton(
              onPressed: () => _addProgression(),
              child: const Text('Добавить'),
            ),
          ],
        ),
      ),
    );
  }
  void _resetForm() {
    _selectedUserMax = null;
    _setsController.clear();
    _intensityController.clear();
    _effortController.clear();
  }
  Future<void> _addProgression() async {
    if (!_formKey.currentState!.validate()) return;
    try {
      final progressionService = Provider.of<ProgressionService>(context, listen: false);
      final progression = Progression(
        userMaxId: _selectedUserMax!.id!,
        sets: int.parse(_setsController.text),
        intensity: double.parse(_intensityController.text),
        effort: double.parse(_effortController.text),
        volume: 0, 
      );
      await progressionService.createProgression(progression);
      Navigator.pop(context);
      setState(() {
        _loadData();
      });
    } catch (e) {
      Navigator.pop(context);
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Ошибка: $e')),
      );
    }
  }
  @override
  void dispose() {
    _setsController.dispose();
    _intensityController.dispose();
    _effortController.dispose();
    super.dispose();
  }
  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Прогрессии'),
      ),
      body: _isLoading
          ? const Center(child: CircularProgressIndicator())
          : FutureBuilder<List<Progression>>(
              future: _progressionsFuture,
              builder: (context, snapshot) {
                if (snapshot.connectionState == ConnectionState.waiting) {
                  return const Center(child: CircularProgressIndicator());
                } else if (snapshot.hasError) {
                  return Center(
                    child: Text(
                      'Ошибка: ${snapshot.error}',
                      style: const TextStyle(color: Colors.red),
                    ),
                  );
                } else if (!snapshot.hasData || snapshot.data!.isEmpty) {
                  return const Center(
                    child: Text('Нет прогрессий. Добавьте новую!'),
                  );
                } else {
                  final progressions = snapshot.data!;
                  return ListView.builder(
                    itemCount: progressions.length,
                    itemBuilder: (context, index) {
                      final progression = progressions[index];
                      return Card(
                        margin: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
                        child: Padding(
                          padding: const EdgeInsets.all(16.0),
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(
                                progression.userMaxDisplay ?? 'Прогрессия #${progression.id}',
                                style: const TextStyle(
                                  fontSize: 18,
                                  fontWeight: FontWeight.bold,
                                ),
                              ),
                              const SizedBox(height: 8),
                              Row(
                                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                                children: [
                                  _buildInfoItem('Подходы', '${progression.sets}'),
                                  _buildInfoItem('Интенсивность', '${progression.intensity}%'),
                                  _buildInfoItem('RPE', '${progression.effort}'),
                                ],
                              ),
                              const SizedBox(height: 8),
                              Row(
                                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                                children: [
                                  _buildInfoItem('Повторения', '${progression.reps ?? "N/A"}'),
                                  _buildInfoItem('Рабочий вес', '${progression.calculatedWeight ?? "N/A"} кг'),
                                  _buildInfoItem('Объем', '${progression.volume} КПШ'),
                                ],
                              ),
                              const SizedBox(height: 8),
                              Row(
                                mainAxisAlignment: MainAxisAlignment.end,
                                children: [
                                  IconButton(
                                    icon: const Icon(Icons.edit),
                                    onPressed: () {
                                    },
                                  ),
                                  IconButton(
                                    icon: const Icon(Icons.delete, color: Colors.red),
                                    onPressed: () async {
                                      final confirm = await showDialog<bool>(
                                        context: context,
                                        builder: (context) => AlertDialog(
                                          title: const Text('Удалить прогрессию?'),
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
                                      if (confirm == true && progression.id != null) {
                                        try {
                                          final progressionService = Provider.of<ProgressionService>(context, listen: false);
                                          await progressionService.deleteProgression(progression.id!);
                                          setState(() {
                                            _loadData();
                                          });
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
                            ],
                          ),
                        ),
                      );
                    },
                  );
                }
              },
            ),
      floatingActionButton: FloatingActionButton(
        onPressed: _showAddProgressionDialog,
        child: const Icon(Icons.add),
      ),
    );
  }
  Widget _buildInfoItem(String label, String value) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          label,
          style: const TextStyle(
            fontSize: 12,
            color: Colors.grey,
          ),
        ),
        Text(
          value,
          style: const TextStyle(
            fontSize: 16,
            fontWeight: FontWeight.bold,
          ),
        ),
      ],
    );
  }
}
