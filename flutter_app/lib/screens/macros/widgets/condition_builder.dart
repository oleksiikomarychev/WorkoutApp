import 'package:flutter/material.dart';
import 'package:workout_app/l10n/app_localizations.dart';

class ConditionBuilder extends StatefulWidget {
  final Map<String, dynamic> initial;
  final ValueChanged<Map<String, dynamic>> onChanged;
  final String? metric;
  const ConditionBuilder({super.key, required this.initial, required this.onChanged, this.metric});

  @override
  State<ConditionBuilder> createState() => _ConditionBuilderState();
}

class _ConditionBuilderState extends State<ConditionBuilder> {
  String _op = '';
  String _value = '';
  String _rangeFrom = '';
  String _rangeTo = '';
  String _n = '';
  String _nSets = '';
  String _epsilonPercent = '';
  String _valuePercent = '';
  String _direction = '';
  String _relation = '';


  List<String> _allowedOpKeysForMetric(String? metric) {
    final m = (metric ?? '').trim();
    switch (m) {
      case 'Performance_Trend':
        return ['stagnates_for', 'deviates_from_avg'];
      case 'e1RM':
        return ['>', '<', '=', '!=', 'in_range', 'not_in_range'];
      case 'RPE_Delta_From_Plan':
      case 'Reps_Delta_From_Plan':
        return ['>', '<', '=', '!=', 'in_range', 'not_in_range', 'holds_for', 'holds_for_sets'];
      case 'Total_Reps':
      case 'Readiness_Score':
      case 'RPE_Session':
        return ['>', '<', '=', '!=', 'in_range', 'not_in_range', 'holds_for'];
      default:
        return ['>', '<', '=', '!=', 'in_range', 'not_in_range'];
    }
  }

  String _opLabel(String op, AppLocalizations l10n) {
    switch (op) {
      case '>':
        return l10n.macroConditionGreater;
      case '<':
        return l10n.macroConditionLess;
      case '=':
        return l10n.macroConditionEqual;
      case '!=':
        return l10n.macroConditionNotEqual;
      case 'in_range':
        return l10n.macroConditionInRange;
      case 'not_in_range':
        return l10n.macroConditionNotInRange;
      case 'stagnates_for':
        return l10n.macroConditionStagnates;
      case 'deviates_from_avg':
        return l10n.macroConditionDeviates;
      case 'holds_for':
        return l10n.macroConditionHoldsForWorkouts;
      case 'holds_for_sets':
        return l10n.macroConditionHoldsForSets;
      default:
        return op;
    }
  }

  List<DropdownMenuItem<String>> _opItems(List<String> keys, AppLocalizations l10n) {
    return keys
        .map((k) => DropdownMenuItem<String>(value: k, child: Text(_opLabel(k, l10n))))
        .toList(growable: false);
  }

  String _opHelp(String op) {
    switch (op) {
      case '>':
      case '<':
      case '=':
      case '!=':
        return 'Сравнение с числом. Введите значение (целое или дробное), например 10 или -2.5.';
      case 'in_range':
        return 'Проверяет, что значение находится ВНУТРИ диапазона (включительно). Введите два числа; порядок не важен.';
      case 'not_in_range':
        return 'Проверяет, что значение находится ВНЕ диапазона (включительно по границам). Введите два числа.';
      case 'stagnates_for':
        return 'Стагнация: последние n окон укладываются в коридор шириной epsilon_percent (%). Укажите n и epsilon_percent.';
      case 'deviates_from_avg':
        return 'Отклонение от среднего за n окон. value_percent — порог отклонения в %, direction — направление (опционально).';
      case 'holds_for':
        return 'Подряд N тренировок: relation (>, <, >=, <=, ==, !=, в диапазоне, вне диапазона) применяется N раз подряд. Для диапазона укажите границы «от» и «до».';
      case 'holds_for_sets':
        return 'Подряд N подходов внутри тренировки: для каждой пары план/факт по сету применяется relation к дельте (например, Δповторов).';
      default:
        return '';
    }
  }

