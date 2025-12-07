import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:workout_app/providers/target_data_providers.dart';

class TargetSelector extends ConsumerStatefulWidget {
  final Map<String, dynamic>? initial;
  final ValueChanged<Map<String, dynamic>?> onChanged;
  const TargetSelector({super.key, this.initial, required this.onChanged});

  @override
  ConsumerState<TargetSelector> createState() => _TargetSelectorState();
}

class _TargetSelectorState extends ConsumerState<TargetSelector> {

  String _mode = 'tags';
  final _exerciseIdsCtrl = TextEditingController();


  final Set<String> _mt = {};
  final Set<String> _rg = {};
  final Set<String> _mg = {};
  final Set<String> _eq = {};

  @override
  void initState() {
    super.initState();
    final init = widget.initial;
    if (init != null) {
      if (init['exercise_ids'] is List) {
        _mode = 'ids';
        _exerciseIdsCtrl.text = (init['exercise_ids'] as List).join(',');
      } else if (init['exercise_id'] != null) {
        _mode = 'ids';
        _exerciseIdsCtrl.text = init['exercise_id'].toString();
      }
      final selector = init['selector'];
      if (selector is Map && (selector['type']?.toString().toLowerCase() == 'tags')) {
        _mode = 'tags';
        final val = (selector['value'] as Map?) ?? {};
        void fill(Set<String> s, dynamic v) {
          if (v is String && v.isNotEmpty) s.add(v.toLowerCase());
          if (v is List) {
            for (final e in v) {
              final t = e?.toString();
              if (t != null && t.isNotEmpty) s.add(t.toLowerCase());
            }
          }
        }
        fill(_mt, val['movement_type']);
        fill(_rg, val['region']);
        fill(_mg, val['muscle_group']);
        fill(_eq, val['equipment']);
      }
    }


  }

  @override
  void dispose() {
    _exerciseIdsCtrl.dispose();
    super.dispose();
  }

  void _emit() {
    if (_mode == 'ids') {
      final ids = _exerciseIdsCtrl.text
          .split(',')
          .map((s) => int.tryParse(s.trim()))
          .where((v) => v != null)
          .map((v) => v!)
          .toList();
      if (ids.isEmpty) {
        widget.onChanged(null);
      } else {
        widget.onChanged({'exercise_ids': ids});
      }
      return;
    }

    final value = <String, dynamic>{};
    if (_mt.isNotEmpty) value['movement_type'] = _mt.toList();
    if (_rg.isNotEmpty) value['region'] = _rg.toList();
    if (_mg.isNotEmpty) value['muscle_group'] = _mg.toList();
    if (_eq.isNotEmpty) value['equipment'] = _eq.toList();
    if (value.isEmpty) {
      widget.onChanged(null);
    } else {
      widget.onChanged({'selector': {'type': 'tags', 'value': value}});
    }
  }

  @override
  Widget build(BuildContext context) {
    final defsAsync = ref.watch(exerciseDefinitionsProvider);
    final tags = ref.watch(tagCatalogProvider);
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            const Text('Target by:'),
            const SizedBox(width: 8),
            SegmentedButton<String>(
              segments: const [
                ButtonSegment(value: 'tags', label: Text('Tags')),
                ButtonSegment(value: 'ids', label: Text('IDs')),
              ],
              selected: {_mode},
              onSelectionChanged: (s) {
                setState(() => _mode = s.first);
                _emit();
              },
            ),
          ],
        ),
        const SizedBox(height: 8),
        if (_mode == 'ids')
          TextField(
            controller: _exerciseIdsCtrl,
            decoration: const InputDecoration(
              border: OutlineInputBorder(),
              labelText: 'exercise_ids (CSV)',
              hintText: '101,205,309',
            ),
            onChanged: (_) => _emit(),
          )
        else ...[
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: [
              _TagGroup(
                title: 'movement_type',
                values: tags.movementTypes,
                selected: _mt,
                onChanged: (s) { setState(() => _mt..clear()..addAll(s)); _emit(); },
              ),
              _TagGroup(
                title: 'region',
                values: tags.regions,
                selected: _rg,
                onChanged: (s) { setState(() => _rg..clear()..addAll(s)); _emit(); },
              ),
              _TagGroup(
                title: 'muscle_group',
                values: tags.muscleGroups,
                selected: _mg,
                onChanged: (s) { setState(() => _mg..clear()..addAll(s)); _emit(); },
              ),
              _TagGroup(
                title: 'equipment',
                values: tags.equipment,
                selected: _eq,
                onChanged: (s) { setState(() => _eq..clear()..addAll(s)); _emit(); },
              ),
            ],
          )
        ],
        const SizedBox(height: 8),
        defsAsync.when(
          data: (_) => const SizedBox.shrink(),
          loading: () => const LinearProgressIndicator(minHeight: 2),
          error: (_, __) => const Text('Failed to load exercises', style: TextStyle(color: Colors.red)),
        )
      ],
    );
  }
}

class _TagGroup extends StatelessWidget {
  final String title;
  final Set<String> values;
  final Set<String> selected;
  final ValueChanged<Set<String>> onChanged;
  const _TagGroup({required this.title, required this.values, required this.selected, required this.onChanged});

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(title, style: Theme.of(context).textTheme.labelLarge),
        Wrap(
          spacing: 8,
          children: values.map((v) {
            final isSel = selected.contains(v);
            return FilterChip(
              selected: isSel,
              label: Text(v),
              onSelected: (sel) {
                final next = Set<String>.from(selected);
                if (sel) next.add(v); else next.remove(v);
                onChanged(next);
              },
            );
          }).toList(),
        )
      ],
    );
  }
}
