import 'package:flutter/material.dart';
import 'package:workout_app/src/api/nutrition_api.dart';
import 'package:workout_app/widgets/primary_app_bar.dart';
import 'package:workout_app/widgets/assistant_chat_host.dart';
import 'package:workout_app/widgets/loading_indicator.dart';

class NutritionPlanCreate extends StatefulWidget {
  final Map<String, dynamic>? initialPlan;

  const NutritionPlanCreate({super.key, this.initialPlan});

  @override
  State<NutritionPlanCreate> createState() => _NutritionPlanCreateState();
}

class _NutritionPlanCreateState extends State<NutritionPlanCreate> {
  final _formKey = GlobalKey<FormState>();
  final _sessionIdController = TextEditingController(
    text: DateTime.now().millisecondsSinceEpoch.toString(),
  );
  final _userIdController = TextEditingController(text: '1');
  final _workoutIdController = TextEditingController();
  final _appliedPlanWorkoutIdController = TextEditingController();

  List<Map<String, dynamic>> _foodList = [];
  List<Map<String, dynamic>> _supplementList = [];
  List<Map<String, dynamic>> _medicationList = [];
  List<Map<String, dynamic>> _selectedEntries = [];

  bool _isLoading = false;
  bool _isLoadingItems = false;
  DateTime _selectedDate = DateTime.now();

  @override
  void initState() {
    super.initState();
    _loadItems();
    if (widget.initialPlan != null) {
      _sessionIdController.text = widget.initialPlan!['session_id'] ?? '';
      _userIdController.text =
          widget.initialPlan!['user_id']?.toString() ?? '1';
      _workoutIdController.text =
          widget.initialPlan!['workout_id']?.toString() ?? '';
      _appliedPlanWorkoutIdController.text =
          widget.initialPlan!['applied_plan_workout_id']?.toString() ?? '';
      if (widget.initialPlan!['date'] != null) {
        _selectedDate = DateTime.parse(widget.initialPlan!['date']);
      }
      _selectedEntries = List<Map<String, dynamic>>.from(
        widget.initialPlan!['entries'] ?? [],
      );
    }
  }

  @override
  void dispose() {
    _sessionIdController.dispose();
    _userIdController.dispose();
    _workoutIdController.dispose();
    _appliedPlanWorkoutIdController.dispose();
    super.dispose();
  }