  String _metricOpHelp(String op) {
    final m = (widget.metric ?? '').toString();
    if (m == 'Performance_Trend') {
      if (op == 'stagnates_for') {
        return 'Тренд (стагнация): берутся последние n значений метрики и сравнивается ширина диапазона с epsilon_percent (%).\nФормат: n — целое (окна), epsilon_percent — число в процентах.\nПример: n=5, epsilon_percent=1.0 (изменение ≤ 1% за 5 окон).';
      }
      if (op == 'deviates_from_avg') {
        return 'Тренд (отклонение): сравнивается последнее значение со средним за n окон. \nФормат: n — целое, value_percent — порог в %, direction — positive/negative (опционально).\nПример: n=5, value_percent=3, direction="negative" (падение ≥ 3%).';
      }
    }
    return '';
  }

  @override
  void initState() {
    super.initState();
    _op = (widget.initial['op'] ?? '').toString();
    if (widget.initial['value'] != null) _value = widget.initial['value'].toString();
    if (widget.initial['range'] is List && (widget.initial['range'] as List).length >= 2) {
      _rangeFrom = (widget.initial['range'][0]).toString();
      _rangeTo = (widget.initial['range'][1]).toString();
    }
    if (widget.initial['values'] is List && (widget.initial['values'] as List).length >= 2) {
      _rangeFrom = (widget.initial['values'][0]).toString();
      _rangeTo = (widget.initial['values'][1]).toString();
    }
    if (widget.initial['n'] != null) _n = widget.initial['n'].toString();
    if (widget.initial['n_sets'] != null) _nSets = widget.initial['n_sets'].toString();
    if (widget.initial['epsilon_percent'] != null) _epsilonPercent = widget.initial['epsilon_percent'].toString();
    if (widget.initial['value_percent'] != null) _valuePercent = widget.initial['value_percent'].toString();
    if (widget.initial['direction'] != null) _direction = widget.initial['direction'].toString();
    if (widget.initial['relation'] != null) _relation = widget.initial['relation'].toString();
  }

