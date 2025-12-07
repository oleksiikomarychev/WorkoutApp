import 'package:flutter/material.dart';

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

  String _opLabel(String op) {
    switch (op) {
      case '>':
        return 'больше >';
      case '<':
        return 'меньше <';
      case '=':
        return 'равно =';
      case '!=':
        return 'не равно ≠';
      case 'in_range':
        return 'в диапазоне';
      case 'not_in_range':
        return 'вне диапазона';
      case 'stagnates_for':
        return 'стагнация за N окон';
      case 'deviates_from_avg':
        return 'отклонение от среднего';
      case 'holds_for':
        return 'выполняется N тренировок подряд';
      case 'holds_for_sets':
        return 'выполняется N подходов подряд (внутри тренировки)';
      default:
        return op;
    }
  }

  List<DropdownMenuItem<String>> _opItems(List<String> keys) {
    return keys
        .map((k) => DropdownMenuItem<String>(value: k, child: Text(_opLabel(k))))
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
    final allowedOps = _allowedOpKeysForMetric(widget.metric);
    final effectiveOp = allowedOps.contains(_op) ? _op : '';
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        DropdownButtonFormField<String>(
          value: effectiveOp.isEmpty ? null : effectiveOp,
          items: _opItems(allowedOps),
          decoration: const InputDecoration(labelText: 'Оператор', border: OutlineInputBorder()),
          onChanged: (v) {
            setState(() => _op = v ?? '');
            _emit();
          },
          validator: (v) => (v == null || v.isEmpty) ? 'Required' : null,
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
                decoration: const InputDecoration(labelText: 'от', hintText: 'число', border: OutlineInputBorder()),
                keyboardType: TextInputType.number,
                onChanged: (v) { _rangeFrom = v; _emit(); },
              ),
            ),
            const SizedBox(width: 8),
            Expanded(
              child: TextFormField(
                initialValue: _rangeTo,
                decoration: const InputDecoration(labelText: 'до', hintText: 'число', border: OutlineInputBorder()),
                keyboardType: TextInputType.number,
                onChanged: (v) { _rangeTo = v; _emit(); },
              ),
            ),
          ])
        else if (effectiveOp == 'stagnates_for') ...[
          TextFormField(
            initialValue: _n,
            decoration: const InputDecoration(labelText: 'n (окон)', hintText: 'целое число, например 5', border: OutlineInputBorder()),
            keyboardType: TextInputType.number,
            onChanged: (v) { _n = v; _emit(); },
          ),
          const SizedBox(height: 8),
          TextFormField(
            initialValue: _epsilonPercent,
            decoration: const InputDecoration(labelText: 'epsilon_percent (порог, %)', hintText: 'например 1.0', border: OutlineInputBorder()),
            keyboardType: TextInputType.number,
            onChanged: (v) { _epsilonPercent = v; _emit(); },
          ),
        ] else if (_op == 'deviates_from_avg') ...[
          TextFormField(
            initialValue: _n,
            decoration: const InputDecoration(labelText: 'n (окон)', hintText: 'целое число', border: OutlineInputBorder()),
            keyboardType: TextInputType.number,
            onChanged: (v) { _n = v; _emit(); },
          ),
          const SizedBox(height: 8),
          TextFormField(
            initialValue: _valuePercent,
            decoration: const InputDecoration(labelText: 'value_percent (откл., %)', hintText: 'например 3.0', border: OutlineInputBorder()),
            keyboardType: TextInputType.number,
            onChanged: (v) { _valuePercent = v; _emit(); },
          ),
          const SizedBox(height: 8),
          DropdownButtonFormField<String>(
            value: _direction.isEmpty ? null : _direction,
            items: const [
              DropdownMenuItem(value: 'positive', child: Text('положительное')),
              DropdownMenuItem(value: 'negative', child: Text('отрицательное')),
            ],
            decoration: const InputDecoration(labelText: 'направление (необязательно)', border: OutlineInputBorder()),
            onChanged: (v) { setState(() => _direction = v ?? ''); _emit(); },
          )
        ] else if (_op == 'holds_for') ...[
          DropdownButtonFormField<String>(
            value: _relation.isEmpty ? null : _relation,
            items: const [
              DropdownMenuItem(value: '>=', child: Text('больше или равно ≥')),
              DropdownMenuItem(value: '<=', child: Text('меньше или равно ≤')),
              DropdownMenuItem(value: '==', child: Text('равно =')),
              DropdownMenuItem(value: '!=', child: Text('не равно ≠')),
              DropdownMenuItem(value: '>', child: Text('больше >')),
              DropdownMenuItem(value: '<', child: Text('меньше <')),
              DropdownMenuItem(value: 'in_range', child: Text('в диапазоне')),
              DropdownMenuItem(value: 'not_in_range', child: Text('вне диапазона')),
            ],
            decoration: const InputDecoration(labelText: 'сравнение', border: OutlineInputBorder()),
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
                  decoration: const InputDecoration(labelText: 'от', hintText: 'число', border: OutlineInputBorder()),
                  keyboardType: TextInputType.number,
                  onChanged: (v) { _rangeFrom = v; _emit(); },
                ),
              ),
              const SizedBox(width: 8),
              Expanded(
                child: TextFormField(
                  initialValue: _rangeTo,
                  decoration: const InputDecoration(labelText: 'до', hintText: 'число', border: OutlineInputBorder()),
                  keyboardType: TextInputType.number,
                  onChanged: (v) { _rangeTo = v; _emit(); },
                ),
              ),
            ])
          else
            TextFormField(
              initialValue: _value,
              decoration: const InputDecoration(labelText: 'значение', hintText: 'порог, например -2', border: OutlineInputBorder()),
              keyboardType: TextInputType.number,
              onChanged: (v) { _value = v; _emit(); },
            ),
          const SizedBox(height: 8),
          TextFormField(
            initialValue: _n,
            decoration: const InputDecoration(labelText: 'n (тренировок)', hintText: 'целое, например 3', border: OutlineInputBorder()),
            keyboardType: TextInputType.number,
            onChanged: (v) { _n = v; _emit(); },
          ),
        ] else if (_op == 'holds_for_sets') ...[
          DropdownButtonFormField<String>(
            value: _relation.isEmpty ? null : _relation,
            items: const [
              DropdownMenuItem(value: '>=', child: Text('больше или равно ≥')),
              DropdownMenuItem(value: '<=', child: Text('меньше или равно ≤')),
              DropdownMenuItem(value: '==', child: Text('равно =')),
              DropdownMenuItem(value: '!=', child: Text('не равно ≠')),
              DropdownMenuItem(value: '>', child: Text('больше >')),
              DropdownMenuItem(value: '<', child: Text('меньше <')),
            ],
            decoration: const InputDecoration(labelText: 'сравнение', border: OutlineInputBorder()),
            onChanged: (v) { setState(() => _relation = v ?? ''); _emit(); },
          ),
          const SizedBox(height: 8),
          TextFormField(
            initialValue: _value,
            decoration: const InputDecoration(labelText: 'значение', hintText: 'дельта, например -2 для повторов', border: OutlineInputBorder()),
            keyboardType: TextInputType.number,
            onChanged: (v) { _value = v; _emit(); },
          ),
          const SizedBox(height: 8),
          TextFormField(
            initialValue: _nSets,
            decoration: const InputDecoration(labelText: 'n (подряд подходов)', hintText: 'целое, например 12', border: OutlineInputBorder()),
            keyboardType: TextInputType.number,
            onChanged: (v) { _nSets = v; _emit(); },
          ),
        ] else ...[
          TextFormField(
            initialValue: _value,
            decoration: const InputDecoration(labelText: 'значение', hintText: 'число', border: OutlineInputBorder()),
            keyboardType: TextInputType.number,
            onChanged: (v) { _value = v; _emit(); },
          ),
        ],
      ],
    );
  }
}