  Future<void> _loadItems() async {
    setState(() {
      _isLoadingItems = true;
    });

    try {
      final food = await NutritionApi.getAllFood();
      final supplements = await NutritionApi.getAllSupplements();
      final medications = await NutritionApi.getAllMedications();

      if (mounted) {
        setState(() {
          _foodList = food;
          _supplementList = supplements;
          _medicationList = medications;
          _isLoadingItems = false;
        });
      }
    } catch (e) {
      if (mounted) {
        setState(() {
          _isLoadingItems = false;
        });
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Error loading items: $e'),
            backgroundColor: Colors.red,
          ),
        );
      }
    }
  }

  void _addEntry(Map<String, dynamic> item, String type) async {
    final dosageController = TextEditingController(
      text: item['dosage']?.toString() ?? '',
    );

    final result = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: Text('Add ${item['name'] ?? 'Item'}'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            TextField(
              controller: dosageController,
              decoration: InputDecoration(
                labelText: 'Dosage (${item['unit'] ?? ''})',
                hintText: item['dosage']?.toString(),
              ),
              keyboardType: TextInputType.number,
            ),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context, false),
            child: const Text('Cancel'),
          ),
          TextButton(
            onPressed: () => Navigator.pop(context, true),
            child: const Text('Add'),
          ),
        ],
      ),
    );

    if (result == true && mounted) {
      final newDosage = double.tryParse(dosageController.text);
      if (newDosage != null && newDosage > 0) {
        setState(() {
          _selectedEntries.add({...item, 'type': type, 'dosage': newDosage});
        });
      }
    }

    dosageController.dispose();
  }

  void _removeEntry(int index) {
    setState(() {
      _selectedEntries.removeAt(index);
    });
  }

  Future<void> _save() async {
    FocusScope.of(context).unfocus();

    if (!_formKey.currentState!.validate()) {
      return;
    }

    if (_selectedEntries.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Please add at least one entry'),
          backgroundColor: Colors.red,
        ),
      );
      return;
    }

    setState(() {
      _isLoading = true;
    });

    try {
      final userId = int.tryParse(_userIdController.text) ?? 1;
      final sessionId = _sessionIdController.text;
      final workoutId = int.tryParse(_workoutIdController.text);
      final appliedPlanWorkoutId = int.tryParse(
        _appliedPlanWorkoutIdController.text,
      );
      final date = _selectedDate.toIso8601String();

      Map<String, dynamic>? result;

      if (widget.initialPlan != null) {
        result = await NutritionApi.updateSession(
          sessionId,
          userId: userId,
          entries: _selectedEntries,
          workoutId: workoutId,
          appliedPlanWorkoutId: appliedPlanWorkoutId,
          date: date,
        );
      } else {
        result = await NutritionApi.createSession(
          userId: userId,
          sessionId: sessionId,
          entries: _selectedEntries,
          workoutId: workoutId,
          appliedPlanWorkoutId: appliedPlanWorkoutId,
          date: date,
        );
      }

      if (!mounted) return;

      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(
            widget.initialPlan != null
                ? 'Session updated successfully'
                : 'Session created successfully',
          ),
        ),
      );

      Navigator.pop(context, result);
    } catch (e) {
      if (!mounted) return;

      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Error: $e'), backgroundColor: Colors.red),
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
  Widget build(BuildContext context) {
    return AssistantChatHost(
      contextBuilder: () async => {
        'screen': 'nutrition_plan_create',
        'is_editing': widget.initialPlan != null,
        'entities': {'selected_entries_count': _selectedEntries.length},
      },
      builder: (context, openChat) {
        return Scaffold(
          appBar: PrimaryAppBar(
            title: widget.initialPlan != null
                ? 'Edit Nutrition Session'
                : 'Create Nutrition Session',
            onTitleTap: openChat,
            showBack: true,
          ),
          body: Form(
            key: _formKey,
            child: SingleChildScrollView(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text(
                    'Session Configuration',
                    style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold),
                  ),
                  const SizedBox(height: 16),
                  TextFormField(
                    controller: _sessionIdController,
                    decoration: const InputDecoration(
                      labelText: 'Session ID',
                      border: OutlineInputBorder(),
                    ),
                    validator: (value) =>
                        value?.isEmpty == true ? 'Required' : null,
                  ),
                  const SizedBox(height: 16),
                  TextFormField(
                    controller: _userIdController,
                    decoration: const InputDecoration(
                      labelText: 'User ID',
                      border: OutlineInputBorder(),
                    ),
                    keyboardType: TextInputType.number,
                    validator: (value) =>
                        value?.isEmpty == true ? 'Required' : null,
                  ),
                  const SizedBox(height: 16),
                  TextFormField(
                    controller: _workoutIdController,
                    decoration: const InputDecoration(
                      labelText: 'Workout ID (optional)',
                      border: OutlineInputBorder(),
                    ),
                    keyboardType: TextInputType.number,
                  ),
                  const SizedBox(height: 16),
                  TextFormField(
                    controller: _appliedPlanWorkoutIdController,
                    decoration: const InputDecoration(
                      labelText: 'Applied Plan Workout ID (optional)',
                      border: OutlineInputBorder(),
                    ),
                    keyboardType: TextInputType.number,
                  ),
                  const SizedBox(height: 16),
                  InkWell(
                    onTap: () async {
                      final picked = await showDatePicker(
                        context: context,
                        initialDate: _selectedDate,
                        firstDate: DateTime(2020),
                        lastDate: DateTime(2030),
                      );
                      if (picked != null) {
                        setState(() {
                          _selectedDate = picked;
                        });
                      }
                    },
                    child: InputDecorator(
                      decoration: const InputDecoration(
                        labelText: 'Date',
                        border: OutlineInputBorder(),
                      ),
                      child: Text(
                        '${_selectedDate.toLocal().toString().split(' ')[0]}',
                        style: const TextStyle(fontSize: 16),
                      ),
                    ),
                  ),
                  const SizedBox(height: 32),
                  const Text(
                    'Selected Entries',
                    style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
                  ),
                  const SizedBox(height: 8),
                  if (_selectedEntries.isEmpty)
                    const Padding(
                      padding: EdgeInsets.symmetric(vertical: 16.0),
                      child: Center(child: Text('No entries selected')),
                    )
                  else
                    ..._selectedEntries.asMap().entries.map((entry) {
                      final index = entry.key;
                      final item = entry.value;
                      return Card(
                        margin: const EdgeInsets.only(bottom: 8),
                        child: ListTile(
                          title: Text(item['name'] ?? 'Unknown'),
                          subtitle: Text(
                            '${item['type']} - ${item['dosage']} ${item['unit']}',
                          ),
                          trailing: IconButton(
                            icon: const Icon(Icons.remove_circle_outline),
                            onPressed: () => _removeEntry(index),
                          ),
                        ),
                      );
                    }).toList(),
                  const SizedBox(height: 32),
                  const Text(
                    'Available Items',
                    style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
                  ),
                  const SizedBox(height: 8),
                  if (_isLoadingItems)
                    const Center(
                      child: Padding(
                        padding: EdgeInsets.all(16.0),
                        child: LoadingIndicator(),
                      ),
                    )
                  else ...[
                    _buildExpansionCategory('Food', _foodList, 'food'),
                    _buildExpansionCategory(
                      'Supplements',
                      _supplementList,
                      'supplement',
                    ),
                    _buildExpansionCategory(
                      'Medications',
                      _medicationList,
                      'medication',
                    ),
                  ],
                  const SizedBox(height: 32),
                  SizedBox(
                    width: double.infinity,
                    height: 50,
                    child: ElevatedButton(
                      onPressed: _isLoading ? null : _save,
                      child: _isLoading
                          ? const SizedBox(
                              width: 24,
                              height: 24,
                              child: CircularProgressIndicator(
                                strokeWidth: 2,
                                color: Colors.white,
                              ),
                            )
                          : Text(
                              widget.initialPlan != null
                                  ? 'Update Session'
                                  : 'Create Session',
                            ),
                    ),
                  ),
                  const SizedBox(height: 32),
                ],
              ),
            ),
          ),
        );
      },
    );
  }

  Widget _buildExpansionCategory(
    String title,
    List<Map<String, dynamic>> items,
    String type,
  ) {
    return ExpansionTile(
      title: Text(title),
      children: items.isEmpty
          ? [const ListTile(title: Text('No items available'))]
          : items.map((item) {
              return ListTile(
                title: Text(item['name'] ?? 'Unknown'),
                subtitle: Text('${item['dosage']} ${item['unit']}'),
                trailing: IconButton(
                  icon: const Icon(Icons.add_circle_outline),
                  onPressed: () => _addEntry(item, type),
                ),
              );
            }).toList(),
    );
  }
}
