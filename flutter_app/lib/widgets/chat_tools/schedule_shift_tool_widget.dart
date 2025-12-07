import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:workout_app/providers/chat_provider.dart';

import 'mass_edit_tool_widget.dart';








class ScheduleShiftToolWidget extends ConsumerWidget {
  const ScheduleShiftToolWidget({
    super.key,
    required this.payload,
  });

  final Map<String, dynamic> payload;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final mode = payload['mode']?.toString();
    final isPreview = mode == 'preview';

    final summaryRaw = payload['summary'];
    final summary = summaryRaw is Map<String, dynamic>
        ? summaryRaw
        : const <String, dynamic>{};

    final workoutsShifted = summary['workouts_shifted'] ?? summary['affected_count'];
    final days = payload['days'] ?? summary['days'];
    final actionType = (payload['action_type'] ?? summary['action_type'] ?? 'shift').toString();
    final fromDate = payload['from_date']?.toString();


    final toDate = payload['to_date']?.toString();
    final onlyFuture = payload['only_future'] == true;
    final statusIn = payload['status_in'];

    final theme = Theme.of(context);
    final colorScheme = theme.colorScheme;


    final headerChips = <Widget>[];
    if (workoutsShifted != null) {
      headerChips.add(
        Chip(
          label: Text('Тренировок сдвинуто: $workoutsShifted'),
          visualDensity: VisualDensity.compact,
        ),
      );
    }
    if (days != null) {
      final numDays = days is num ? days.toInt() : int.tryParse(days.toString());
      final sign = (numDays ?? 0) > 0 ? '+' : '';
      headerChips.add(
        Chip(
          label: Text('Сдвиг: $sign${numDays ?? days} дн.'),
          visualDensity: VisualDensity.compact,
        ),
      );
    }


    final filterLines = <String>[];
    if (fromDate != null && fromDate.isNotEmpty) {
      filterLines.add('Начиная с: $fromDate');
    }
    if (toDate != null && toDate.isNotEmpty) {
      filterLines.add('До даты (включительно): $toDate');
    }

    if (actionType == 'set_rest') {
      filterLines.add('Режим: изменить интервалы между тренировками');
    } else {
      filterLines.add('Режим: сдвиг расписания');
    }

    if (onlyFuture) {
      filterLines.add('Только будущие тренировки');
    }
    if (statusIn is List && statusIn.isNotEmpty) {
      filterLines.add('Статусы: ${statusIn.join(', ')}');
    }

    final content = Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        if (headerChips.isNotEmpty)
          Wrap(
            spacing: 8,
            runSpacing: 4,
            children: headerChips,
          ),
        if (filterLines.isNotEmpty) ...[
          const SizedBox(height: 8),
          Text(
            'Параметры сдвига',
            style: theme.textTheme.labelLarge?.copyWith(
              color: colorScheme.primary,
              fontWeight: FontWeight.w600,
            ),
          ),
          const SizedBox(height: 4),
          ...filterLines.map(
            (line) => Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text('• '),
                Expanded(
                  child: Text(
                    line,
                    style: theme.textTheme.bodySmall,
                  ),
                ),
              ],
            ),
          ),
        ],
      ],
    );

    final List<Widget> actions = [];
    final command = payload['schedule_shift_command'];
    if (isPreview && command is Map<String, dynamic>) {
      actions.add(
        ElevatedButton.icon(
          onPressed: () {
            ref
                .read(chatControllerProvider.notifier)
                .applyScheduleShiftFromPreview(payload);
          },
          icon: const Icon(Icons.check_rounded),
          label: const Text('Применить'),
          style: ElevatedButton.styleFrom(
            backgroundColor: colorScheme.primary,
            foregroundColor: colorScheme.onPrimary,
          ),
        ),
      );
    }

    const titleText = 'Сдвиг расписания активного плана выполнен';

    return ToolResultCard(
      title: titleText,
      icon: Icons.calendar_today_rounded,
      content: content,
      actions: actions,
      isPreview: isPreview,
    );
  }
}
