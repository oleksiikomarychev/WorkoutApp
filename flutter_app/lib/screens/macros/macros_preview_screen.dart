import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:workout_app/providers/macro_preview_providers.dart';
import 'package:workout_app/providers/macro_context_providers.dart';
import 'package:workout_app/widgets/primary_app_bar.dart';
import 'package:workout_app/widgets/assistant_chat_host.dart';

class MacrosPreviewScreen extends ConsumerStatefulWidget {
  final int appliedPlanId;
  const MacrosPreviewScreen({super.key, required this.appliedPlanId});

  @override
  ConsumerState<MacrosPreviewScreen> createState() => _MacrosPreviewScreenState();
}

List<Widget> _buildGroupedPatchesWithDiffs(List patches, String Function(int) wname, String Function(int?) ename, Map<int, Map<int?, Map<int?, Map<String, dynamic>>>> originals) {
  final Map<int, Map<int?, List<Map<String, dynamic>>>> grouped = {};
  for (final p in patches) {
    final mp = (p as Map).cast<String, dynamic>();
    final wid = (mp['workout_id'] as num).toInt();
    final eid = (mp['exercise_id'] as num?)?.toInt();
    grouped.putIfAbsent(wid, () => {});
    grouped[wid]!.putIfAbsent(eid, () => []);
    grouped[wid]![eid]!.add(mp);
  }
  final widgets = <Widget>[];
  grouped.forEach((wid, byEx) {
    widgets.add(Padding(
      padding: const EdgeInsets.symmetric(vertical: 4),
      child: Text('• ${wname(wid)}', style: const TextStyle(fontWeight: FontWeight.w600)),
    ));
    byEx.forEach((eid, items) {
      widgets.add(Padding(
        padding: const EdgeInsets.only(left: 12, bottom: 2),
        child: Text('↳ ${ename(eid)} (${items.length} change${items.length == 1 ? '' : 's'})'),
      ));
      for (final mp in items) {
        final sid = mp['set_id'] as int?;
        final changes = (mp['changes'] as Map? ?? const {}).cast<String, dynamic>();
        final before = originals[wid]?[eid]?[sid] ?? const {};
        final diffs = <String>[];
        void addDiff(String key, String label) {
          if (!changes.containsKey(key)) return;
          final after = changes[key];
          final b = before[key];
          if (b == null) {
            diffs.add('$label: → $after');
          } else {
            diffs.add('$label: $b → $after');
          }
        }
        addDiff('intensity', 'intensity');
        addDiff('volume', 'reps');
        addDiff('weight', 'weight');
        addDiff('working_weight', 'weight');
        // structural actions
        if (changes['action'] == 'add_set') {
          diffs.add('add set');
        } else if (changes['action'] == 'remove_set') {
          diffs.add('remove set');
        }
        widgets.add(Padding(
          padding: const EdgeInsets.only(left: 24, bottom: 4),
          child: Text('Set ${sid ?? '-'} → ${diffs.isEmpty ? changes.toString() : diffs.join(', ')}'),
        ));
      }
    });
  });
  return widgets;
}

class _MacrosPreviewScreenState extends ConsumerState<MacrosPreviewScreen> {
  @override
  void initState() {
    super.initState();
    Future.microtask(() => ref.read(macroPreviewNotifierProvider.notifier).runPreview(widget.appliedPlanId));
  }

