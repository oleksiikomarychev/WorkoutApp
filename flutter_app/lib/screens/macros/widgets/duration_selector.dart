import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:workout_app/l10n/app_localizations.dart';
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
  int? _anchorWorkoutId;
  String? _anchorWorkoutName;

  @override
  void initState() {
    super.initState();
    _scope = (widget.initial['scope'] ?? 'Next_N_Workouts').toString();
    _count = (widget.initial['count'] ?? 1).toString();
    if (widget.initial['workout_id'] != null) {
      final wid = int.tryParse(widget.initial['workout_id'].toString());
      if (wid != null) _anchorWorkoutId = wid;
    }
  }

  void _emit() {
    final cnt = int.tryParse(_count) ?? 1;
    final map = <String, dynamic>{'scope': _scope};
    if (_scope == 'Next_N_Workouts') {
      map['count'] = cnt;
    } else if (_scope == 'Until_Workout') {
      if (_anchorWorkoutId != null) map['workout_id'] = _anchorWorkoutId;
    }
    widget.onChanged(map);
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        DropdownButtonFormField<String>(
          value: _scope,
          items: [
            DropdownMenuItem(value: 'Next_N_Workouts', child: Text(l10n.macroDurationNextNWorkouts)),
            DropdownMenuItem(value: 'Until_Last_Workout', child: Text(l10n.macroDurationUntilLastWorkout)),
            DropdownMenuItem(value: 'Until_End_Of_Mesocycle', child: Text(l10n.macroDurationUntilEndOfMeso)),
            DropdownMenuItem(value: 'Until_End_Of_Microcycle', child: Text(l10n.macroDurationUntilEndOfMicro)),
            DropdownMenuItem(value: 'Until_Workout', child: Text(l10n.macroDurationUntilWorkoutX)),
          ],
          decoration: InputDecoration(labelText: l10n.macroDurationScopeLabel, border: const OutlineInputBorder()),
          onChanged: (v) {
            setState(() {
              _scope = v ?? 'Next_N_Workouts';
              if (_scope != 'Next_N_Workouts') _count = '1';
              if (_scope != 'Until_Workout') { _anchorWorkoutId = null; _anchorWorkoutName = null; }
            });
            _emit();
            if (_scope == 'Until_Workout' && _anchorWorkoutId == null) {
              Future.microtask(() async {
                final picked = await showWorkoutPickerBottomSheet(context, ref);
                if (!mounted) return;
                if (picked != null) {
                  setState(() { _anchorWorkoutId = picked.id; _anchorWorkoutName = picked.name; });
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
              decoration: InputDecoration(labelText: l10n.macroDurationCountLabel, border: const OutlineInputBorder()),
              keyboardType: TextInputType.number,
              onChanged: (v) { setState(() => _count = v); _emit(); },
              validator: (v) {
                if (_scope == 'Next_N_Workouts') {
                  if (v == null || v.isEmpty) return l10n.fieldRequired;
                  if (int.tryParse(v) == null) return l10n.macroActionEnterNumber;
                }
                return null;
              },
            ),
          )
        else if (_scope == 'Until_Workout') ...[
          const SizedBox(height: 8),
          Row(
            children: [
              OutlinedButton.icon(
                onPressed: () async {
                  final picked = await showWorkoutPickerBottomSheet(context, ref);
                  if (picked != null) {
                    setState(() {
                      _anchorWorkoutId = picked.id;
                      _anchorWorkoutName = picked.name;
                    });
                    _emit();
                  }
                },
                icon: const Icon(Icons.calendar_today),
                label: Text(l10n.macroActionPickWorkout),
              ),
              const SizedBox(width: 8),
              Expanded(
                child: Text(_anchorWorkoutId == null ? l10n.macroActionNotSelected : '${l10n.macroActionAfterAnchor(_anchorWorkoutName ?? '#'+_anchorWorkoutId.toString())}'),
              ),
            ],
          ),
        ]
      ],
    );
  }
}
