import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:workout_app/l10n/app_localizations.dart';
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
    final l10n = AppLocalizations.of(context);
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
          label: Text(l10n.workoutsShifted(workoutsShifted.toString())),
          visualDensity: VisualDensity.compact,
        ),
      );
    }
    if (days != null) {
      final numDays = days is num ? days.toInt() : int.tryParse(days.toString());
      final sign = (numDays ?? 0) > 0 ? '+' : '';
      headerChips.add(
        Chip(
          label: Text(l10n.shiftDays(sign, (numDays ?? days).toString())),
          visualDensity: VisualDensity.compact,
        ),
      );
    }


    final filterLines = <String>[];
    if (fromDate != null && fromDate.isNotEmpty) {
      filterLines.add(l10n.startingFrom(fromDate));
    }
    if (toDate != null && toDate.isNotEmpty) {
      filterLines.add(l10n.upToDate(toDate));
    }

    if (actionType == 'set_rest') {
      filterLines.add(l10n.modeChangeIntervals);
    } else {
      filterLines.add(l10n.modeScheduleShift);
    }

    if (onlyFuture) {
      filterLines.add(l10n.onlyFutureWorkouts);
    }
    if (statusIn is List && statusIn.isNotEmpty) {
      filterLines.add(l10n.statuses(statusIn.join(', ')));
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
            l10n.shiftParameters,
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
          label: Text(l10n.apply),
          style: ElevatedButton.styleFrom(
            backgroundColor: colorScheme.primary,
            foregroundColor: colorScheme.onPrimary,
          ),
        ),
      );
    }

    final titleText = isPreview
        ? l10n.scheduleShiftPreviewTitle
        : l10n.scheduleShiftTitle;

    return ToolResultCard(
      title: titleText,
      icon: Icons.calendar_today_rounded,
      content: content,
      actions: actions,
      isPreview: isPreview,
    );
  }
}