  @override
  Widget build(BuildContext context) {
    final st = ref.watch(macroPreviewNotifierProvider);
    final ctxData = ref.watch(previewContextProvider(widget.appliedPlanId)).maybeWhen(
      data: (d) => d,
      orElse: () => null,
    );
    final notifier = ref.read(macroPreviewNotifierProvider.notifier);

    final preview = st.preview;
    final items = (preview != null ? (preview['preview'] as List? ?? const []) : const []) as List;

    return AssistantChatHost(
      builder: (context, openChat) {
        return Scaffold(
          appBar: PrimaryAppBar(
            title: 'Macros Preview (applied_plan_id=${widget.appliedPlanId})',
            onTitleTap: openChat,
            actions: [
              IconButton(
                icon: const Icon(Icons.refresh),
                onPressed: st.loading ? null : () => notifier.runPreview(widget.appliedPlanId),
              ),
            ],
          ),
          body: st.loading
          ? const Center(child: CircularProgressIndicator())
          : (st.error != null)
              ? Center(child: Text('Error: ${st.error}'))
              : items.isEmpty
                  ? const Center(child: Text('No changes suggested'))
                  : ListView.builder(
                      itemCount: items.length,
                      itemBuilder: (context, index) {
                        final it = (items[index] as Map).cast<String, dynamic>();
                        final patches = (it['patches'] as List? ?? const []) as List;
                        final matched = (it['matched_workouts'] as List? ?? const []) as List;
                        String _wname(int id) => ctxData?.workoutNames[id] ?? '#$id';
                        String _ename(int? id) => id == null ? '-' : (ctxData?.exerciseNames[id] ?? '#$id');
                        // Counters
                        final perWorkoutCounts = <int, int>{};
                        for (final p in patches) {
                          final mp = (p as Map).cast<String, dynamic>();
                          final wid = (mp['workout_id'] as num).toInt();
                          perWorkoutCounts.update(wid, (v) => v + 1, ifAbsent: () => 1);
                        }
                        final workoutIds = perWorkoutCounts.keys.toList()..sort();
                        final originalsAsync = ref.watch(workoutOriginalSetsProvider(workoutIds));
                        return Card(
                          margin: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                          child: Padding(
                            padding: const EdgeInsets.all(12),
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Text('${it['name']} (prio ${it['priority']})', style: Theme.of(context).textTheme.titleMedium),
                                Text('Patches: ${patches.length} across ${perWorkoutCounts.length} workouts'),
                                const SizedBox(height: 4),
                                Text('Matched workouts: ${matched.map((e) => _wname(e as int)).join(', ')}'),
                                const SizedBox(height: 8),
                                if (patches.isEmpty) const Text('No patches') else ...[
                                  const Text('Patches (grouped + diffs):'),
                                  const SizedBox(height: 6),
                                  originalsAsync.when(
                                    data: (orig) => Column(children: _buildGroupedPatchesWithDiffs(patches, _wname, _ename, orig)),
                                    loading: () => const LinearProgressIndicator(minHeight: 2),
                                    error: (_, __) => Column(children: _buildGroupedPatches(patches, _wname, _ename)),
                                  ),
                                ]
                              ],
                            ),
                          ),
                        );
                      },
                    ),
          bottomNavigationBar: SafeArea(
            child: Padding(
              padding: const EdgeInsets.all(12.0),
              child: FilledButton.icon(
            onPressed: (st.loading || (items.isEmpty)) ? null : () async {
              final confirm = await showDialog<bool>(
                context: context,
                builder: (_) => AlertDialog(
                  title: const Text('Apply Macros'),
                  content: const Text('Apply suggested changes to future workouts?'),
                  actions: [
                    TextButton(onPressed: () => Navigator.pop(context, false), child: const Text('Cancel')),
                    FilledButton(onPressed: () => Navigator.pop(context, true), child: const Text('Apply')),
                  ],
                ),
              );
              if (confirm == true) {
                await notifier.apply(widget.appliedPlanId);
                if (!mounted) return;
                final res = ref.read(macroPreviewNotifierProvider).applyResult;
                final msg = res != null ? 'Applied: ${res['applied']}\nErrors: ${(res['errors'] ?? []).length}' : 'Done';
                ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(msg)));
                // Auto-refresh preview after apply
                await notifier.runPreview(widget.appliedPlanId);
              }
            },
            icon: const Icon(Icons.check),
            label: const Text('Apply changes'),
          ),
        ),
      ),
    );
      },
    );
  }
}

List<Widget> _buildGroupedPatches(List patches, String Function(int) wname, String Function(int?) ename) {
  // Build: workoutId -> exerciseId -> list of sets
  final Map<int, Map<int?, List<Map<String, dynamic>>>> grouped = {};
  for (final p in patches) {
    final mp = (p as Map).cast<String, dynamic>();
    final wid = (mp['workout_id'] as num).toInt();
    final eid = (mp['exercise_id'] as num?)?.toInt();
    grouped.putIfAbsent(wid, () => {});
    grouped[wid]!.putIfAbsent(eid, () => []);
    grouped[wid]![eid]!.add(mp);
  }
  final widgets = <Widget>[];
  grouped.forEach((wid, byEx) {
    widgets.add(Padding(
      padding: const EdgeInsets.symmetric(vertical: 4),
      child: Text('• ${wname(wid)}', style: const TextStyle(fontWeight: FontWeight.w600)),
    ));
    byEx.forEach((eid, items) {
      widgets.add(Padding(
        padding: const EdgeInsets.only(left: 12, bottom: 2),
        child: Text('↳ ${ename(eid)} (${items.length} change${items.length == 1 ? '' : 's'})'),
      ));
      for (final mp in items) {
        final sid = mp['set_id'];
        final changes = (mp['changes'] as Map? ?? const {}).cast<String, dynamic>();
        widgets.add(Padding(
          padding: const EdgeInsets.only(left: 24, bottom: 4),
          child: Text('Set ${sid ?? '-'} → ${changes.toString()}'),
        ));
      }
    });
  });
  return widgets;
}
