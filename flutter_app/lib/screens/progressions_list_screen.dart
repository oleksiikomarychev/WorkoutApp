import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../models/progression_template.dart';
import '../services/progression_service.dart';
import '../models/user_max.dart';
import '../services/user_max_service.dart';
import 'progression_detail_screen.dart';

class ProgressionsListScreen extends StatefulWidget {
  const ProgressionsListScreen({Key? key}) : super(key: key);

  @override
  _ProgressionsListScreenState createState() => _ProgressionsListScreenState();
}

class _ProgressionsListScreenState extends State<ProgressionsListScreen> {
  late Future<List<ProgressionTemplate>> _progressionsFuture;
  bool _isLoading = false;
  final TextEditingController _nameController = TextEditingController();
  final TextEditingController _intensityController = TextEditingController();
  final TextEditingController _effortController = TextEditingController();
  final TextEditingController _volumeController = TextEditingController();
  List<UserMax> _userMaxes = [];
  UserMax? _selectedUserMax;

  @override
  void initState() {
    super.initState();
    _loadProgressions();
    _loadUserMaxes();
  }

  Future<void> _loadProgressions() async {
    setState(() => _isLoading = true);
    try {
      final progressionService = Provider.of<ProgressionService>(context, listen: false);
      _progressionsFuture = progressionService.getTemplates();
      await _progressionsFuture;
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Ошибка загрузки прогрессий: $e')),
        );
      }
    } finally {
      if (mounted) {
        setState(() => _isLoading = false);
      }
    }
  }

  Future<void> _loadUserMaxes() async {
    try {
      final userMaxService = Provider.of<UserMaxService>(context, listen: false);
      final maxes = await userMaxService.getUserMaxes();
      if (mounted) {
        setState(() {
          _userMaxes = maxes;
        });
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Failed to load user maxes: $e')),
        );
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Прогрессии'),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: _isLoading ? null : _loadProgressions,
          ),
        ],
      ),
      body: _isLoading
          ? const Center(child: CircularProgressIndicator())
          : FutureBuilder<List<ProgressionTemplate>>(
              future: _progressionsFuture,
              builder: (context, snapshot) {
                if (snapshot.connectionState == ConnectionState.waiting) {
                  return const Center(child: CircularProgressIndicator());
                }

                if (snapshot.hasError) {
                  return Center(child: Text('Ошибка: ${snapshot.error}'));
                }

                final progressions = snapshot.data ?? [];

                if (progressions.isEmpty) {
                  return Center(
                    child: Column(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        const Icon(
                          Icons.timeline_outlined,
                          size: 64,
                          color: Colors.grey,
                        ),
                        const SizedBox(height: 16),
                        Text(
                          'Нет сохраненных прогрессий',
                          style: Theme.of(context).textTheme.titleMedium?.copyWith(
                            color: Colors.grey,
                          ),
                        ),
                        const SizedBox(height: 8),
                        ElevatedButton.icon(
                          onPressed: _loadProgressions,
                          icon: const Icon(Icons.refresh),
                          label: const Text('Обновить'),
                        ),
                      ],
                    ),
                  );
                }

                return ListView.builder(
                  itemCount: progressions.length,
                  itemBuilder: (context, index) {
                    final progression = progressions[index];
                    return Card(
                      margin: const EdgeInsets.symmetric(
                        horizontal: 16,
                        vertical: 8,
                      ),
                      child: ListTile(
                        title: Text(progression.name),
                        subtitle: Text(
                          'Интенсивность: ${progression.intensity}%\n'
                          'Усилие: ${progression.effort}\n'
                          'Объем: ${progression.volume ?? 'Не указан'} повторений',
                        ),
                        trailing: IconButton(
                          icon: const Icon(Icons.info),
                          onPressed: () {
                            Navigator.push(
                              context,
                              MaterialPageRoute(
                                builder: (context) => ProgressionDetailScreen(
                                  templateId: progression.id!,
                                ),
                              ),
                            );
                          },
                        ),
                      ),
                    );
                  },
                );
              },
            ),
      floatingActionButton: FloatingActionButton(
        onPressed: _showAddProgressionDialog,
        child: const Icon(Icons.add),
      ),
    );
  }

  void _showAddProgressionDialog() {
    _nameController.clear();
    _intensityController.clear();
    _effortController.clear();
    _volumeController.clear();
    setState(() {
      _selectedUserMax = null;
    });

    showDialog(
      context: context,
      builder: (context) {
        // Use a StatefulWidget for the dialog's content to manage its own state
        return StatefulBuilder(
          builder: (context, setDialogState) {
            return AlertDialog(
              title: const Text('Добавить прогрессию'),
              content: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  TextField(
                    controller: _nameController,
                    decoration: const InputDecoration(labelText: 'Название прогрессии'),
                  ),
                  const SizedBox(height: 16),
                  if (_userMaxes.isNotEmpty)
                    DropdownButtonFormField<UserMax>(
                      value: _selectedUserMax,
                      hint: const Text('Выберите максимум'),
                      isExpanded: true,
                      items: _userMaxes.map((UserMax max) {
                        return DropdownMenuItem<UserMax>(
                          value: max,
                          child: Text('Упражнение ${max.exerciseId} - ${max.maxWeight}kg'),
                        );
                      }).toList(),
                      onChanged: (UserMax? newValue) {
                        setDialogState(() {
                          _selectedUserMax = newValue;
                        });
                      },
                      validator: (value) => value == null ? 'Выберите максимум' : null,
                    )
                  else
                    const Text('Сначала создайте пользовательский максимум'),
                  const SizedBox(height: 16),
                  TextField(
                    controller: _intensityController,
                    keyboardType: TextInputType.number,
                    decoration: const InputDecoration(
                      labelText: 'Интенсивность (1-100)',
                      hintText: 'Введите число от 1 до 100',
                    ),
                  ),
                  const SizedBox(height: 16),
                  TextField(
                    controller: _effortController,
                    keyboardType: TextInputType.number,
                    decoration: const InputDecoration(
                      labelText: 'Усилие (1-10)',
                      hintText: 'Введите число от 1 до 10',
                    ),
                  ),
                  const SizedBox(height: 16),
                  TextField(
                    controller: _volumeController,
                    keyboardType: TextInputType.number,
                    decoration: const InputDecoration(
                      labelText: 'Объем (повторения)',
                      hintText: 'Введите количество повторений',
                    ),
                  ),
                ],
              ),
              actions: [
                TextButton(
                  onPressed: () => Navigator.pop(context),
                  child: const Text('Отмена'),
                ),
                TextButton(
                  onPressed: () async {
                    final name = _nameController.text.trim();
                    if (name.isEmpty || _selectedUserMax == null) {
                      ScaffoldMessenger.of(context).showSnackBar(
                        const SnackBar(content: Text('Заполните все поля')),
                      );
                      return;
                    }

                    final intensity = int.tryParse(_intensityController.text);
                    if (intensity == null || intensity < 1 || intensity > 100) {
                      ScaffoldMessenger.of(context).showSnackBar(
                        const SnackBar(content: Text('Интенсивность должна быть числом от 1 до 100')),
                      );
                      return;
                    }

                    final effort = int.tryParse(_effortController.text);
                    if (effort == null || effort < 1 || effort > 10) {
                      ScaffoldMessenger.of(context).showSnackBar(
                        const SnackBar(content: Text('Усилие должно быть числом от 1 до 10')),
                      );
                      return;
                    }

                    final volumeStr = _volumeController.text;
                    int? volume;
                    if (volumeStr.isEmpty) {
                      volume = null;
                    } else {
                      final parsedVolume = int.tryParse(volumeStr);
                      if (parsedVolume == null) {
                        ScaffoldMessenger.of(context).showSnackBar(
                          const SnackBar(content: Text('Объем должен быть числом')),
                        );
                        return;
                      }
                      volume = parsedVolume;
                      if (volume < 1) {
                        ScaffoldMessenger.of(context).showSnackBar(
                          const SnackBar(content: Text('Объем должен быть числом больше или равным 1')),
                        );
                        return;
                      }
                    }

                    try {
                      final progressionService = Provider.of<ProgressionService>(context, listen: false);
                      final progression = ProgressionTemplate(
                        id: 0, // Server will assign ID
                        name: name,
                        user_max_id: _selectedUserMax!.id!,
                        intensity: intensity,
                        effort: effort,
                        volume: volume, // Pass the volume as is, it's already properly validated
                      );
                      await progressionService.createTemplate(progression);
                      Navigator.pop(context);
                      setState(() {
                        _loadProgressions();
                      });
                    } catch (e) {
                      ScaffoldMessenger.of(context).showSnackBar(
                        SnackBar(content: Text('Ошибка: $e')),
                      );
                    }
                  },
                  child: const Text('Добавить'),
                ),
              ],
            );
          },
        );
      },
    );
  }

  @override
  void dispose() {
    _nameController.dispose();
    _intensityController.dispose();
    _effortController.dispose();
    _volumeController.dispose();
    super.dispose();
  }
}
