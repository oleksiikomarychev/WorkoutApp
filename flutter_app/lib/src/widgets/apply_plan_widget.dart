import 'package:flutter/material.dart';
import 'package:workout_app/models/user_max.dart';

class ApplyPlanWidget extends StatefulWidget {
  final List<UserMax> userMaxList;
  final Function(Map<String, dynamic>) onApply;

  const ApplyPlanWidget({
    Key? key,
    required this.userMaxList,
    required this.onApply,
  }) : super(key: key);

  @override
  _ApplyPlanWidgetState createState() => _ApplyPlanWidgetState();
}

class _ApplyPlanWidgetState extends State<ApplyPlanWidget> {
  final _formKey = GlobalKey<FormState>();
  List<int> _selectedUserMaxIds = [];
  bool _computeWeights = true;
  double _roundingStep = 2.5;
  String _roundingMode = 'nearest';

  @override
  Widget build(BuildContext context) {
    final groupedUserMaxes = <int, List<UserMax>>{};
    for (var userMax in widget.userMaxList) {
      groupedUserMaxes.putIfAbsent(userMax.exerciseId, () => []).add(userMax);
    }

    return FractionallySizedBox(
      heightFactor: 0.7,
      child: Container(
        decoration: BoxDecoration(
          color: Theme.of(context).colorScheme.surface,
          borderRadius: const BorderRadius.vertical(top: Radius.circular(28)),
          boxShadow: [
            BoxShadow(
              color: Colors.black.withOpacity(0.2),
              blurRadius: 12,
              offset: const Offset(0, -4),
            ),
          ],
        ),
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(24),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Text('Apply Training Plan', 
                      style: Theme.of(context).textTheme.headlineSmall),
                  IconButton(
                    icon: const Icon(Icons.close),
                    onPressed: () => Navigator.pop(context),
                  ),
                ],
              ),
              const Divider(height: 24),
              Form(
                key: _formKey,
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    // UserMax selection
                    Text('Select User Max', 
                        style: Theme.of(context).textTheme.titleMedium),
                    const SizedBox(height: 12),
                    
                    Column(
                      children: groupedUserMaxes.entries.map((entry) {
                        final exerciseId = entry.key;
                        final userMaxes = entry.value;
                        return ExpansionTile(
                          title: Text(userMaxes.first.exerciseName),
                          children: userMaxes.map((userMax) {
                            return Padding(
                              padding: const EdgeInsets.symmetric(vertical: 4),
                              child: FilterChip.elevated(
                                label: Text('${userMax.maxWeight} kg x ${userMax.repMax}'),
                                selected: _selectedUserMaxIds.contains(userMax.id),
                                onSelected: (selected) {
                                  setState(() {
                                    if (selected) {
                                      _selectedUserMaxIds.add(userMax.id);
                                    } else {
                                      _selectedUserMaxIds.remove(userMax.id);
                                    }
                                  });
                                },
                              ),
                            );
                          }).toList(),
                        );
                      }).toList(),
                    ),
                    const SizedBox(height: 20),
                    
                    // Compute weights toggle
                    Row(
                      children: [
                        Switch.adaptive(
                          value: _computeWeights,
                          onChanged: (value) => setState(() => _computeWeights = value),
                        ),
                        const SizedBox(width: 8),
                        Text('Compute weights', 
                            style: Theme.of(context).textTheme.bodyLarge),
                      ],
                    ),
                    const SizedBox(height: 20),
                    
                    // Rounding options
                    Row(
                      children: [
                        Expanded(
                          child: TextFormField(
                            decoration: const InputDecoration(
                              labelText: 'Rounding Step',
                              border: OutlineInputBorder(),
                              isDense: true,
                            ),
                            keyboardType: TextInputType.number,
                            initialValue: _roundingStep.toString(),
                            onChanged: (value) => 
                                _roundingStep = double.tryParse(value) ?? 2.5,
                          ),
                        ),
                        const SizedBox(width: 16),
                        Expanded(
                          child: DropdownButtonFormField<String>(
                            value: _roundingMode,
                            decoration: const InputDecoration(
                              labelText: 'Rounding Mode',
                              border: OutlineInputBorder(),
                              isDense: true,
                            ),
                            items: ['nearest', 'ceil', 'floor']
                                .map((mode) => DropdownMenuItem(
                                      value: mode,
                                      child: Text(mode),
                                    ))
                                .toList(),
                            onChanged: (value) => 
                                setState(() => _roundingMode = value ?? 'nearest'),
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 24),
                    
                    // Apply button
                    FilledButton.tonal(
                      onPressed: () {
                        if (_selectedUserMaxIds.isEmpty) {
                          ScaffoldMessenger.of(context).showSnackBar(
                            const SnackBar(content: Text('Please select at least one User Max')),
                          );
                          return;
                        }
                        
                        widget.onApply({
                          'user_max_ids': _selectedUserMaxIds,
                          'compute_weights': _computeWeights,
                          'rounding_step': _roundingStep,
                          'rounding_mode': _roundingMode,
                          'generate_workouts': true,
                        });
                      },
                      child: const Text('Apply Plan'),
                    ),
                  ],
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
