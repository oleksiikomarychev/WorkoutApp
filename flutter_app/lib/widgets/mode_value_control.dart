import 'package:flutter/material.dart';

enum ParamMode { set, offset, scale }

class ModeValue {
  ParamMode mode;
  double value;
  ModeValue({required this.mode, required this.value});
}

class ModeValueControl extends StatelessWidget {
  final String label;
  final bool enabled;
  final ValueChanged<bool> onEnabledChanged;
  final ModeValue value;
  final ValueChanged<ModeValue> onChanged;

  final List<ParamMode> allowedModes;
  final Map<ParamMode, String> modeTitles;


  final String Function(ParamMode, double) displayTextBuilder;
  final double Function(ParamMode) stepForMode;


  final double? setMin;
  final double? setMax;

  final double? scaleMin;

  const ModeValueControl({
    super.key,
    required this.label,
    required this.enabled,
    required this.onEnabledChanged,
    required this.value,
    required this.onChanged,
    required this.allowedModes,
    required this.modeTitles,
    required this.displayTextBuilder,
    required this.stepForMode,
    this.setMin,
    this.setMax,
    this.scaleMin,
  });

  @override
  Widget build(BuildContext context) {
    String _labelForMode(ParamMode m) {
      final fromMap = modeTitles[m];
      if (fromMap != null) return fromMap;

      final s = m.toString();
      final idx = s.indexOf('.');
      return idx >= 0 ? s.substring(idx + 1) : s;
    }
    final canUseScale = allowedModes.contains(ParamMode.scale);
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            Switch(
              value: enabled,
              onChanged: onEnabledChanged,
            ),
            Text(label, style: Theme.of(context).textTheme.bodyMedium),
            const Spacer(),
            SizedBox(
              width: 220,
              child: DropdownButtonFormField<ParamMode>(
                value: value.mode,
                items: allowedModes
                    .map((m) => DropdownMenuItem(
                          value: m,
                          child: Text(_labelForMode(m)),
                        ))
                    .toList(),
                onChanged: enabled
                    ? (m) {
                        if (m == null) return;
                        onChanged(ModeValue(mode: m, value: value.value));
                      }
                    : null,
              ),
            ),
          ],
        ),
        const SizedBox(height: 6),
        Row(
          children: [
            const SizedBox(width: 48),
            FilledButton.tonal(
              onPressed: enabled
                  ? () {
                      final step = stepForMode(value.mode);
                      double newVal = value.value;
                      if (value.mode == ParamMode.scale) {
                        newVal = (newVal - step);
                        if (scaleMin != null && newVal < scaleMin!) newVal = scaleMin!;
                      } else if (value.mode == ParamMode.set) {
                        newVal = (newVal - step);
                        if (setMin != null && newVal < setMin!) newVal = setMin!;
                      } else {
                        newVal = (newVal - step);
                      }
                      onChanged(ModeValue(mode: value.mode, value: newVal));
                    }
                  : null,
              child: const Icon(Icons.remove),
            ),
            const SizedBox(width: 8),
            Expanded(
              child: Container(
                padding: const EdgeInsets.symmetric(vertical: 10, horizontal: 12),
                decoration: BoxDecoration(
                  border: Border.all(color: Theme.of(context).dividerColor),
                  borderRadius: BorderRadius.circular(8),
                ),
                child: Text(
                  displayTextBuilder(value.mode, value.value),
                  textAlign: TextAlign.center,
                ),
              ),
            ),
            const SizedBox(width: 8),
            FilledButton.tonal(
              onPressed: enabled
                  ? () {
                      final step = stepForMode(value.mode);
                      double newVal = value.value;
                      if (value.mode == ParamMode.scale) {
                        newVal = (newVal + step);
                      } else if (value.mode == ParamMode.set) {
                        newVal = (newVal + step);
                        if (setMax != null && newVal > setMax!) newVal = setMax!;
                      } else {
                        newVal = (newVal + step);
                      }
                      onChanged(ModeValue(mode: value.mode, value: newVal));
                    }
                  : null,
              child: const Icon(Icons.add),
            ),
          ],
        ),
      ],
    );
  }
}
