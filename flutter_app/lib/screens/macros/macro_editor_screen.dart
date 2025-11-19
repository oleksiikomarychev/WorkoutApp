import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:workout_app/models/macro.dart';
import 'package:workout_app/providers/macro_providers.dart';
import 'package:workout_app/screens/macros/widgets/trigger_builder.dart';
import 'package:workout_app/screens/macros/widgets/condition_builder.dart';
import 'package:workout_app/screens/macros/widgets/action_builder.dart';
import 'package:workout_app/screens/macros/widgets/duration_selector.dart';
import 'package:workout_app/screens/macros/widgets/macro_human_preview.dart';

class MacroEditorScreen extends ConsumerStatefulWidget {
  final PlanMacro initial;
  final int calendarPlanId;
  const MacroEditorScreen({super.key, required this.initial, required this.calendarPlanId});

  @override
  ConsumerState<MacroEditorScreen> createState() => _MacroEditorScreenState();
}

class _MacroEditorScreenState extends ConsumerState<MacroEditorScreen> {
  final _formKey = GlobalKey<FormState>();
  late TextEditingController _nameCtrl;
  late TextEditingController _priorityCtrl;
  late TextEditingController _ruleCtrl;
  bool _isActive = true;
  String? _error;
  bool _editRawJson = false;

  // Visual builder state
  Map<String, dynamic> _trigger = {};
  Map<String, dynamic> _condition = {};
  Map<String, dynamic> _action = {};
  Map<String, dynamic> _duration = {"scope": "Next_N_Workouts", "count": 1};

  @override
  void initState() {
    super.initState();
    _nameCtrl = TextEditingController(text: widget.initial.name);
    _priorityCtrl = TextEditingController(text: widget.initial.priority.toString());
    _ruleCtrl = TextEditingController(text: const JsonEncoder.withIndent('  ').convert(widget.initial.rule.toJson()));
    _isActive = widget.initial.isActive;
    _trigger = Map<String, dynamic>.from(widget.initial.rule.trigger);
    _condition = Map<String, dynamic>.from(widget.initial.rule.condition);
    _action = Map<String, dynamic>.from(widget.initial.rule.action);
    _duration = Map<String, dynamic>.from(widget.initial.rule.duration.isEmpty ? {"scope": "Next_N_Workouts", "count": 1} : widget.initial.rule.duration);
  }

  @override
  void dispose() {
    _nameCtrl.dispose();
    _priorityCtrl.dispose();
    _ruleCtrl.dispose();
    super.dispose();
  }

  Future<void> _save() async {
    if (!_formKey.currentState!.validate()) return;
    setState(() => _error = null);
    try {
      // Build rule from visual state (or raw JSON if enabled)
      MacroRule rule;
      if (_editRawJson) {
        final Map<String, dynamic> ruleJson = jsonDecode(_ruleCtrl.text) as Map<String, dynamic>;
        rule = MacroRule.fromJson(ruleJson);
      } else {
        final built = {
          'trigger': _trigger,
          'condition': _condition,
          'action': _action,
          'duration': _duration,
        };
        rule = MacroRule.fromJson(built);
      }
      final priority = int.tryParse(_priorityCtrl.text) ?? 100;

      final notifier = ref.read(macrosNotifierProvider(widget.calendarPlanId).notifier);
      final draft = PlanMacro(
        id: widget.initial.id,
        calendarPlanId: widget.calendarPlanId,
        name: _nameCtrl.text.trim(),
        isActive: _isActive,
        priority: priority,
        rule: rule,
      );

      if (draft.id == null) {
        await notifier.create(draft);
      } else {
        await notifier.update(draft);
      }
      if (mounted) Navigator.of(context).pop(draft);
    } catch (e) {
      setState(() => _error = 'Некорректный JSON правила: $e');
    }
  }

  void _syncRulePreview() {
    if (_editRawJson) return;
    final built = {
      'trigger': _trigger,
      'condition': _condition,
      'action': _action,
      'duration': _duration,
    };
    _ruleCtrl.text = const JsonEncoder.withIndent('  ').convert(built);
  }

