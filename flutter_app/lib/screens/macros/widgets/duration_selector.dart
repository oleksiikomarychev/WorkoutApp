import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:workout_app/screens/macros/widgets/workout_picker.dart';

class DurationSelector extends ConsumerStatefulWidget {
  final Map<String, dynamic> initial;
  final ValueChanged<Map<String, dynamic>> onChanged;
  const DurationSelector({super.key, required this.initial, required this.onChanged});

  @override
  ConsumerState<DurationSelector> createState() => _DurationSelectorState();
}

class _DurationSelectorState extends ConsumerState<DurationSelector> {
  String _scope = 'Next_N_Workouts';
  String _count = '1';
  int? _workoutId;
  String? _workoutName;

  @override
  void initState() {
    super.initState();
    _scope = (widget.initial['scope'] ?? 'Next_N_Workouts').toString();
    _count = (widget.initial['count'] ?? 1).toString();
    if (widget.initial['workout_id'] != null) {
      final wid = int.tryParse(widget.initial['workout_id'].toString());
      if (wid != null) _workoutId = wid;
    }
  }

  void _emit() {
    final cnt = int.tryParse(_count) ?? 1;
    final map = <String, dynamic>{'scope': _scope};
    if (_scope == 'Next_N_Workouts') {
      map['count'] = cnt;
    } else if (_scope == 'Until_Workout') {
      if (_workoutId != null) map['workout_id'] = _workoutId;
    }
    widget.onChanged(map);
  }

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        DropdownButtonFormField<String>(
          value: _scope,
          items: const [
            DropdownMenuItem(value: 'Next_N_Workouts', child: Text('Следующие N тренировок')),
            DropdownMenuItem(value: 'Until_Last_Workout', child: Text('До последней тренировки')),
            DropdownMenuItem(value: 'Until_End_Of_Mesocycle', child: Text('До конца мезоцикла')),
            DropdownMenuItem(value: 'Until_End_Of_Microcycle', child: Text('До конца микроцикла')),
            DropdownMenuItem(value: 'Until_Workout', child: Text('До тренировки X')),
          ],
          decoration: const InputDecoration(labelText: 'Область', border: OutlineInputBorder()),
          onChanged: (v) {
            setState(() {
              _scope = v ?? 'Next_N_Workouts';
              if (_scope != 'Next_N_Workouts') _count = '1';
              if (_scope != 'Until_Workout') { _workoutId = null; _workoutName = null; }
            });
            _emit();
            if (_scope == 'Until_Workout' && _workoutId == null) {
              Future.microtask(() async {
                final picked = await showWorkoutPickerBottomSheet(context, ref);
                if (!mounted) return;
                if (picked != null) {
                  setState(() { _workoutId = picked.id; _workoutName = picked.name; });
                  _emit();
                }
              });
            }
          },
        ),
        const SizedBox(height: 8),
        if (_scope == 'Next_N_Workouts')
          SizedBox(
            width: 180,
            child: TextFormField(
              initialValue: _count,
              decoration: const InputDecoration(labelText: 'Количество', border: OutlineInputBorder()),
              keyboardType: TextInputType.number,
              onChanged: (v) { setState(() => _count = v); _emit(); },
              validator: (v) {
                final n = int.tryParse(v ?? '');
                if (n == null || n < 1) return '>=1';
                return null;
              },
            ),
          )
        else if (_scope == 'Until_Workout') ...[
          Row(
            children: [
              OutlinedButton.icon(
                onPressed: () async {
                  final picked = await showWorkoutPickerBottomSheet(context, ref);
                  if (picked != null) {
                    setState(() { _workoutId = picked.id; _workoutName = picked.name; });
                    _emit();
                  }
                },
                icon: const Icon(Icons.calendar_today),
                label: const Text('Выбрать тренировку'),
              ),
              const SizedBox(width: 8),
              Expanded(
                child: Text(
                  _workoutId == null ? 'Не выбрано' : 'Выбрано: ${_workoutName ?? '#'+_workoutId.toString()}',
                  overflow: TextOverflow.ellipsis,
                ),
              )
            ],
          ),
        ]
      ],
    );
  }
}
