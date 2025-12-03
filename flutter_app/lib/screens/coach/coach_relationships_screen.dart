import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/intl.dart';
import 'package:workout_app/models/crm_analytics.dart';
import 'package:workout_app/models/crm_coach_athlete_link.dart';
import 'package:workout_app/services/service_locator.dart' as sl;
import 'package:workout_app/providers/providers.dart';
import 'package:workout_app/screens/coach/coach_chat_screen.dart';
import 'package:workout_app/config/constants/route_names.dart';
import 'package:workout_app/widgets/primary_app_bar.dart';
import 'package:workout_app/widgets/assistant_chat_host.dart';

final coachRelationshipsStatusFilterProvider = StateProvider<String?>((ref) => null);

final coachRelationshipsProvider = FutureProvider<List<CoachAthleteLink>>((ref) async {
  final svc = ref.watch(sl.crmRelationshipsServiceProvider);
  final links = await svc.getMyAthletes();
  return links;
});

final coachRelationshipsAnalyticsProvider =
    FutureProvider<Map<String, AthleteTrainingSummaryModel>>((ref) async {
  final svc = ref.watch(sl.crmAnalyticsServiceProvider);
  final analytics = await svc.getMyAthletesAnalytics();
  final map = <String, AthleteTrainingSummaryModel>{};
  for (final athlete in analytics.athletes) {
    map[athlete.athleteId] = athlete;
  }
  return map;
});

class CoachRelationshipsScreen extends ConsumerWidget {
  const CoachRelationshipsScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final asyncLinks = ref.watch(coachRelationshipsProvider);
    final analyticsAsync = ref.watch(coachRelationshipsAnalyticsProvider);
    final allUsersAsync = ref.watch(allUsersProvider);
    final analyticsMap = analyticsAsync.maybeWhen(
      data: (value) => value,
      orElse: () => null,
    );
    final usersMap = allUsersAsync.maybeWhen(
      data: (users) => {
        for (final u in users) u.userId: u,
      },
      orElse: () => null,
    );

