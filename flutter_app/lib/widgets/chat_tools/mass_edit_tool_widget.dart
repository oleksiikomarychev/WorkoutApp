import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:workout_app/l10n/app_localizations.dart';
import 'package:workout_app/providers/chat_provider.dart';
import 'package:workout_app/providers/target_data_providers.dart';

class ToolResultCard extends ConsumerWidget {
  const ToolResultCard({
    super.key,
    required this.title,
    required this.icon,
    required this.content,
    this.actions,
    this.isPreview = false,
  });

  final String title;
  final IconData icon;
  final Widget content;
  final List<Widget>? actions;
  final bool isPreview;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final theme = Theme.of(context);
    final colorScheme = theme.colorScheme;

    final l10n = AppLocalizations.of(context);

    return Card(
      elevation: 2,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
      child: Padding(
        padding: const EdgeInsets.all(14.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [

            Row(
              children: [
                Icon(icon, color: colorScheme.primary),
                const SizedBox(width: 8),
                Expanded(
                  child: Text(
                    title,
                    style: theme.textTheme.titleSmall?.copyWith(
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 12),


            content,

            const SizedBox(height: 12),


            Row(
              mainAxisAlignment: MainAxisAlignment.end,
              children: [
                TextButton.icon(
                  onPressed: () {

                    ref.read(chatControllerProvider.notifier).clearMassEditResult();
                  },
                  icon: const Icon(Icons.close_rounded),
                  label: Text(l10n.hide),
                ),
                if (actions != null) ...[
                  const SizedBox(width: 8),
                  ...actions!,
                ],
              ],
            ),
          ],
        ),
      ),
    );
  }
}

class MassEditToolWidget extends ConsumerWidget {
  const MassEditToolWidget({
    super.key,
    required this.payload,
  });

  final Map<String, dynamic> payload;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final l10n = AppLocalizations.of(context);
    final mode = payload['mode']?.toString();
    final isPreview = mode == 'preview';
    final exerciseNameMap = ref.watch(exerciseDefinitionNameMapProvider);


    final summaryRaw = payload['summary'];
    final summary = summaryRaw is Map<String, dynamic> ? summaryRaw : <String, dynamic>{};
    final commandRaw = payload['mass_edit_command'];
    final command = commandRaw is Map<String, dynamic> ? commandRaw : <String, dynamic>{};
    final filterRaw = command['filter'];
    final filter = filterRaw is Map<String, dynamic> ? filterRaw : <String, dynamic>{};
    final actionsRaw = command['actions'];
    final actions = actionsRaw is Map<String, dynamic> ? actionsRaw : <String, dynamic>{};

    final workoutsMatched = summary['workouts_matched'] ?? summary['workouts_shifted'];
    final setsMatched = summary['sets_matched'];
    final setsModified = summary['sets_modified'];

    final dynamic setsCount = isPreview
        ? (setsMatched ?? setsModified)
        : (setsModified ?? setsMatched);


    final filterLines = <String>[];
    final onlyFuture = filter['only_future'] == true;
    final scheduledFrom = filter['scheduled_from']?.toString();
    final scheduledTo = filter['scheduled_to']?.toString();
    final statusIn = filter['status_in'];
    final exerciseIds = filter['exercise_definition_ids'];

    if (onlyFuture) filterLines.add(l10n.onlyFutureWorkouts);
    if (scheduledFrom != null && scheduledFrom.isNotEmpty) filterLines.add(l10n.dateNotEarlierThan(scheduledFrom));
    if (scheduledTo != null && scheduledTo.isNotEmpty) filterLines.add(l10n.dateNotLaterThan(scheduledTo));
    if (statusIn is List && statusIn.isNotEmpty) filterLines.add(l10n.statuses(statusIn.join(', ')));

    if (exerciseIds is List && exerciseIds.isNotEmpty) {
      final names = <String>[];
      for (final rawId in exerciseIds) {
        final id = rawId is num ? rawId.toInt() : int.tryParse(rawId.toString());
        if (id == null) continue;
        final name = exerciseNameMap[id];
        if (name != null && name.isNotEmpty) {
          names.add('$name (ID $id)');
        } else {
          names.add('ID $id');
        }
      }
      if (names.isNotEmpty) {
        filterLines.add(l10n.exercises(names.join(', ')));
      }
    }


    final actionLines = <String>[];
    void addActionLine(String key, String Function(num v) textBuilder) {
      final raw = actions[key];
      if (raw is num) {
        actionLines.add(textBuilder(raw));
      }
    }

    addActionLine('set_intensity', (v) => l10n.setIntensity(v.toString()));
    addActionLine('increase_intensity_by', (v) => l10n.increaseIntensityBy(v.toString()));
    addActionLine('decrease_intensity_by', (v) => l10n.decreaseIntensityBy(v.toString()));
    addActionLine('set_volume', (v) => l10n.setVolume(v.toStringAsFixed(0)));
    addActionLine('increase_volume_by', (v) => l10n.increaseVolumeBy(v.toStringAsFixed(0)));
    addActionLine('decrease_volume_by', (v) => l10n.decreaseVolumeBy(v.toStringAsFixed(0)));
    addActionLine('set_weight', (v) => l10n.setWeight(v.toString()));
    addActionLine('increase_weight_by', (v) => l10n.increaseWeightBy(v.toString()));
    addActionLine('decrease_weight_by', (v) => l10n.decreaseWeightBy(v.toString()));
    addActionLine('set_effort', (v) => l10n.setEffort(v.toString()));
    addActionLine('increase_effort_by', (v) => l10n.increaseEffortBy(v.toString()));
    addActionLine('decrease_effort_by', (v) => l10n.decreaseEffortBy(v.toString()));

    if (actions['clamp_non_negative'] == true) {
      actionLines.add(l10n.clampNonNegative);
    }

    final replaceId = actions['replace_exercise_definition_id_to'];
    if (replaceId is num) {
      final id = replaceId.toInt();
      final name = exerciseNameMap[id];
      if (name != null && name.isNotEmpty) {
        actionLines.add(l10n.replaceExerciseTo(name, id.toString()));
      } else {
        actionLines.add(l10n.replaceExerciseTo('', id.toString()));
      }
    }
    final replaceName = actions['replace_exercise_name_to']?.toString();
    if (replaceName != null && replaceName.isNotEmpty) {
      actionLines.add(l10n.renameExerciseTo(replaceName));
    }

    final addInstances = actions['add_exercise_instances'];
    if (addInstances is List && addInstances.isNotEmpty) {
      actionLines.add(l10n.addNewExercises(addInstances.length.toString()));
    }


    final theme = Theme.of(context);
    final colorScheme = theme.colorScheme;

    final titleText = isPreview
        ? l10n.massEditPreviewTitle
        : l10n.massEditAppliedTitle;

    final content = Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        if (workoutsMatched != null || setsCount != null)
          Wrap(
            spacing: 8,
            runSpacing: 4,
            children: [
              if (workoutsMatched != null)
                Chip(
                  label: Text(l10n.massEditToolWorkoutsMatched(workoutsMatched.toString())),
                  visualDensity: VisualDensity.compact,
                ),
              if (setsCount != null)
                Chip(
                  label: Text(
                    isPreview
                        ? l10n.massEditToolSetsToBeModified(setsCount.toString())
                        : l10n.massEditToolSetsModified(setsCount.toString()),
                  ),
                  visualDensity: VisualDensity.compact,
                ),
            ],
          ),
        if (filterLines.isNotEmpty) ...[
          const SizedBox(height: 8),
          Text(
            l10n.filter,
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
                Expanded(child: Text(line, style: theme.textTheme.bodySmall)),
              ],
            ),
          ),
        ],
        if (actionLines.isNotEmpty) ...[
          const SizedBox(height: 8),
          Text(
            l10n.changes,
            style: theme.textTheme.labelLarge?.copyWith(
              color: colorScheme.primary,
              fontWeight: FontWeight.w600,
            ),
          ),
          const SizedBox(height: 4),
          ...actionLines.map(
            (line) => Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text('• '),
                Expanded(child: Text(line, style: theme.textTheme.bodySmall)),
              ],
            ),
          ),
        ],
      ],
    );


    final List<Widget> actionsList = [];
    if (isPreview && command.isNotEmpty) {
      actionsList.add(
        ElevatedButton.icon(
          onPressed: () {
            ref
                .read(chatControllerProvider.notifier)
                .applyMassEditFromPreview(payload);
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

    return ToolResultCard(
      title: titleText,
      icon: Icons.auto_fix_high_rounded,
      content: content,
      actions: actionsList,
      isPreview: isPreview,
    );
  }
}
