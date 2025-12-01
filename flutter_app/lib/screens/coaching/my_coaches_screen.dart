import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:workout_app/models/crm_coach_athlete_link.dart';
import 'package:workout_app/services/service_locator.dart' as sl;
import 'package:workout_app/config/constants/route_names.dart';
import 'package:workout_app/screens/coach/coach_chat_screen.dart';
import 'package:workout_app/widgets/primary_app_bar.dart';
import 'package:workout_app/widgets/assistant_chat_host.dart';

final myCoachesProvider = FutureProvider<List<CoachAthleteLink>>((ref) async {
  final svc = ref.watch(sl.crmRelationshipsServiceProvider);
  final links = await svc.getMyCoaches();
  return links;
});

final coachDisplayNameProvider = FutureProvider.family<String, String>((ref, coachId) async {
  final profileService = ref.watch(sl.profileServiceProvider);
  try {
    final profile = await profileService.fetchProfileById(coachId);
    final displayName = profile.displayName;
    if (displayName != null && displayName.trim().isNotEmpty) {
      return displayName;
    }
  } catch (_) {}
  return coachId;
});

class MyCoachesScreen extends ConsumerWidget {
  const MyCoachesScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final asyncLinks = ref.watch(myCoachesProvider);

    return AssistantChatHost(
      builder: (context, openChat) {
        return Scaffold(
          appBar: PrimaryAppBar(
            title: 'My Coaches',
            onTitleTap: openChat,
            actions: [
              IconButton(
                icon: const Icon(Icons.refresh),
                onPressed: () => ref.refresh(myCoachesProvider),
              ),
            ],
          ),
          body: asyncLinks.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (error, _) => Center(child: Text('Error: $error')),
        data: (links) {
          if (links.isEmpty) {
            return const Center(child: Text('No coaches yet'));
          }
          return RefreshIndicator(
            onRefresh: () async {
              await ref.refresh(myCoachesProvider.future);
            },
            child: ListView.separated(
              padding: const EdgeInsets.symmetric(vertical: 8),
              itemCount: links.length,
              separatorBuilder: (_, __) => const Divider(height: 1),
              itemBuilder: (context, index) {
                final link = links[index];
                final hasChannel = (link.channelId ?? '').isNotEmpty;
                final status = link.status.toUpperCase();
                final displayNameAsync = ref.watch(coachDisplayNameProvider(link.coachId));
                return ListTile(
                  title: displayNameAsync.when(
                    data: (value) => Text(value),
                    loading: () => Text(link.coachId),
                    error: (_, __) => Text(link.coachId),
                  ),
                  subtitle: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text('Status: $status'),
                      if ((link.note ?? '').isNotEmpty)
                        Text('Note: ${link.note}'),
                      Text('Channel: ${link.channelId ?? 'not created'}'),
                    ],
                  ),
                  trailing: TextButton.icon(
                    icon: const Icon(Icons.chat_bubble_outline),
                    label: const Text('Chat'),
                    onPressed: hasChannel
                        ? () {
                            Navigator.of(context).pushNamed(
                              RouteNames.coachChat,
                              arguments: CoachChatScreenArgs(
                                channelId: link.channelId!,
                                title: link.coachId,
                              ),
                            );
                          }
                        : null,
                  ),
                );
              },
            ),
          );
        },
      ),
        );
      },
    );
  }
}