    return AssistantChatHost(
      initialMessage:
          'Открываю ассистента из CoachRelationshipsScreen. Используй контекст v1, чтобы понимать фильтр по статусу и приоритетные связи.',
      contextBuilder: () => _buildCoachRelationshipsChatContext(ref),
      builder: (context, openChat) {
        return Scaffold(
          appBar: PrimaryAppBar(
            title: 'Coach ↔ Athletes',
            onTitleTap: openChat,
            actions: [
              IconButton(
                icon: const Icon(Icons.refresh),
                onPressed: () => ref.refresh(coachRelationshipsProvider),
              ),
              PopupMenuButton<String?>(
                onSelected: (value) {
                  ref.read(coachRelationshipsStatusFilterProvider.notifier).state = value;
                },
                itemBuilder: (context) => [
                  const PopupMenuItem<String?>(
                    value: null,
                    child: Text('All'),
                  ),
                  const PopupMenuItem<String?>(
                    value: 'pending',
                    child: Text('Pending'),
                  ),
                  const PopupMenuItem<String?>(
                    value: 'active',
                    child: Text('Active'),
                  ),
                  const PopupMenuItem<String?>(
                    value: 'paused',
                    child: Text('Paused'),
                  ),
                  const PopupMenuItem<String?>(
                    value: 'ended',
                    child: Text('Ended'),
                  ),
                ],
              ),
            ],
          ),
          body: asyncLinks.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (error, _) => Center(child: Text('Error: $error')),
        data: (links) {
          final filter = ref.watch(coachRelationshipsStatusFilterProvider);
          final filteredLinks = filter == null
              ? links
              : links.where((l) => l.status.toLowerCase() == filter).toList();

          if (filteredLinks.isEmpty) {
            return const Center(child: Text('No relationships yet'));
          }

          return RefreshIndicator(
            onRefresh: () async {
              await ref.refresh(coachRelationshipsProvider.future);
            },
            child: ListView.separated(
              padding: const EdgeInsets.symmetric(vertical: 8),
              itemCount: filteredLinks.length,
              separatorBuilder: (_, __) => const Divider(height: 1),
              itemBuilder: (context, index) {
                final link = filteredLinks[index];
                final hasChannel = (link.channelId ?? '').isNotEmpty;
                final status = link.status.toUpperCase();
                final statusLower = link.status.toLowerCase();
                final summary = analyticsMap?[link.athleteId];
                final athleteName = usersMap?[link.athleteId]?.displayName ?? link.athleteId;
                return ListTile(
                  title: Text('Athlete: $athleteName'),
                  subtitle: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text('Status: $status'),
                      if ((link.note ?? '').isNotEmpty)
                        Text('Note: ${link.note}'),
                      Text('Channel: ${link.channelId ?? 'not created'}'),
                      if (summary != null) ...[
                        const SizedBox(height: 4),
                        Text('Sessions (12w): ${summary.sessionsCount}'),
                        Text(
                          'Last workout: ${summary.lastWorkoutAt != null ? DateFormat('MMM d').format(summary.lastWorkoutAt!.toLocal()) : 'n/a'}'
                          '${summary.daysSinceLastWorkout != null ? ' · ${summary.daysSinceLastWorkout}d ago' : ''}',
                        ),
                        Text(
                          'Volume: ${summary.totalVolume != null ? summary.totalVolume!.toStringAsFixed(1) : '-'} | Active plan: ${summary.activePlanName ?? 'n/a'}',
                        ),
                      ] else if (analyticsAsync.isLoading) ...[
                        const SizedBox(height: 4),
                        const Text('Loading training summary...'),
                      ],
                    ],
                  ),
                  trailing: statusLower == 'pending'
                      ? Row(
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            TextButton(
                              onPressed: () async {
                                final svc = ref.read(sl.crmRelationshipsServiceProvider);
                                try {
                                  await svc.updateStatus(
                                    id: link.id,
                                    status: 'active',
                                  );
                                  if (context.mounted) {
                                    ScaffoldMessenger.of(context).showSnackBar(
                                      const SnackBar(content: Text('Request accepted')),
                                    );
                                  }
                                  ref.refresh(coachRelationshipsProvider);
                                } catch (e) {
                                  if (context.mounted) {
                                    ScaffoldMessenger.of(context).showSnackBar(
                                      SnackBar(content: Text('Failed to accept: $e')),
                                    );
                                  }
                                }
                              },
                              child: const Text('Accept'),
                            ),
                            TextButton(
                              onPressed: () async {
                                final controller = TextEditingController();
                                final confirmed = await showDialog<bool>(
                                  context: context,
                                  builder: (ctx) {
                                    return AlertDialog(
                                      title: const Text('Decline request'),
                                      content: TextField(
                                        controller: controller,
                                        decoration: const InputDecoration(
                                          labelText: 'Reason (optional)',
                                        ),
                                        maxLines: 3,
                                      ),
                                      actions: [
                                        TextButton(
                                          onPressed: () => Navigator.of(ctx).pop(false),
                                          child: const Text('Cancel'),
                                        ),
                                        ElevatedButton(
                                          onPressed: () => Navigator.of(ctx).pop(true),
                                          child: const Text('Decline'),
                                        ),
                                      ],
                                    );
                                  },
                                );
                                if (confirmed != true) return;
                                final svc = ref.read(sl.crmRelationshipsServiceProvider);
                                try {
                                  final reason = controller.text.trim();
                                  await svc.updateStatus(
                                    id: link.id,
                                    status: 'ended',
                                    endedReason: reason.isEmpty ? null : reason,
                                  );
                                  if (context.mounted) {
                                    ScaffoldMessenger.of(context).showSnackBar(
                                      const SnackBar(content: Text('Request declined')),
                                    );
                                  }
                                  ref.refresh(coachRelationshipsProvider);
                                } catch (e) {
                                  if (context.mounted) {
                                    ScaffoldMessenger.of(context).showSnackBar(
                                      SnackBar(content: Text('Failed to decline: $e')),
                                    );
                                  }
                                }
                              },
                              child: const Text('Decline'),
                            ),
                          ],
                        )
                      : Row(
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            IconButton(
                              icon: const Icon(Icons.chat_bubble_outline),
                              tooltip: 'Chat',
                              onPressed: hasChannel
                                  ? () {
                                      Navigator.of(context).pushNamed(
                                        RouteNames.coachChat,
                                        arguments: CoachChatScreenArgs(
                                          channelId: link.channelId!,
                                          title: athleteName,
                                        ),
                                      );
                                    }
                                  : null,
                            ),
                            IconButton(
                              icon: const Icon(Icons.insights_outlined),
                              tooltip: 'Analytics',
                              onPressed: () {
                                Navigator.of(context).pushNamed(
                                  RouteNames.coachAthleteDetail,
                                  arguments: link.athleteId,
                                );
                              },
                            ),
                            IconButton(
                              icon: const Icon(Icons.notifications_active_outlined),
                              tooltip: 'Nudge',
                              onPressed: (statusLower == 'active' && hasChannel)
                                  ? () => _sendNudge(context, ref, link, summary)
                                  : null,
                            ),
                            PopupMenuButton<String>(
                              onSelected: (value) async {
                                if (value == 'pause') {
                                  final svc = ref.read(sl.crmRelationshipsServiceProvider);
                                  try {
                                    await svc.updateStatus(id: link.id, status: 'paused');
                                    if (context.mounted) {
                                      ScaffoldMessenger.of(context).showSnackBar(
                                        const SnackBar(content: Text('Coaching paused')),
                                      );
                                    }
                                    ref.refresh(coachRelationshipsProvider);
                                  } catch (e) {
                                    if (context.mounted) {
                                      ScaffoldMessenger.of(context).showSnackBar(
                                        SnackBar(content: Text('Failed to pause: $e')),
                                      );
                                    }
                                  }
                                } else if (value == 'resume') {
                                  final svc = ref.read(sl.crmRelationshipsServiceProvider);
                                  try {
                                    await svc.updateStatus(id: link.id, status: 'active');
                                    if (context.mounted) {
                                      ScaffoldMessenger.of(context).showSnackBar(
                                        const SnackBar(content: Text('Coaching resumed')),
                                      );
                                    }
                                    ref.refresh(coachRelationshipsProvider);
                                  } catch (e) {
                                    if (context.mounted) {
                                      ScaffoldMessenger.of(context).showSnackBar(
                                        SnackBar(content: Text('Failed to resume: $e')),
                                      );
                                    }
                                  }
                                } else if (value == 'end') {
                                  final controller = TextEditingController();
                                  final confirmed = await showDialog<bool>(
                                    context: context,
                                    builder: (ctx) {
                                      return AlertDialog(
                                        title: const Text('End coaching'),
                                        content: TextField(
                                          controller: controller,
                                          decoration: const InputDecoration(
                                            labelText: 'Reason (optional)',
                                          ),
                                          maxLines: 3,
                                        ),
                                        actions: [
                                          TextButton(
                                            onPressed: () => Navigator.of(ctx).pop(false),
                                            child: const Text('Cancel'),
                                          ),
                                          ElevatedButton(
                                            onPressed: () => Navigator.of(ctx).pop(true),
                                            child: const Text('End'),
                                          ),
                                        ],
                                      );
                                    },
                                  );
                                  if (confirmed != true) return;
                                  final svc = ref.read(sl.crmRelationshipsServiceProvider);
                                  try {
                                    final reason = controller.text.trim();
                                    await svc.updateStatus(
                                      id: link.id,
                                      status: 'ended',
                                      endedReason: reason.isEmpty ? null : reason,
                                    );
                                    if (context.mounted) {
                                      ScaffoldMessenger.of(context).showSnackBar(
                                        const SnackBar(content: Text('Coaching ended')),
                                      );
                                    }
                                    ref.refresh(coachRelationshipsProvider);
                                  } catch (e) {
                                    if (context.mounted) {
                                      ScaffoldMessenger.of(context).showSnackBar(
                                        SnackBar(content: Text('Failed to end: $e')),
                                      );
                                    }
                                  }
                                }
                              },
                              itemBuilder: (context) => [
                                if (statusLower == 'active')
                                  const PopupMenuItem<String>(
                                    value: 'pause',
                                    child: Text('Pause coaching'),
                                  ),
                                if (statusLower == 'paused')
                                  const PopupMenuItem<String>(
                                    value: 'resume',
                                    child: Text('Resume coaching'),
                                  ),
                                if (statusLower != 'ended')
                                  const PopupMenuItem<String>(
                                    value: 'end',
                                    child: Text('End coaching'),
                                  ),
                              ],
                            ),
                          ],
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

Future<void> _sendNudge(
  BuildContext context,
  WidgetRef ref,
  CoachAthleteLink link,
  AthleteTrainingSummaryModel? summary,
) async {
  final channelId = link.channelId;
  if (channelId == null || channelId.isEmpty) {
    if (context.mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Chat channel is not available')),
      );
    }
    return;
  }

  final days = summary?.daysSinceLastWorkout;
  final message = days != null && days > 0
      ? 'Hey ${link.athleteId}, it\'s been $days day${days == 1 ? '' : 's'} since your last workout. Let\'s plan the next session!'
      : 'Hey ${link.athleteId}, let\'s schedule our next workout soon!';

  try {
    final messaging = ref.read(sl.messagingServiceProvider);
    await messaging.sendTextMessage(channelId: channelId, content: message);
    if (context.mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Nudge sent')),
      );
    }
  } catch (e) {
    if (context.mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Failed to send nudge: $e')),
      );
    }
  }
}

Future<Map<String, dynamic>> _buildCoachRelationshipsChatContext(WidgetRef ref) async {
  try {
    final links = await ref.read(coachRelationshipsProvider.future);
    Map<String, AthleteTrainingSummaryModel>? analyticsMap;
    try {
      analyticsMap = await ref.read(coachRelationshipsAnalyticsProvider.future);
    } catch (_) {}

    final filter = ref.read(coachRelationshipsStatusFilterProvider);
    final nowIso = DateTime.now().toUtc().toIso8601String();

    final byStatus = <String, int>{};
    for (final link in links) {
      final key = link.status.toLowerCase();
      byStatus[key] = (byStatus[key] ?? 0) + 1;
    }

    final highlighted = links
        .where((l) => filter == null || l.status.toLowerCase() == filter)
        .take(3)
        .map((link) {
      final summary = analyticsMap?[link.athleteId];
      return {
        'relationship_id': link.id,
        'athlete_id': link.athleteId,
        'status': link.status,
        'channel_id': link.channelId,
        'note': link.note,
        'summary': summary == null
            ? null
            : {
                'sessions_12w': summary.sessionsCount,
                'sessions_per_week': summary.sessionsPerWeek,
                'plan_adherence': summary.planAdherence,
                'days_since_last_workout': summary.daysSinceLastWorkout,
                'active_plan_name': summary.activePlanName,
              },
      };
    }).toList();

    return {
      'v': 1,
      'app': 'WorkoutApp',
      'screen': 'coach_relationships',
      'role': 'coach',
      'timestamp': nowIso,
      'entities': {
        'relationships_summary': {
          'total': links.length,
          'by_status': byStatus,
        },
        'highlighted_relationships': highlighted,
      },
      'selection': {
        'status_filter': filter,
      },
    };
  } catch (e) {
    return {
      'v': 1,
      'app': 'WorkoutApp',
      'screen': 'coach_relationships',
      'role': 'coach',
      'timestamp': DateTime.now().toUtc().toIso8601String(),
      'error': e.toString(),
    };
  }
}
