import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:workout_app/models/macro.dart';
import 'package:workout_app/providers/macro_providers.dart';
import 'package:workout_app/screens/macros/macro_editor_screen.dart';
import 'package:workout_app/screens/macros/macros_preview_screen.dart';
import 'package:workout_app/providers/plan_providers.dart';
import 'package:workout_app/widgets/primary_app_bar.dart';
import 'package:workout_app/widgets/assistant_chat_host.dart';

class MacrosListScreen extends ConsumerWidget {
  final int calendarPlanId;
  const MacrosListScreen({super.key, required this.calendarPlanId});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final state = ref.watch(macrosNotifierProvider(calendarPlanId));
    final notifier = ref.read(macrosNotifierProvider(calendarPlanId).notifier);

    return AssistantChatHost(
      builder: (context, openChat) {
        return Scaffold(
          appBar: PrimaryAppBar(
            title: 'Plan Macros',
            onTitleTap: openChat,
            actions: [
              IconButton(
                icon: const Icon(Icons.visibility),
                tooltip: 'Preview/Apply',
                onPressed: () async {
                  final active = await ref.read(activeAppliedPlanProvider.future);
                  final id = active?.id;
                  if (id == null) {
                    if (!context.mounted) return;
                    ScaffoldMessenger.of(context).showSnackBar(
                      const SnackBar(content: Text('Active plan not found')),
                    );
                    return;
                  }
                  if (!context.mounted) return;
                  Navigator.of(context).push(
                    MaterialPageRoute(builder: (_) => MacrosPreviewScreen(appliedPlanId: id)),
                  );
                },
              )
            ],
          ),
          body: RefreshIndicator(
        onRefresh: () async => notifier.load(),
        child: state.loading
            ? const Center(child: CircularProgressIndicator())
            : state.items.isEmpty
                ? const Center(child: Text('No macros yet'))
                : ListView.separated(
                    itemCount: state.items.length,
                    separatorBuilder: (_, __) => const Divider(height: 1),
                    itemBuilder: (context, index) {
                      final m = state.items[index];
                      return ListTile(
                        leading: CircleAvatar(child: Text('${m.priority}')),
                        title: Text(m.name),
                        subtitle: Text('Active: ${m.isActive}  |  id: ${m.id ?? '-'}'),
                        trailing: Row(
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            IconButton(
                              icon: const Icon(Icons.edit),
                              onPressed: () async {
                                final updated = await Navigator.of(context).push<PlanMacro>(
                                  MaterialPageRoute(
                                    builder: (_) => MacroEditorScreen(
                                      initial: m,
                                      calendarPlanId: calendarPlanId,
                                    ),
                                  ),
                                );
                                if (updated != null) {
                                  // on return, notifier already updated via editor save
                                }
                              },
                            ),
                            IconButton(
                              icon: const Icon(Icons.delete_outline),
                              onPressed: () async {
                                final confirm = await showDialog<bool>(
                                  context: context,
                                  builder: (_) => AlertDialog(
                                    title: const Text('Delete Macro'),
                                    content: Text('Are you sure to delete "${m.name}"?'),
                                    actions: [
                                      TextButton(onPressed: () => Navigator.pop(context, false), child: const Text('Cancel')),
                                      FilledButton(onPressed: () => Navigator.pop(context, true), child: const Text('Delete')),
                                    ],
                                  ),
                                );
                                if (confirm == true && m.id != null) {
                                  await notifier.delete(m.id!);
                                }
                              },
                            ),
                          ],
                        ),
                        onTap: () async {
                          await Navigator.of(context).push(
                            MaterialPageRoute(
                              builder: (_) => MacroEditorScreen(
                                initial: m,
                                calendarPlanId: calendarPlanId,
                              ),
                            ),
                          );
                        },
                      );
                    },
                  ),
      ),
      floatingActionButton: FloatingActionButton.extended(
        onPressed: () async {
          final created = await Navigator.of(context).push<PlanMacro>(
            MaterialPageRoute(
              builder: (_) => MacroEditorScreen(
                initial: PlanMacro(
                  calendarPlanId: calendarPlanId,
                  name: '',
                  isActive: true,
                  priority: 100,
                  rule: MacroRule.empty(),
                ),
                calendarPlanId: calendarPlanId,
              ),
            ),
          );
          if (created != null) {
            // list auto refresh handled in editor save
          }
        },
        label: const Text('Add Macro'),
        icon: const Icon(Icons.add),
      ),
    );
      },
    );
  }
}
