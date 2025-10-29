import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:workout_app/models/exercise_definition.dart';
import 'package:workout_app/providers/target_data_providers.dart';

class MacroHumanPreview extends ConsumerWidget {
  final Map<String, dynamic> trigger;
  final Map<String, dynamic> condition;
  final Map<String, dynamic> action;
  final Map<String, dynamic> duration;
  const MacroHumanPreview({super.key, required this.trigger, required this.condition, required this.action, required this.duration});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final defs = ref.watch(exerciseDefinitionsProvider).maybeWhen(data: (d) => d, orElse: () => const <ExerciseDefinition>[]);
    final nameMap = <int, String>{
      for (final e in defs)
        if (e.id != null) e.id!: (e.name ?? 'Упражнение ${e.id}')
    };
    final main = _mainSentence(nameMap, defs);
    final details = _detailsLines(nameMap, defs);
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(main),
        const SizedBox(height: 6),
        ...details.map((s) => Padding(
              padding: const EdgeInsets.only(bottom: 2),
              child: Text(s, style: Theme.of(context).textTheme.bodySmall),
            )),
      ],
    );
  }

  String _metricName(String? m) {
    switch (m) {
      case 'Readiness_Score':
        return 'готовность';
      case 'RPE_Session':
        return 'RPE сессии';
      case 'Total_Reps':
        return 'количество повторений';
      case 'e1RM':
        return 'оценка 1ПМ';
      case 'Performance_Trend':
        return 'тренд прогресса';
      case 'RPE_Delta_From_Plan':
        return 'отклонение RPE от плана';
      case 'Reps_Delta_From_Plan':
        return 'отклонение повторов от плана';
    }
    return 'метрика';
  }

  String _targetFromTrigger(Map<int, String> names) {
    final ids = <int>[];
    final src = trigger['exercise_ids'];
    if (src is List) {
      for (final e in src) {
        final id = int.tryParse(e.toString());
        if (id != null) ids.add(id);
      }
    } else if (trigger['exercise_id'] != null) {
      final id = int.tryParse(trigger['exercise_id'].toString());
      if (id != null) ids.add(id);
    }
    if (ids.isEmpty) return 'по всем упражнениям';
    final namesList = ids.map((id) => names[id] ?? 'ID $id').toList();
    return 'для упражнений: ${namesList.join(', ')}';
  }

  String _relationWord(String r) {
    switch (r) {
      case '>=':
        return 'больше или равно';
      case '<=':
        return 'меньше или равно';
      case '==':
        return 'равно';
      case '!=':
        return 'не равно';
      case '>':
        return 'больше';
      case '<':
        return 'меньше';
    }
    return r;
  }

  String _unitForMetric(String? m) {
    if (m == 'e1RM') return 'кг';
    return '';
  }

  String _conditionPhrase() {
    final op = (condition['op'] ?? '').toString();
    if (op.isEmpty) return 'условие не задано';
    final metric = trigger['metric']?.toString();
    final unit = _unitForMetric(metric);
    if (op == 'in_range' || op == 'not_in_range') {
      final vals = (condition['range'] as List?) ?? (condition['values'] as List?) ?? const [];
      if (vals.length >= 2) {
        final a = vals[0].toString();
        final b = vals[1].toString();
        final su = unit.isEmpty ? '' : ' $unit';
        return op == 'in_range' ? 'значение в диапазоне $a до $b$su' : 'значение вне диапазона $a до $b$su';
      }
      return op == 'in_range' ? 'значение в диапазоне' : 'значение вне диапазона';
    }
    if (op == 'stagnates_for') {
      final n = condition['n']?.toString();
      final e = condition['epsilon_percent']?.toString();
      if (n != null && e != null) return 'стагнация за $n окон в пределах $e процентов';
      return 'стагнация за окна';
    }
    if (op == 'deviates_from_avg') {
      final n = condition['n']?.toString();
      final v = condition['value_percent']?.toString();
      final d = (condition['direction'] ?? '').toString();
      final dir = d.isEmpty ? '' : ', направление: ${d == 'positive' ? 'положительное' : d == 'negative' ? 'отрицательное' : d}';
      if (n != null && v != null) return 'отклонение от среднего за $n окон не менее $v процентов$dir';
      return 'отклонение от среднего';
    }
    if (op == 'holds_for') {
      final rel = _relationWord((condition['relation'] ?? '').toString());
      final val = (condition['value'] ?? '').toString();
      final su = unit.isEmpty ? '' : ' $unit';
      final n = (condition['n'] ?? '').toString();
      if (rel.isNotEmpty && val.isNotEmpty && n.isNotEmpty) return 'выполняется $n тренировок подряд: значение $rel $val$su';
      return 'выполняется несколько тренировок подряд';
    }
    if (op == 'holds_for_sets') {
      final rel = _relationWord((condition['relation'] ?? '').toString());
      final val = (condition['value'] ?? '').toString();
      final su = unit.isEmpty ? '' : ' $unit';
      final n = (condition['n_sets'] ?? '').toString();
      if (rel.isNotEmpty && val.isNotEmpty && n.isNotEmpty) return 'выполняется $n подходов подряд внутри тренировки: значение $rel $val$su';
      return 'выполняется несколько подходов подряд внутри тренировки';
    }
    final v = (condition['value'] ?? '').toString();
    final su = unit.isEmpty ? '' : ' $unit';
    if (op == '>') return 'значение больше $v$su';
    if (op == '<') return 'значение меньше $v$su';
    if (op == '=') return 'значение равно $v$su';
    if (op == '!=') return 'значение не равно $v$su';
    return 'условие задано';
  }

  String _actionTarget(Map<int, String> names, List<ExerciseDefinition> defs) {
    final t = (action['target'] as Map?)?.cast<String, dynamic>();
    if (t == null) return 'для всех упражнений';
    if (t['exercise_ids'] is List) {
      final ids = <int>[];
      for (final e in (t['exercise_ids'] as List)) {
        final id = int.tryParse(e.toString());
        if (id != null) ids.add(id);
      }
      if (ids.isEmpty) return 'для всех упражнений';
      final list = ids.map((id) => names[id] ?? 'ID $id').toList();
      return 'для упражнений: ${list.join(', ')}';
    }
    if (t['selector'] is Map) {
      final sel = (t['selector'] as Map).cast<String, dynamic>();
      final val = (sel['value'] as Map?)?.cast<String, dynamic>() ?? const {};
      final parts = <String>[];
      void add(String k) {
        final v = val[k];
        if (v is String && v.isNotEmpty) parts.add('$k: $v');
        if (v is List && v.isNotEmpty) parts.add('$k: ${v.join(', ')}');
      }
      add('movement_type');
      add('region');
      add('muscle_group');
      add('equipment');
      if (parts.isEmpty) return 'для всех упражнений';
      final examples = <String>[];
      bool matches(ExerciseDefinition d) {
        bool ok = true;
        bool check(String key, String? val) {
          final want = val?.toLowerCase();
          if (want == null || want.isEmpty) return true;
          final actual = (d.toJson()[key] as String?)?.toLowerCase();
          return actual != null && actual.isNotEmpty && actual == want;
        }
        bool checkList(String key, List list) {
          if (list.isEmpty) return true;
          final actual = (d.toJson()[key] as String?)?.toLowerCase();
          if (actual == null || actual.isEmpty) return false;
          return list.map((e) => e.toString().toLowerCase()).contains(actual);
        }
        final mt = val['movement_type'];
        final rg = val['region'];
        final mg = val['muscle_group'];
        final eq = val['equipment'];
        if (mt is String) ok = ok && check('movement_type', mt);
        if (mt is List) ok = ok && checkList('movement_type', mt);
        if (rg is String) ok = ok && check('region', rg);
        if (rg is List) ok = ok && checkList('region', rg);
        if (mg is String) ok = ok && check('muscle_group', mg);
        if (mg is List) ok = ok && checkList('muscle_group', mg);
        if (eq is String) ok = ok && check('equipment', eq);
        if (eq is List) ok = ok && checkList('equipment', eq);
        return ok;
      }
      for (final d in defs) {
        if (examples.length >= 3) break;
        if (matches(d)) {
          final nm = (d.name ?? '').trim();
          if (nm.isNotEmpty) examples.add(nm);
        }
      }
      final base = 'по тегам: ${parts.join(', ')}';
      if (examples.isEmpty) return base;
      return '$base, например: ${examples.join(', ')}';
    }
    return 'для всех упражнений';
  }

  String _actionPhrase(Map<int, String> names, List<ExerciseDefinition> defs) {
    final type = (action['type'] ?? '').toString();
    final params = (action['params'] as Map?)?.cast<String, dynamic>() ?? const {};
    final mode = (params['mode'] ?? '').toString();
    final valStr = (params['value'] ?? '').toString();
    final v = double.tryParse(valStr);
    if (type == 'Inject_Mesocycle') {
      final buf = <String>[];
      String base = 'внедрить мезоцикл';
      if (mode == 'by_Template') {
        final tid = params['template_id'];
        if (tid != null && tid.toString().isNotEmpty) {
          base = '$base по шаблону ID ${tid.toString()}';
        }
      } else if (mode == 'Create_Inline') {
        final weeks = params['duration_weeks'];
        final dim = params['days_in_microcycle'];
        final restDays = (params['rest_days'] as List?)?.map((e) => int.tryParse(e.toString()) ?? -1).where((e) => e > 0).toList() ?? const <int>[];
        final focus = (params['default_focus_tags'] as Map?)?.cast<String, dynamic>() ?? const {};
        final parts = <String>[];
        if (weeks != null) parts.add('${weeks.toString()} недель');
        if (dim != null) parts.add('микроцикл ${dim.toString()} дней');
        if (restDays.isNotEmpty) parts.add('выходные дни: ${restDays.join(', ')}');
        if (focus.isNotEmpty) {
          final tagParts = <String>[];
          void add(String k) {
            final v = focus[k];
            if (v is String && v.isNotEmpty) tagParts.add('$k: $v');
            if (v is List && v.isNotEmpty) tagParts.add('$k: ${v.join(', ')}');
          }
          add('movement_type');
          add('region');
          add('muscle_group');
          add('equipment');
          if (tagParts.isNotEmpty) parts.add('фокус: ${tagParts.join(', ')}');
        }
        if (parts.isNotEmpty) base = '$base (${parts.join('; ')})';
      }
      final placement = (params['placement'] as Map?)?.cast<String, dynamic>() ?? const {};
      final pmode = (placement['mode'] ?? '').toString();
      if (pmode == 'Append_To_End') buf.add('в конец плана');
      if (pmode == 'Insert_After_Workout') {
        final wid = placement['workout_id'];
        if (wid != null) {
          buf.add('после тренировки #${wid.toString()}');
        } else {
          buf.add('после выбранной тренировки');
        }
      }
      if (pmode == 'Insert_After_Mesocycle') {
        final midx = placement['mesocycle_index'];
        if (midx != null) {
          buf.add('после мезоцикла ${midx.toString()}');
        } else {
          buf.add('после выбранного мезоцикла');
        }
      }
      final conflict = (params['on_conflict'] ?? '').toString();
      if (conflict.isNotEmpty) {
        String ctext = conflict == 'Replace_Planned' ? 'заменять запланированное' : conflict == 'Shift_Forward' ? 'сдвигать вперёд' : conflict == 'Skip_On_Conflict' ? 'пропускать конфликтующие' : conflict;
        buf.add('при конфликте: $ctext');
      }
      final tail = buf.isEmpty ? '' : ' ' + buf.join(', ');
      return base + tail;
    }
    if (type == 'Adjust_Load' && mode == 'by_Percent' && v != null) {
      final abs = v.abs().toString().replaceAll('-', '');
      return v < 0 ? 'уменьшить вес на $abs процентов ${_actionTarget(names, defs)}' : 'увеличить вес на $abs процентов ${_actionTarget(names, defs)}';
    }
    if (type == 'Adjust_Load' && mode == 'to_Target' && valStr.isNotEmpty) {
      return 'подогнать вес к целевому RPE $valStr ${_actionTarget(names, defs)}';
    }
    if (type == 'Adjust_Reps' && mode == 'by_Value' && v != null) {
      final abs = v.abs().toString().replaceAll('-', '');
      return v < 0 ? 'уменьшить повторы на $abs ${_actionTarget(names, defs)}' : 'увеличить повторы на $abs ${_actionTarget(names, defs)}';
    }
    if (type == 'Adjust_Reps' && mode == 'to_Target' && valStr.isNotEmpty) {
      return 'подобрать повторы к целевому RPE $valStr ${_actionTarget(names, defs)}';
    }
    if (type == 'Adjust_Sets' && mode == 'by_Value' && v != null) {
      final abs = v.abs().toString().replaceAll('-', '');
      return v < 0 ? 'убрать $abs подходов ${_actionTarget(names, defs)}' : 'добавить $abs подходов ${_actionTarget(names, defs)}';
    }
    return 'выполнить действие ${_actionTarget(names, defs)}';
  }

  String _durationPhrase() {
    final scope = (duration['scope'] ?? '').toString();
    final count = int.tryParse((duration['count'] ?? '1').toString()) ?? 1;
    if (scope == 'Next_N_Workouts') return 'в следующие $count тренировок';
    if (scope == 'Until_Last_Workout') return 'до последней тренировки';
    if (scope == 'Until_End_Of_Mesocycle') return 'до конца мезоцикла';
    if (scope == 'Until_End_Of_Microcycle') return 'до конца микроцикла';
    if (scope == 'Until_Workout') {
      final wid = duration['workout_id'];
      if (wid != null) return 'до тренировки #$wid';
      return 'до выбранной тренировки';
    }
    return '';
  }

  String _mainSentence(Map<int, String> names, List<ExerciseDefinition> defs) {
    final metric = _metricName(trigger['metric']?.toString());
    final trg = _targetFromTrigger(names);
    final cond = _conditionPhrase();
    final act = _actionPhrase(names, defs);
    final dur = _durationPhrase();
    if ((trigger.isEmpty && condition.isEmpty && action.isEmpty)) return 'Описание появится после выбора метрики, условия и действия';
    final parts = <String>[];
    parts.add('Если $metric $trg, и $cond, то $act');
    if (dur.isNotEmpty) parts.add(dur);
    return parts.join(' ') + '.';
  }

  List<String> _detailsLines(Map<int, String> names, List<ExerciseDefinition> defs) {
    final metric = _metricName(trigger['metric']?.toString());
    final trg = _targetFromTrigger(names);
    final cond = _conditionPhrase();
    final act = _actionPhrase(names, defs);
    final dur = _durationPhrase();
    final out = <String>[];
    out.add('Метрика: $metric');
    out.add('Триггер: $trg');
    out.add('Условие: $cond');
    out.add('Действие: $act');
    if (dur.isNotEmpty) out.add('Длительность: $dur');
    return out;
  }
}