  @override
  void didUpdateWidget(covariant ConditionBuilder oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.metric != widget.metric) {
      final allowed = _allowedOpKeysForMetric(widget.metric);
      if (!allowed.contains(_op)) {
        WidgetsBinding.instance.addPostFrameCallback((_) {
          if (!mounted) return;
          setState(() {
            _op = '';
            _value = '';
            _rangeFrom = '';
            _rangeTo = '';
            _n = '';
            _nSets = '';
            _epsilonPercent = '';
            _valuePercent = '';
            _direction = '';
            _relation = '';
          });
          _emit();
        });
      }
    }
  }

  void _emit() {
    final map = <String, dynamic>{'op': _op};
    if (_op == 'in_range' || _op == 'not_in_range') {
      final a = double.tryParse(_rangeFrom);
      final b = double.tryParse(_rangeTo);
      if (a != null && b != null) map['range'] = [a, b];
    } else if (_op == 'holds_for') {
      if (_relation.isNotEmpty) map['relation'] = _relation;
      final isRangeRelation = _relation == 'in_range' || _relation == 'not_in_range';
      if (isRangeRelation) {
        final a = double.tryParse(_rangeFrom);
        final b = double.tryParse(_rangeTo);
        if (a != null && b != null) map['range'] = [a, b];
      } else if (_value.isNotEmpty) {
        final numVal = double.tryParse(_value);
        map['value'] = numVal ?? _value;
      }
      if (_n.isNotEmpty) map['n'] = int.tryParse(_n) ?? _n;
    } else if (_op == 'holds_for_sets') {
      if (_relation.isNotEmpty) map['relation'] = _relation;
      if (_value.isNotEmpty) {
        final numVal = double.tryParse(_value);
        map['value'] = numVal ?? _value;
      }
      if (_nSets.isNotEmpty) map['n_sets'] = int.tryParse(_nSets) ?? _nSets;
    } else {
      if (_value.isNotEmpty) {
        final numVal = double.tryParse(_value);
        map['value'] = numVal ?? _value;
      }
    }
    if (_op.startsWith('stagnates_for')) {
      if (_n.isNotEmpty) map['n'] = int.tryParse(_n) ?? _n;
      if (_epsilonPercent.isNotEmpty) map['epsilon_percent'] = double.tryParse(_epsilonPercent) ?? _epsilonPercent;
    }
    if (_op.startsWith('deviates_from_avg')) {
      if (_n.isNotEmpty) map['n'] = int.tryParse(_n) ?? _n;
      if (_valuePercent.isNotEmpty) map['value_percent'] = double.tryParse(_valuePercent) ?? _valuePercent;
      if (_direction.isNotEmpty) map['direction'] = _direction;
    }
    widget.onChanged(map);
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    final allowedOps = _allowedOpKeysForMetric(widget.metric);
    final effectiveOp = allowedOps.contains(_op) ? _op : '';
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        DropdownButtonFormField<String>(
          value: effectiveOp.isEmpty ? null : effectiveOp,
          items: _opItems(allowedOps, l10n),
          decoration: InputDecoration(labelText: l10n.macroConditionOperatorLabel, border: const OutlineInputBorder()),
          onChanged: (v) {
            setState(() => _op = v ?? '');
            _emit();
          },
          validator: (v) => (v == null || v.isEmpty) ? l10n.fieldRequired : null,
        ),
        if (effectiveOp.isNotEmpty) ...[
          const SizedBox(height: 6),
          Text(_opHelp(effectiveOp), style: Theme.of(context).textTheme.bodySmall),
          if (_metricOpHelp(effectiveOp).isNotEmpty) ...[
            const SizedBox(height: 6),
            Text(_metricOpHelp(effectiveOp), style: Theme.of(context).textTheme.bodySmall),
          ],
        ],
        const SizedBox(height: 8),
        if (effectiveOp == 'in_range' || effectiveOp == 'not_in_range')
          Row(children: [
            Expanded(
              child: TextFormField(
                initialValue: _rangeFrom,
                decoration: InputDecoration(labelText: l10n.macroConditionRangeFrom, hintText: l10n.macroConditionNumberHint, border: const OutlineInputBorder()),
                keyboardType: TextInputType.number,
                onChanged: (v) { _rangeFrom = v; _emit(); },
              ),
            ),
            const SizedBox(width: 8),
            Expanded(
              child: TextFormField(
                initialValue: _rangeTo,
                decoration: InputDecoration(labelText: l10n.macroConditionRangeTo, hintText: l10n.macroConditionNumberHint, border: const OutlineInputBorder()),
                keyboardType: TextInputType.number,
                onChanged: (v) { _rangeTo = v; _emit(); },
              ),
            ),
          ])
        else if (effectiveOp == 'stagnates_for') ...[
          TextFormField(
            initialValue: _n,
            decoration: InputDecoration(labelText: l10n.macroConditionWindowCount, hintText: l10n.macroConditionWindowCountHint, border: const OutlineInputBorder()),
            keyboardType: TextInputType.number,
            onChanged: (v) { _n = v; _emit(); },
          ),
          const SizedBox(height: 8),
          TextFormField(
            initialValue: _epsilonPercent,
            decoration: InputDecoration(labelText: l10n.macroConditionEpsilonPercent, hintText: '1.0', border: const OutlineInputBorder()),
            keyboardType: TextInputType.number,
            onChanged: (v) { _epsilonPercent = v; _emit(); },
          ),
        ] else if (_op == 'deviates_from_avg') ...[
          TextFormField(
            initialValue: _n,
            decoration: InputDecoration(labelText: l10n.macroConditionWindowCount, hintText: l10n.macroConditionNumberHint, border: const OutlineInputBorder()),
            keyboardType: TextInputType.number,
            onChanged: (v) { _n = v; _emit(); },
          ),
          const SizedBox(height: 8),
          TextFormField(
            initialValue: _valuePercent,
            decoration: InputDecoration(labelText: l10n.macroConditionValuePercent, hintText: '3.0', border: const OutlineInputBorder()),
            keyboardType: TextInputType.number,
            onChanged: (v) { _valuePercent = v; _emit(); },
          ),
          const SizedBox(height: 8),
          DropdownButtonFormField<String>(
            value: _direction.isEmpty ? null : _direction,
            items: [
              DropdownMenuItem(value: 'positive', child: Text(l10n.macroConditionPositive)),
              DropdownMenuItem(value: 'negative', child: Text(l10n.macroConditionNegative)),
            ],
            decoration: InputDecoration(labelText: l10n.macroConditionDirection, border: const OutlineInputBorder()),
            onChanged: (v) { setState(() => _direction = v ?? ''); _emit(); },
          )
        ] else if (_op == 'holds_for') ...[
          DropdownButtonFormField<String>(
            value: _relation.isEmpty ? null : _relation,
            items: [
              DropdownMenuItem(value: '>=', child: Text(l10n.macroConditionGreaterEqual)),
              DropdownMenuItem(value: '<=', child: Text(l10n.macroConditionLessEqual)),
              DropdownMenuItem(value: '==', child: Text(l10n.macroConditionEqual)),
              DropdownMenuItem(value: '!=', child: Text(l10n.macroConditionNotEqual)),
              DropdownMenuItem(value: '>', child: Text(l10n.macroConditionGreater)),
              DropdownMenuItem(value: '<', child: Text(l10n.macroConditionLess)),
              DropdownMenuItem(value: 'in_range', child: Text(l10n.macroConditionInRange)),
              DropdownMenuItem(value: 'not_in_range', child: Text(l10n.macroConditionNotInRange)),
            ],
            decoration: InputDecoration(labelText: l10n.macroConditionRelationLabel, border: const OutlineInputBorder()),
            onChanged: (v) {
              setState(() {
                _relation = v ?? '';
                if (_relation == 'in_range' || _relation == 'not_in_range') {
                  _value = '';
                }
              });
              _emit();
            },
          ),
          const SizedBox(height: 8),
          if (_relation == 'in_range' || _relation == 'not_in_range')
            Row(children: [
              Expanded(
                child: TextFormField(
                  initialValue: _rangeFrom,
                  decoration: InputDecoration(labelText: l10n.macroConditionRangeFrom, hintText: l10n.macroConditionNumberHint, border: const OutlineInputBorder()),
                  keyboardType: TextInputType.number,
                  onChanged: (v) { _rangeFrom = v; _emit(); },
                ),
              ),
              const SizedBox(width: 8),
              Expanded(
                child: TextFormField(
                  initialValue: _rangeTo,
                  decoration: InputDecoration(labelText: l10n.macroConditionRangeTo, hintText: l10n.macroConditionNumberHint, border: const OutlineInputBorder()),
                  keyboardType: TextInputType.number,
                  onChanged: (v) { _rangeTo = v; _emit(); },
                ),
              ),
            ])
          else
            TextFormField(
              initialValue: _value,
              decoration: InputDecoration(labelText: l10n.macroConditionValueLabel, hintText: '-2', border: const OutlineInputBorder()),
              keyboardType: TextInputType.number,
              onChanged: (v) { _value = v; _emit(); },
            ),
          const SizedBox(height: 8),
          TextFormField(
            initialValue: _n,
            decoration: InputDecoration(labelText: l10n.macroConditionWorkoutCount, hintText: l10n.macroConditionWorkoutCountHint, border: const OutlineInputBorder()),
            keyboardType: TextInputType.number,
            onChanged: (v) { _n = v; _emit(); },
          ),
        ] else if (_op == 'holds_for_sets') ...[
          DropdownButtonFormField<String>(
            value: _relation.isEmpty ? null : _relation,
            items: [
              DropdownMenuItem(value: '>=', child: Text(l10n.macroConditionGreaterEqual)),
              DropdownMenuItem(value: '<=', child: Text(l10n.macroConditionLessEqual)),
              DropdownMenuItem(value: '==', child: Text(l10n.macroConditionEqual)),
              DropdownMenuItem(value: '!=', child: Text(l10n.macroConditionNotEqual)),
              DropdownMenuItem(value: '>', child: Text(l10n.macroConditionGreater)),
              DropdownMenuItem(value: '<', child: Text(l10n.macroConditionLess)),
            ],
            decoration: InputDecoration(labelText: l10n.macroConditionRelationLabel, border: const OutlineInputBorder()),
            onChanged: (v) { setState(() => _relation = v ?? ''); _emit(); },
          ),
          const SizedBox(height: 8),
          TextFormField(
            initialValue: _value,
            decoration: InputDecoration(labelText: l10n.macroConditionValueLabel, hintText: l10n.macroConditionDeltaHint, border: const OutlineInputBorder()),
            keyboardType: TextInputType.number,
            onChanged: (v) { _value = v; _emit(); },
          ),
          const SizedBox(height: 8),
          TextFormField(
            initialValue: _nSets,
            decoration: InputDecoration(labelText: l10n.macroConditionSetCount, hintText: l10n.macroConditionSetCountHint, border: const OutlineInputBorder()),
            keyboardType: TextInputType.number,
            onChanged: (v) { _nSets = v; _emit(); },
          ),
        ] else ...[
          TextFormField(
            initialValue: _value,
            decoration: InputDecoration(labelText: l10n.macroConditionValueLabel, hintText: l10n.macroConditionNumberHint, border: const OutlineInputBorder()),
            keyboardType: TextInputType.number,
            onChanged: (v) { _value = v; _emit(); },
          ),
        ],
      ],
    );
  }
}
