import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:intl/intl.dart';

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
  late Future<List<ProgressionTemplate>> _templatesFuture;
  late Future<List<UserMax>> _userMaxesFuture;
  bool _isLoading = false;
  final _formKey = GlobalKey<FormState>();
  UserMax? _selectedUserMax;
  final TextEditingController _nameController = TextEditingController();
  final TextEditingController _setsController = TextEditingController();
  final TextEditingController _intensityController = TextEditingController();
  final TextEditingController _effortController = TextEditingController(text: '8.0');
  final TextEditingController _notesController = TextEditingController();
  @override
  void initState() {
    super.initState();
    _loadData();
  }

  @override
  void dispose() {
    _nameController.dispose();
    _setsController.dispose();
    _intensityController.dispose();
    _effortController.dispose();
    _notesController.dispose();
    super.dispose();
  }

  void _loadData() {
    _templatesFuture = Provider.of<ProgressionService>(context, listen: false).getTemplates();
    _userMaxesFuture = Provider.of<UserMaxService>(context, listen: false).getUserMaxes();
  }
  void _resetForm() {
    _formKey.currentState?.reset();
    _nameController.clear();
    _setsController.clear();
    _intensityController.clear();
    _effortController.text = '8.0';
    _notesController.clear();
    _selectedUserMax = null;
  }

  Future<void> _showAddProgressionDialog() async {
    _resetForm();
    setState(() {
      _isLoading = true;
    });
    
    try {
      // Load user maxes if not already loaded
      final userMaxes = await _userMaxesFuture;
      if (userMaxes.isEmpty) {
        if (!mounted) return;
        
        setState(() {
          _isLoading = false;
        });
        
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('Сначала добавьте максимумы в разделе "Мои максимумы"'),
            duration: Duration(seconds: 3),
          ),
        );
        return;
      }
      
      // Select first user max by default
      _selectedUserMax = userMaxes.first;
      
      if (!mounted) return;
      
      // Show the add dialog
      final result = await showDialog<bool>(
        context: context,
        builder: (context) => AlertDialog(
          title: const Text('Новый шаблон прогрессии'),
          content: SingleChildScrollView(
            child: Form(
              key: _formKey,
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  TextFormField(
                    controller: _nameController,
                    decoration: const InputDecoration(
                      labelText: 'Название',
                      hintText: 'Введите название шаблона',
                      border: OutlineInputBorder(),
                    ),
                    validator: (value) {
                      if (value == null || value.isEmpty) {
                        return 'Пожалуйста, введите название';
                      }
                      return null;
                    },
                  ),
                  const SizedBox(height: 16),
                  DropdownButtonFormField<UserMax>(
                    value: _selectedUserMax,
                    decoration: const InputDecoration(
                      labelText: 'Максимум',
                      border: OutlineInputBorder(),
                    ),
                    items: userMaxes
                        .map((max) => DropdownMenuItem(
                              value: max,
                              child: Text(max.exerciseName),
                            ))
                        .toList(),
                    onChanged: (max) {
                      setState(() {
                        _selectedUserMax = max;
                      });
                    },
                    validator: (value) {
                      if (value == null) {
                        return 'Пожалуйста, выберите максимум';
                      }
                      return null;
                    },
                  ),
                  const SizedBox(height: 16),
                  Row(
                    children: [
                      Expanded(
                        child: TextFormField(
                          controller: _setsController,
                          decoration: const InputDecoration(
                            labelText: 'Подходы',
                            border: OutlineInputBorder(),
                          ),
                          keyboardType: TextInputType.number,
                          validator: (value) {
                            if (value == null || value.isEmpty) {
                              return 'Введите количество';
                            }
                            final sets = int.tryParse(value);
                            if (sets == null || sets <= 0) {
                              return 'Некорректное значение';
                            }
                            return null;
                          },
                        ),
                      ),
                      const SizedBox(width: 16),
                      Expanded(
                        child: TextFormField(
                          controller: _intensityController,
                          decoration: const InputDecoration(
                            labelText: 'Интенсивность, %',
                            hintText: '1-100',
                            border: OutlineInputBorder(),
                            suffixText: '%',
                          ),
                          keyboardType: TextInputType.number,
                          validator: (value) {
                            if (value == null || value.isEmpty) {
                              return 'Введите значение';
                            }
                            final intensity = int.tryParse(value);
                            if (intensity == null || intensity <= 0 || intensity > 100) {
                              return '1-100%';
                            }
                            return null;
                          },
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 16),
                  TextFormField(
                    controller: _effortController,
                    decoration: const InputDecoration(
                      labelText: 'Усилие (RPE)',
                      hintText: '1.0-10.0',
                      border: OutlineInputBorder(),
                    ),
                    keyboardType: const TextInputType.numberWithOptions(decimal: true),
                    validator: (value) {
                      if (value == null || value.isEmpty) {
                        return 'Введите значение';
                      }
                      final effort = double.tryParse(value);
                      if (effort == null || effort < 1.0 || effort > 10.0) {
                        return '1.0-10.0';
                      }
                      return null;
                    },
                  ),
                  const SizedBox(height: 16),
                  TextFormField(
                    controller: _notesController,
                    decoration: const InputDecoration(
                      labelText: 'Примечания (необязательно)',
                      border: OutlineInputBorder(),
                    ),
                    maxLines: 3,
                  ),
                ],
              ),
            ),
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(context, false),
              child: const Text('Отмена'),
            ),
            ElevatedButton(
              onPressed: () {
                if (_formKey.currentState?.validate() ?? false) {
                  Navigator.pop(context, true);
                }
              },
              child: const Text('Добавить'),
            ),
          ],
        ),
      );

      if (result == true) {
        await _addProgression();
      }
    } catch (e) {
      if (!mounted) return;
      
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Ошибка: $e')),
      );
    } finally {
      if (mounted) {
        setState(() {
          _isLoading = false;
        });
      }
    }
  }

  Future<void> _addProgression() async {
    if (!_formKey.currentState!.validate() || _selectedUserMax == null) return;
    
    setState(() {
      _isLoading = true;
    });
    
    try {
      final template = ProgressionTemplate(
        name: _nameController.text,
        userMaxId: _selectedUserMax!.id!,
        sets: int.parse(_setsController.text),
        intensity: int.parse(_intensityController.text),
        effort: double.parse(_effortController.text),
        notes: _notesController.text.isNotEmpty ? _notesController.text : null,
      );
      
      await Provider.of<ProgressionService>(context, listen: false)
          .createTemplate(template);
      
      if (!mounted) return;
      
      _loadData();
      
      if (mounted) {
        Navigator.of(context).pop();
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Шаблон создан')),
        );
      }
    } catch (e) {
      if (!mounted) return;
      
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Ошибка при создании: $e')),
      );
    } finally {
      if (mounted) {
        setState(() {
          _isLoading = false;
        });
      }
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
        title: const Text('Шаблоны прогрессий'),
        actions: [
          IconButton(
            icon: const Icon(Icons.add),
            onPressed: _showAddProgressionDialog,
          ),
          IconButton(
            icon: const Icon(Icons.info_outline),
            onPressed: () {
              showDialog(
                context: context,
                builder: (context) => AlertDialog(
                  title: const Text('О шаблонах прогрессий'),
                  content: const Text(
                    'Шаблоны прогрессий помогают создавать предустановки для ваших тренировок. '
                    'Создавайте шаблоны с разными параметрами интенсивности и усилия для разных целей тренировки.',
                  ),
                  actions: [
                    TextButton(
                      onPressed: () => Navigator.pop(context),
                      child: const Text('Понятно'),
                    ),
                  ],
                ),
              );
            },
          ),
        ],
      ),
      body: _isLoading
          ? const Center(child: CircularProgressIndicator())
          : FutureBuilder<List<ProgressionTemplate>>(
              future: _templatesFuture,
              builder: (context, snapshot) {
                if (snapshot.connectionState == ConnectionState.waiting) {
                  return const Center(child: CircularProgressIndicator());
                } else if (snapshot.hasError) {
                  return Center(
                    child: Text(
                      'Ошибка загрузки шаблонов: ${snapshot.error}',
                      style: const TextStyle(color: Colors.red),
                    ),
                  );
                } else if (!snapshot.hasData || snapshot.data!.isEmpty) {
                  return Center(
                    child: Column(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        Icon(
                          Icons.template_outlined,
                          size: 64,
                          color: Theme.of(context).colorScheme.primary.withOpacity(0.3),
                        ),
                        const SizedBox(height: 16),
                        Text(
                          'Нет шаблонов',
                          style: Theme.of(context).textTheme.titleLarge,
                        ),
                        const SizedBox(height: 8),
                        const Text(
                          'Создайте свой первый шаблон прогрессии',
                          style: TextStyle(color: Colors.grey),
                        ),
                        const SizedBox(height: 24),
                        ElevatedButton.icon(
                          onPressed: _showAddProgressionDialog,
                          icon: const Icon(Icons.add),
                          label: const Text('Создать шаблон'),
                        ),
                      ],
                    ),
                  );
                } else {
                  final templates = snapshot.data!;
                  return ListView.builder(
                    padding: const EdgeInsets.symmetric(vertical: 8),
                    itemCount: templates.length,
                    itemBuilder: (context, index) {
                      final template = templates[index];
                      final dateFormat = DateFormat('dd.MM.yyyy');
                      
                      return Card(
                        margin: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
                        child: Padding(
                          padding: const EdgeInsets.all(16.0),
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              // Template name and RPE indicator
                              Row(
                                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                                children: [
                                  Expanded(
                                    child: Text(
                                      template.name,
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
                                      color: _getRpeColor(template.effort),
                                      borderRadius: BorderRadius.circular(12),
                                    ),
                                    child: Text(
                                      'RPE ${template.effort.toStringAsFixed(1)}',
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
                              
                              // Main template metrics
                              Row(
                                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                                children: [
                                  _buildInfoItem('Подходы', '${template.sets} x'),
                                  _buildInfoItem('Повторения', '${template.volume ?? "-"}'),
                                  _buildInfoItem('Вес', '${template.calculatedWeight?.toStringAsFixed(1) ?? "-"} кг'),
                                  _buildInfoItem('Инт.', '${template.intensity}%'),
                                ],
                              ),
                              
                              // Notes and date
                              if (template.notes?.isNotEmpty ?? false) ...[
                                const SizedBox(height: 8),
                                Container(
                                  width: double.infinity,
                                  padding: const EdgeInsets.all(8),
                                  decoration: BoxDecoration(
                                    color: Colors.grey[100],
                                    borderRadius: BorderRadius.circular(8),
                                  ),
                                  child: Text(
                                    template.notes!,
                                    style: const TextStyle(fontSize: 14, color: Colors.black87),
                                  ),
                                ),
                              ],
                              
                              // Date and actions
                              const SizedBox(height: 12),
                              Row(
                                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                                children: [
                                  Text(
                                    'Создано: ${dateFormat.format(template.createdAt)}',
                                    style: const TextStyle(
                                      fontSize: 12,
                                      color: Colors.grey,
                                    ),
                                  ),
                                  Row(
                                    children: [
                                      IconButton(
                                        icon: const Icon(Icons.edit_outlined, size: 20),
                                        onPressed: () => _editProgression(template),
                                        padding: EdgeInsets.zero,
                                        constraints: const BoxConstraints(),
                                        tooltip: 'Редактировать',
                                      ),
                                      const SizedBox(width: 8),
                                      IconButton(
                                        icon: const Icon(Icons.delete_outline, size: 20, color: Colors.red),
                                        onPressed: () => _confirmDeleteProgression(template),
                                        padding: EdgeInsets.zero,
                                        constraints: const BoxConstraints(),
                                        tooltip: 'Удалить',
                                      ),
                                    ],
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
      floatingActionButton: FloatingActionButton.extended(
        onPressed: _showAddProgressionDialog,
        icon: const Icon(Icons.add),
        label: const Text('Добавить'),
        elevation: 2,
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
    if (intensity < 80) return Colors.green;
    if (intensity < 85) return Colors.lightGreen;
    if (intensity < 90) return Colors.orange;
    return Colors.red;
  }
  
  Future<void> _editProgression(ProgressionTemplate template) async {
    // Load the template data into the form
    _nameController.text = template.name;
    _setsController.text = template.sets.toString();
    _intensityController.text = template.intensity.toString();
    _effortController.text = template.effort.toStringAsFixed(1);
    _notesController.text = template.notes ?? '';
    
    // Find and set the selected user max
    try {
      final userMaxes = await _userMaxesFuture;
      _selectedUserMax = userMaxes.firstWhere((max) => max.id == template.userMaxId);
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Ошибка загрузки данных')),
      );
      return;
    }
    
    // Show the edit dialog
    final result = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Редактировать шаблон'),
        content: SingleChildScrollView(
          child: Form(
            key: _formKey,
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                TextFormField(
                  controller: _nameController,
                  decoration: const InputDecoration(
                    labelText: 'Название',
                    hintText: 'Введите название шаблона',
                  ),
                  validator: (value) {
                    if (value == null || value.isEmpty) {
                      return 'Пожалуйста, введите название';
                    }
                    return null;
                  },
                ),
                const SizedBox(height: 16),
                DropdownButtonFormField<UserMax>(
                  value: _selectedUserMax,
                  decoration: const InputDecoration(
                    labelText: 'Максимум',
                    border: OutlineInputBorder(),
                  ),
                  items: _userMaxesFuture.then((maxes) => maxes
                      .map((max) => DropdownMenuItem(
                            value: max,
                            child: Text(max.exerciseName),
                          ))
                      .toList()),
                  onChanged: (max) {
                    setState(() {
                      _selectedUserMax = max;
                    });
                  },
                  validator: (value) {
                    if (value == null) {
                      return 'Пожалуйста, выберите максимум';
                    }
                    return null;
                  },
                ),
                const SizedBox(height: 16),
                Row(
                  children: [
                    Expanded(
                      child: TextFormField(
                        controller: _setsController,
                        decoration: const InputDecoration(
                          labelText: 'Подходы',
                          border: OutlineInputBorder(),
                        ),
                        keyboardType: TextInputType.number,
                        validator: (value) {
                          if (value == null || value.isEmpty) {
                            return 'Введите количество';
                          }
                          final sets = int.tryParse(value);
                          if (sets == null || sets <= 0) {
                            return 'Некорректное значение';
                          }
                          return null;
                        },
                      ),
                    ),
                    const SizedBox(width: 16),
                    Expanded(
                      child: TextFormField(
                        controller: _intensityController,
                        decoration: const InputDecoration(
                          labelText: 'Интенсивность, %',
                          border: OutlineInputBorder(),
                          suffixText: '%',
                        ),
                        keyboardType: TextInputType.number,
                        validator: (value) {
                          if (value == null || value.isEmpty) {
                            return 'Введите значение';
                          }
                          final intensity = int.tryParse(value);
                          if (intensity == null || intensity <= 0 || intensity > 100) {
                            return '1-100%';
                          }
                          return null;
                        },
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 16),
                TextFormField(
                  controller: _effortController,
                  decoration: const InputDecoration(
                    labelText: 'Усилие (RPE)',
                    hintText: '1.0-10.0',
                    border: OutlineInputBorder(),
                  ),
                  keyboardType: const TextInputType.numberWithOptions(decimal: true),
                  validator: (value) {
                    if (value == null || value.isEmpty) {
                      return 'Введите значение';
                    }
                    final effort = double.tryParse(value);
                    if (effort == null || effort < 1.0 || effort > 10.0) {
                      return '1.0-10.0';
                    }
                    return null;
                  },
                ),
                const SizedBox(height: 16),
                TextFormField(
                  controller: _notesController,
                  decoration: const InputDecoration(
                    labelText: 'Примечания (необязательно)',
                    border: OutlineInputBorder(),
                  ),
                  maxLines: 3,
                ),
              ],
            ),
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context, false),
            child: const Text('Отмена'),
          ),
          ElevatedButton(
            onPressed: () {
              if (_formKey.currentState?.validate() ?? false) {
                Navigator.pop(context, true);
              }
            },
            child: const Text('Сохранить'),
          ),
        ],
      ),
    );

    if (result == true) {
      await _updateProgression(template);
    }
  }

  Future<void> _updateProgression(ProgressionTemplate template) async {
    if (!_formKey.currentState!.validate() || _selectedUserMax == null) return;
    
    setState(() {
      _isLoading = true;
    });
    
    try {
      final updatedTemplate = template.copyWith(
        name: _nameController.text,
        userMaxId: _selectedUserMax!.id!,
        sets: int.parse(_setsController.text),
        intensity: int.parse(_intensityController.text),
        effort: double.parse(_effortController.text),
        notes: _notesController.text.isNotEmpty ? _notesController.text : null,
      );
      
      await Provider.of<ProgressionService>(context, listen: false)
          .updateTemplate(updatedTemplate);
      
      if (!mounted) return;
      
      _loadData();
      
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Шаблон обновлен')),
      );
    } catch (e) {
      if (!mounted) return;
      
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Ошибка при обновлении: $e')),
      );
    } finally {
      if (mounted) {
        setState(() {
          _isLoading = false;
        });
      }
    }
  }

  Future<void> _confirmDeleteProgression(ProgressionTemplate template) async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Удалить шаблон?'),
        content: Text('Вы уверены, что хотите удалить шаблон "${template.name}"?'),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context, false),
            child: const Text('Отмена'),
          ),
          TextButton(
            onPressed: () => Navigator.pop(context, true),
            style: TextButton.styleFrom(
              foregroundColor: Theme.of(context).colorScheme.error,
            ),
            child: const Text('Удалить'),
          ),
        ],
      ),
    );

    if (confirmed == true) {
      try {
        setState(() {
          _isLoading = true;
        });
        
        await Provider.of<ProgressionService>(context, listen: false)
            .deleteTemplate(template.id!);
            
        if (!mounted) return;
        
        _loadData();
        
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Шаблон удален')),
        );
      } catch (e) {
        if (!mounted) return;
        
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Ошибка при удалении: $e')),
        );
      } finally {
        if (mounted) {
          setState(() {
            _isLoading = false;
          });
        }
      }
    }
  }
}
