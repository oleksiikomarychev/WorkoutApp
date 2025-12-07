import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'mass_edit_tool_widget.dart';
import 'schedule_shift_tool_widget.dart';


class ToolWidgetFactory extends ConsumerWidget {
  const ToolWidgetFactory({
    super.key,
    required this.payload,
  });

  final Map<String, dynamic> payload;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final variant = payload['variant']?.toString();


    switch (variant) {
      case 'applied_plan':
        return MassEditToolWidget(payload: payload);
      case 'applied_schedule_shift':
        return ScheduleShiftToolWidget(payload: payload);
      default:
        return const SizedBox.shrink();
    }
  }
}