  @override
  Widget build(BuildContext context) {
    final state = ref.watch(macrosNotifierProvider(widget.calendarPlanId));
    // Prepare data for human-readable preview: from visual builder or raw JSON when enabled
    Map<String, dynamic> humanTrigger = _trigger;
    Map<String, dynamic> humanCondition = _condition;
    Map<String, dynamic> humanAction = _action;
    Map<String, dynamic> humanDuration = _duration;
    if (_editRawJson) {
      try {
        final parsed = jsonDecode(_ruleCtrl.text);
        if (parsed is Map) {
          final j = parsed.cast<String, dynamic>();
          if (j['trigger'] is Map) humanTrigger = (j['trigger'] as Map).cast<String, dynamic>();
          if (j['condition'] is Map) humanCondition = (j['condition'] as Map).cast<String, dynamic>();
          if (j['action'] is Map) humanAction = (j['action'] as Map).cast<String, dynamic>();
          if (j['duration'] is Map) humanDuration = (j['duration'] as Map).cast<String, dynamic>();
        }
      } catch (_) {
        // ignore parse errors, fallback to visual state
      }
    }
    final actionType = (_action['type'] ?? '').toString();
    final showDuration = actionType != 'Inject_Mesocycle';

    return Scaffold(
      appBar: AppBar(
        title: Text(widget.initial.id == null ? 'Создать макрос' : 'Редактировать макрос'),
        actions: [
          IconButton(
            onPressed: _save,
            icon: const Icon(Icons.save),
            tooltip: 'Сохранить',
          )
        ],
      ),
      body: Form(
        key: _formKey,
        child: ListView(
          padding: const EdgeInsets.all(16),
          children: [
            if (_error != null)
              Padding(
                padding: const EdgeInsets.only(bottom: 12),
                child: Text(_error!, style: const TextStyle(color: Colors.red)),
              ),
            TextFormField(
              controller: _nameCtrl,
              decoration: const InputDecoration(labelText: 'Название', border: OutlineInputBorder()),
              validator: (v) => (v == null || v.trim().isEmpty) ? 'Обязательно' : null,
            ),
            const SizedBox(height: 12),
            Row(
              children: [
                Expanded(
                  child: TextFormField(
                    controller: _priorityCtrl,
                    decoration: const InputDecoration(labelText: 'Приоритет', border: OutlineInputBorder()),
                    keyboardType: TextInputType.number,
                    validator: (v) {
                      final n = int.tryParse(v ?? '');
                      if (n == null) return 'Некорректное число';
                      if (n < 0 || n > 10000) return '0..10000';
                      return null;
                    },
                  ),
                ),
                const SizedBox(width: 16),
                Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    const Text('Активен'),
                    Switch(value: _isActive, onChanged: (val) => setState(() => _isActive = val)),
                  ],
                ),
              ],
            ),
            const SizedBox(height: 12),
            // Visual builders
            const SizedBox(height: 16),
            Text('Триггер', style: Theme.of(context).textTheme.titleMedium),
            const SizedBox(height: 8),
            TriggerBuilder(
              initial: _trigger,
              onChanged: (v) {
                setState(() => _trigger = v);
                _syncRulePreview();
              },
            ),
            const SizedBox(height: 16),
            Text('Условие', style: Theme.of(context).textTheme.titleMedium),
            const SizedBox(height: 8),
            ConditionBuilder(
              initial: _condition,
              metric: (_trigger['metric'] as String?),
              onChanged: (v) {
                setState(() => _condition = v);
                _syncRulePreview();
              },
            ),
            const SizedBox(height: 16),
            Text('Действие', style: Theme.of(context).textTheme.titleMedium),
            const SizedBox(height: 8),
            ActionBuilder(
              initial: _action,
              onChanged: (v) {
                setState(() => _action = v);
                _syncRulePreview();
              },
            ),
            if (showDuration) ...[
              const SizedBox(height: 16),
              Text('Длительность', style: Theme.of(context).textTheme.titleMedium),
              const SizedBox(height: 8),
              DurationSelector(
                initial: _duration,
                onChanged: (v) {
                  setState(() => _duration = v);
                  _syncRulePreview();
                },
              ),
            ],
            const SizedBox(height: 16),
            Text('Естественное описание', style: Theme.of(context).textTheme.titleMedium),
            const SizedBox(height: 8),
            MacroHumanPreview(
              trigger: humanTrigger,
              condition: humanCondition,
              action: humanAction,
              duration: humanDuration,
            ),
            const SizedBox(height: 16),
            Row(
              children: [
                const Text('Редактировать JSON'),
                Switch(
                  value: _editRawJson,
                  onChanged: (v) => setState(() {
                    _editRawJson = v;
                    if (!v) _syncRulePreview();
                  }),
                )
              ],
            ),
            TextFormField(
              controller: _ruleCtrl,
              readOnly: !_editRawJson,
              maxLines: 14,
              decoration: const InputDecoration(
                border: OutlineInputBorder(),
                labelText: 'Правило (предпросмотр JSON)',
              ),
              validator: (v) {
                if (!_editRawJson) return null;
                if (v == null || v.trim().isEmpty) return 'Обязательно';
                try {
                  final parsed = jsonDecode(v);
                  if (parsed is! Map) return 'Должен быть JSON-объект';
                } catch (_) {
                  return 'Некорректный JSON';
                }
                return null;
              },
            ),
            const SizedBox(height: 24),
            FilledButton.icon(
              onPressed: _save,
              icon: const Icon(Icons.save),
              label: const Text('Сохранить'),
            ),
          ],
        ),
      ),
    );
  }
}
