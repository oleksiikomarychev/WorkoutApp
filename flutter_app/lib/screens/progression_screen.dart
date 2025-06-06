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
  final TextEditingController _effortController = TextEditingController(text: '8'); // Default effort of 8
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
                    decoration: const InputDecoration(labelText: 'Усилие (1-10)'),
                    keyboardType: TextInputType.number,
                    validator: (value) {
                      if (value == null || value.isEmpty) return 'Введите значение';
                      final effort = int.tryParse(value);
                      if (effort == null || effort < 1 || effort > 10) {
                        return 'Введите целое число от 1 до 10';
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
        intensity: int.tryParse(_intensityController.text) ?? 75, // Default to 75% intensity if not provided
        effort: int.tryParse(_effortController.text) ?? 8, // Default to 8 if parsing fails
        volume: 1, // Set default volume to 1 to satisfy the schema validation
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
                      // Calculate total volume (sets * reps * weight)
                      final totalVolume = progression.calculatedWeight != null && progression.volume != null
                          ? (progression.sets * progression.volume! * progression.calculatedWeight!).toInt()
                          : 0;
                      
                      return Card(
                        margin: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
                        child: Padding(
                          padding: const EdgeInsets.all(16.0),
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              // Exercise name and max info
                              Row(
                                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                                children: [
                                  Expanded(
                                    child: Text(
                                      progression.userMaxDisplay ?? 'Прогрессия #${progression.id}',
                                      style: const TextStyle(
                                        fontSize: 18,
                                        fontWeight: FontWeight.bold,
                                      ),
                                      maxLines: 2,
                                      overflow: TextOverflow.ellipsis,
                                    ),
                                  ),
                                  // RPE indicator
                                  Container(
                                    padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                                    decoration: BoxDecoration(
                                      color: _getRpeColor(progression.effort?.toDouble() ?? 0),
                                      borderRadius: BorderRadius.circular(12),
                                    ),
                                    child: Text(
                                      'RPE ${progression.effort?.toStringAsFixed(1) ?? 'N/A'}',
                                      style: const TextStyle(
                                        color: Colors.white,
                                        fontWeight: FontWeight.bold,
                                        fontSize: 12,
                                      ),
                                    ),
                                  ),
                                ],
                              ),
                              const SizedBox(height: 12),
                              
                              // Main workout metrics
                              Row(
                                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                                children: [
                                  _buildInfoItem('Подходы', '${progression.sets} x'),
                                  _buildInfoItem('Повторения', '${progression.volume ?? "-"}'),
                                  _buildInfoItem('Вес', '${progression.calculatedWeight?.toStringAsFixed(1) ?? "-"} кг'),
                                  _buildInfoItem('Инт.', '${progression.intensity}%'),
                                ],
                              ),
                              const SizedBox(height: 8),
                              
                              // Intensity indicator
                              Container(
                                margin: const EdgeInsets.only(bottom: 8, top: 4),
                                height: 6,
                                decoration: BoxDecoration(
                                  color: Colors.grey[200],
                                  borderRadius: BorderRadius.circular(3),
                                ),
                                child: FractionallySizedBox(
                                  alignment: Alignment.centerLeft,
                                  widthFactor: (progression.intensity ?? 0) / 100.0,
                                  child: Container(
                                    decoration: BoxDecoration(
                                      color: _getIntensityColor(progression.intensity ?? 0),
                                      borderRadius: BorderRadius.circular(3),
                                    ),
                                  ),
                                ),
                              ),
                              const SizedBox(height: 4),
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
      crossAxisAlignment: CrossAxisAlignment.center,
      children: [
        Text(
          label,
          style: TextStyle(
            fontSize: 12,
            color: Colors.grey[600],
          ),
        ),
        const SizedBox(height: 2),
        Text(
          value,
          style: const TextStyle(
            fontSize: 16,
            fontWeight: FontWeight.w600,
          ),
        ),
      ],
    );
  }
  
  Color _getRpeColor(double rpe) {
    if (rpe <= 7) return Colors.green;
    if (rpe <= 8.5) return Colors.orange;
    return Colors.red;
  }
  
  Color _getIntensityColor(int intensity) {
    if (intensity < 60) return Colors.blue;
    if (intensity < 70) return Colors.green;
    if (intensity < 80) return Colors.lightGreen;
    if (intensity < 85) return Colors.yellow[700]!;
    if (intensity < 90) return Colors.orange;
    return Colors.red;
  }
}
